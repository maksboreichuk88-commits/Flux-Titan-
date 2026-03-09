"""
Compatibility wrapper for Kimi via an OpenAI-compatible API.
"""

from .openai import OpenAISummarizer

DEFAULT_KIMI_MODEL = "moonshotai/kimi-k2.5"
DEFAULT_KIMI_BASE_URL = "https://integrate.api.nvidia.com/v1"


class KimiSummarizer(OpenAISummarizer):
    """
    Compatibility preset for existing Kimi-based setups.
    Prefer the generic OpenAI-compatible path in new configurations.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_KIMI_MODEL,
        base_url: str = DEFAULT_KIMI_BASE_URL,
    ):
        super().__init__(
            api_key=api_key,
            model=self._normalize_model_name(model),
            base_url=base_url,
            provider_name="Kimi-compatible",
            temperature=0.6,
            top_p=0.95,
            max_tokens=4096,
            extra_body={"thinking": {"type": "disabled"}},
        )

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        model = model.strip()
        if "/" in model or not model.startswith("kimi-"):
            return model

        return f"moonshotai/{model}"
