# Flux-Titan Issue Drafts

These drafts are aligned with the current product direction:

- Telegram is the only output channel in this phase.
- No web dashboards.
- No multi-platform expansion.
- No general-purpose "AI agent does everything" scope.

Direct GitHub issue creation was not available in the current environment, so the items below are ready to paste into GitHub manually.

## Current Issue Cleanup

- Keep and rewrite issue `#2` as `Keep processed state across scheduled newsroom runs`
- Keep and rewrite issue `#4` as `Harden RSS ingestion against malformed or partial feeds`
- Replace issue `#1` with `Add OpenAI-compatible base URL support`
- Close issue `#3` as out of scope for the Telegram-only phase
- Close issue `#5` as out of scope for the selected-sources newsroom workflow

---

## Title: Add source priority scoring for selected feeds

```markdown
## Problem

Flux-Titan can collect from multiple sources, but it still treats new items mostly as a flat stream. That makes it harder to consistently favor stronger sources or higher-value items when the per-run article limit is low.

## Why it matters

A newsroom workflow needs a lightweight ranking step, even if it is not a full editorial scoring system. Source priority scoring would improve which items get rewritten and published first without turning Flux-Titan into a heavy platform.

## Proposed solution

Add optional source priority scoring to the source configuration layer. Each source should be able to carry a small numeric priority, and item selection should prefer higher-priority sources before lower-priority ones when building the candidate list for a run.

Keep the implementation simple:

- source-level priority only
- no machine-learned ranking
- no dashboard
- no change to the Telegram-only publishing target

## Acceptance criteria

- `feeds.yaml` supports an optional priority field for each source
- the in-memory article list is sorted with source priority included in the final ordering
- the default behavior stays backward compatible when priority is not set
- tests cover mixed-priority feeds and confirm higher-priority items are selected first
```

---

## Title: Add manual approval mode before Telegram publish

```markdown
## Problem

Flux-Titan currently publishes automatically once a post has been generated. Some operators need a lightweight approval step before a post goes live, especially for higher-risk channels or curated news flows.

## Why it matters

An approval mode makes Flux-Titan more usable as a newsroom tool, not just an unattended automation script. It adds human review without requiring a dashboard or changing the Telegram-first scope.

## Proposed solution

Add an optional manual approval mode that stops after rewrite and image selection, then stores the candidate post for review before publish.

Keep it lightweight:

- no web UI
- no new output platforms
- no editorial queue system beyond what is needed for approve-or-skip

The first implementation can store pending items locally and provide a simple CLI-oriented approval flow.

## Acceptance criteria

- a config flag enables manual approval mode
- generated posts can be stored locally as pending items instead of being published immediately
- operators can approve or skip pending items without editing source code
- automatic publish remains the default behavior when approval mode is disabled
- tests cover both automatic publish mode and approval mode
```

---

## Title: Add image fallback chain for Telegram posts

```markdown
## Problem

Flux-Titan currently relies on a narrow image extraction path. When the first candidate image is missing or unusable, the post often falls back to text-only even when another valid image is available on the page.

## Why it matters

Image quality affects Telegram post quality directly. A newsroom workflow needs a more reliable image path, but it does not need a complex media pipeline.

## Proposed solution

Add an image fallback chain that tries multiple extraction candidates in order, such as:

1. `og:image`
2. `twitter:image`
3. other relevant meta/image candidates already present on the page

Keep the logic narrow and deterministic. If no valid image is found, the system should still publish text-only.

## Acceptance criteria

- image extraction tries more than one candidate source before giving up
- the fallback order is explicit and testable
- invalid or empty image URLs are skipped cleanly
- text-only publishing still works when no image candidate succeeds
- tests cover primary success, fallback success, and no-image cases
```

---

## Title: Add OpenAI-compatible base URL support

```markdown
## Problem

Flux-Titan supports OpenAI-style APIs in practice, but the public configuration path is still too tied to named provider variants. That makes it harder to use self-hosted or third-party OpenAI-compatible backends cleanly.

## Why it matters

Provider flexibility should help operators choose a backend without turning Flux-Titan into a provider zoo. A single OpenAI-compatible path keeps the product small and practical.

## Proposed solution

Add `OPENAI_BASE_URL` as an optional configuration input and make `openai_compatible` the main path for OpenAI-style APIs.

Compatibility aliases such as `openai` and `kimi` can remain supported, but the public docs and config should guide new users toward:

- `AI_PROVIDER=openai_compatible`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- optional `OPENAI_BASE_URL`

## Acceptance criteria

- config supports `OPENAI_BASE_URL`
- `AI_PROVIDER=openai_compatible` works with and without a custom base URL
- `AI_PROVIDER=openai` still works as a compatibility alias
- `AI_PROVIDER=kimi` still works as a compatibility alias
- tests cover alias normalization and custom base URL initialization
```

---

## Title: Add digest mode for grouped Telegram posting

```markdown
## Problem

Flux-Titan currently posts one item at a time. For some newsroom use cases, a grouped digest is more useful than several separate posts, especially when operators want periodic briefings instead of a continuous stream.

## Why it matters

Digest mode is a natural newsroom workflow for Telegram channels. It keeps the publishing target the same while broadening how curated updates can be delivered.

## Proposed solution

Add an optional digest mode that groups multiple selected items into one scheduled Telegram post.

Keep the first version small:

- Telegram only
- no dashboard
- no separate digest management service

The digest should reuse the existing collection, filtering, and rewrite steps, then combine the selected summaries into a single Telegram-ready output.

## Acceptance criteria

- a config flag enables digest mode
- multiple selected items can be grouped into one Telegram post
- the default one-item publishing path remains unchanged when digest mode is disabled
- the digest respects the existing article limit or an explicit digest size setting
- tests cover grouped output formatting and the default non-digest path
```

---

## Title: Keep processed state across scheduled newsroom runs

```markdown
## Problem

Flux-Titan uses SQLite to track processed links, but scheduled environments such as GitHub Actions can lose state between runs if the database file is not preserved correctly.

## Why it matters

A newsroom workflow becomes noisy and unreliable when deduplication state is lost. Preserving processed state is a core reliability requirement for repeated Telegram publishing.

## Proposed solution

Make scheduled deployment guidance and workflow defaults preserve `processed.db` between runs in the supported self-hosted paths.

This should stay focused on practical state persistence for recurring newsroom runs, not on adding a separate hosted database product.

## Acceptance criteria

- the supported scheduled path documents how processed state is preserved
- the GitHub Actions example preserves processed state across runs
- duplicate items are not reposted when state has been restored correctly
- tests or smoke checks cover the expected persistence behavior
```

---

## Title: Harden RSS ingestion against malformed or partial feeds

```markdown
## Problem

Some sources expose malformed, partial, or inconsistently encoded RSS feeds. Today a broken feed can still reduce run quality or pollute logs more than necessary.

## Why it matters

Flux-Titan depends on selected sources staying usable. A newsroom workflow should degrade gracefully when one source is noisy or broken instead of treating feed parsing as all-or-nothing.

## Proposed solution

Improve RSS ingestion resilience so malformed or partial feeds are isolated and skipped cleanly when possible.

Keep the change focused on robustness:

- better error handling
- better logging
- no expansion into a generic ingestion framework

## Acceptance criteria

- malformed or partially broken feeds do not break the full run
- feed-level errors are logged clearly
- usable feeds in the same run continue to process normally
- tests cover malformed feed input and confirm the rest of the pipeline still proceeds
```
