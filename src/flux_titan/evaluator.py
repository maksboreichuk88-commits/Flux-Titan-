"""
AI Scoring Agent — NewsEvaluator.

Runs each article through an LLM "Judge" prompt and returns a structured
evaluation (clickbait score, factuality score, approval decision).
"""

import json
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import google.generativeai as genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from flux_titan.config import Config

logger = logging.getLogger("NewsBot.Evaluator")


@dataclass
class EvaluationResult:
    """Structured result from the AI Judge."""
    clickbait_score: int = 100      # 0 (clean) → 100 (extreme clickbait)
    factuality_score: int = 0       # 0 (fiction) → 100 (solid facts)
    is_approved: bool = False
    raw_response: str = ""


JUDGE_SYSTEM_PROMPT = """You are a strict Senior News Editor AI Judge.
You evaluate news articles for quality before they are published on a premium Telegram channel.

Your job:
1. Assess the CLICKBAIT level of the headline and content (0 = clean journalism, 100 = extreme clickbait).
2. Assess the FACTUALITY of the content (0 = unverifiable fiction, 100 = well-sourced hard facts).
3. Decide whether the article is APPROVED for publication.

Approval rules:
• clickbait_score MUST be < {clickbait_threshold}
• factuality_score MUST be > {factuality_threshold}
• Both conditions must be met for approval.

You MUST respond with ONLY a valid JSON object — no markdown, no explanation:
{{"clickbait_score": <0-100>, "factuality_score": <0-100>, "is_approved": <true|false>}}"""


JUDGE_USER_PROMPT = """Evaluate this article:

TITLE: {title}

CONTENT:
{content}

Respond with JSON only."""


class NewsEvaluator:
    """
    Evaluates article quality via a fast LLM call.
    Supports Gemini and OpenAI-compatible backends.
    """

    def __init__(self, config: Config):
        self.config = config
        self._system_prompt = JUDGE_SYSTEM_PROMPT.format(
            clickbait_threshold=config.clickbait_threshold,
            factuality_threshold=config.factuality_threshold,
        )
        logger.info(
            "NewsEvaluator initialized (clickbait<%d, factuality>%d)",
            config.clickbait_threshold,
            config.factuality_threshold,
        )

    async def evaluate(self, article: Dict[str, Any]) -> EvaluationResult:
        """
        Run article through the AI Judge.

        Args:
            article: dict with 'title' and 'content' / 'summary' keys.

        Returns:
            EvaluationResult with scores and approval status.
        """
        title = article.get("title", "")
        content = article.get("content", article.get("summary", ""))[:2000]
        user_prompt = JUDGE_USER_PROMPT.format(title=title, content=content)

        try:
            if self.config.ai_provider == "gemini":
                raw = await self._call_gemini(user_prompt)
            else:
                raw = await self._call_openai(user_prompt)

            if not raw:
                logger.warning("Empty AI Judge response — rejecting article")
                return EvaluationResult(raw_response="<empty>")

            return self._parse_response(raw)

        except Exception as e:
            logger.error("Evaluation failed: %s — rejecting article", e)
            return EvaluationResult(raw_response=str(e))

    # ── Gemini backend ──────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _gemini_generate_sync(self, prompt: str) -> Optional[str]:
        """Synchronous Gemini call (runs in thread pool)."""
        genai.configure(api_key=self.config.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=self.config.gemini_model,
            system_instruction=self._system_prompt,
        )
        response = model.generate_content(prompt)
        if response.parts:
            return response.text
        return None

    async def _call_gemini(self, prompt: str) -> Optional[str]:
        return await asyncio.to_thread(self._gemini_generate_sync, prompt)

    # ── OpenAI-compatible backend ───────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _openai_generate_sync(self, prompt: str) -> Optional[str]:
        """Synchronous OpenAI call (runs in thread pool)."""
        client_kwargs: Dict[str, Any] = {"api_key": self.config.openai_api_key}
        if self.config.openai_base_url:
            client_kwargs["base_url"] = self.config.openai_base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        return response.choices[0].message.content

    async def _call_openai(self, prompt: str) -> Optional[str]:
        return await asyncio.to_thread(self._openai_generate_sync, prompt)

    # ── Response parsing ────────────────────────────────────────────

    @staticmethod
    def _parse_response(raw: str) -> EvaluationResult:
        """Parse JSON from the LLM response, tolerating markdown fences."""
        cleaned = raw.strip()
        # Strip ```json ... ``` wrappers
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return EvaluationResult(
                clickbait_score=int(data.get("clickbait_score", 100)),
                factuality_score=int(data.get("factuality_score", 0)),
                is_approved=bool(data.get("is_approved", False)),
                raw_response=raw,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error("Could not parse Judge response: %s | raw=%s", e, raw[:200])
            return EvaluationResult(raw_response=raw)
