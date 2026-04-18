"""Token usage tracking callback for LangChain/Anthropic API calls."""
from langchain_core.callbacks import BaseCallbackHandler


class TokenUsageHandler(BaseCallbackHandler):
    """Callback handler to capture token usage from Anthropic API."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_end(self, response, **kwargs):
        """Capture token usage when LLM call completes."""
        # Try from llm_output
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("usage", {})
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)

        # Also try from generation_info
        if hasattr(response, "generations"):
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "generation_info") and gen.generation_info:
                        usage = gen.generation_info.get("usage", {})
                        self.input_tokens += usage.get("input_tokens", 0)
                        self.output_tokens += usage.get("output_tokens", 0)

    def get_usage(self) -> dict[str, int]:
        """Return usage dict."""
        return {"input": self.input_tokens, "output": self.output_tokens}

    @property
    def has_data(self) -> bool:
        """Check if any tokens were captured."""
        return self.input_tokens > 0 or self.output_tokens > 0


def estimate_tokens(text: str) -> int:
    """
    Rough estimate: ~1 token per 3 chars for Vietnamese.
    Used as fallback when callback doesn't capture usage.
    """
    return len(text) // 3
