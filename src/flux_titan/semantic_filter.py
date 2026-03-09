"""
Semantic Deduplication Filter.

Compares a new article title against recent titles using:
  1. Fast token-overlap (Jaccard) pre-screening.
  2. LLM verification for borderline cases.
"""

import asyncio
import logging
import re
from typing import List, Optional

import google.generativeai as genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from flux_titan.config import Config

logger = logging.getLogger("NewsBot.SemanticFilter")

# ── Lightweight token-based pre-filter ─────────────────────────────────

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will shall would should can could may might must and or but if in on at "
    "to for of with by from as into through during about — – - : | «»".split()
)


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, remove stop words."""
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def jaccard_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    sa, sb = _tokenize(a), _tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ── LLM-based semantic check ──────────────────────────────────────────

_DEDUP_PROMPT = """You are a duplicate-detection engine for a news pipeline.
Determine if the NEW title describes the SAME event or news story as ANY title in the list.

NEW TITLE: "{new_title}"

RECENT TITLES:
{titles_block}

Rules:
• "Same event" means ≥85 % semantic overlap — the core news is identical.
• Different angles or genuinely new information about the same topic count as DIFFERENT.
• Respond with EXACTLY one word: YES or NO."""


async def check_semantic_duplicate(
    new_title: str,
    recent_titles: List[str],
    config: Config,
) -> bool:
    """
    Return True if *new_title* is a semantic duplicate of any recent title.
    
    Pipeline:
      1. Jaccard pre-screen — if similarity ≥ 0.60 with any title, escalate to LLM.
      2. LLM verdict — ask the model for a YES/NO answer.
      3. If Jaccard ≥ 0.90, skip LLM entirely and report duplicate immediately.
    """
    if not recent_titles:
        return False

    threshold = config.dedup_similarity_threshold  # default 0.85

    # --- Stage 1: fast token overlap ---
    max_sim = 0.0
    for t in recent_titles:
        sim = jaccard_similarity(new_title, t)
        if sim > max_sim:
            max_sim = sim

    if max_sim >= 0.90:
        logger.info(
            "Jaccard=%.2f ≥ 0.90 → instant duplicate: %s", max_sim, new_title[:80]
        )
        return True

    if max_sim < 0.35:
        # Clearly different — no need to ask LLM
        return False

    # --- Stage 2: LLM verification for borderline titles ---
    titles_block = "\n".join(f"{i}. {t}" for i, t in enumerate(recent_titles, 1))
    prompt = _DEDUP_PROMPT.format(new_title=new_title, titles_block=titles_block)

    try:
        if config.ai_provider == "gemini":
            result = await _ask_gemini(prompt, config)
        else:
            result = await _ask_openai(prompt, config)

        if result and "YES" in result.upper():
            logger.info("LLM confirmed semantic duplicate: %s", new_title[:80])
            return True
        return False

    except Exception as e:
        logger.error("Semantic check LLM call failed: %s — allowing article", e)
        return False


# ── LLM helpers (with tenacity retries) ────────────────────────────────

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8), reraise=True)
def _gemini_sync(prompt: str, config: Config) -> Optional[str]:
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)
    response = model.generate_content(prompt)
    return response.text.strip() if response.parts else None


async def _ask_gemini(prompt: str, config: Config) -> Optional[str]:
    return await asyncio.to_thread(_gemini_sync, prompt, config)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8), reraise=True)
def _openai_sync(prompt: str, config: Config) -> Optional[str]:
    kw = {"api_key": config.openai_api_key}
    if config.openai_base_url:
        kw["base_url"] = config.openai_base_url
    client = OpenAI(**kw)
    resp = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": "Reply only YES or NO."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=5,
    )
    return resp.choices[0].message.content.strip()


async def _ask_openai(prompt: str, config: Config) -> Optional[str]:
    return await asyncio.to_thread(_openai_sync, prompt, config)
