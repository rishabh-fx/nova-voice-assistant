"""
Settings, read from environment variables, a local .env file, or Streamlit secrets.

The chat model is reached through any OpenAI-compatible endpoint:
  * Azure OpenAI (v1 API):  LLM_BASE_URL=https://<resource>.openai.azure.com/openai/v1/
                            CHAT_MODEL=<your deployment name>
  * Any other OpenAI-compatible provider (OpenAI, Groq, ...): only these three values change.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:          # python-dotenv is optional
    pass


def _get(name, default=""):
    """Environment variable first, then Streamlit secrets (used on Streamlit Community Cloud)."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:        # streamlit not installed, or no secrets file
        return default


def _int(name, default):
    try:
        return int(_get(name, default))
    except ValueError:
        return int(default)


@dataclass
class Settings:
    llm_base_url: str = field(default_factory=lambda: _get("LLM_BASE_URL"))
    llm_api_key: str = field(default_factory=lambda: _get("LLM_API_KEY"))
    chat_model: str = field(default_factory=lambda: _get("CHAT_MODEL"))

    # Optional: Tavily key for higher-quality web answers. Empty -> free DuckDuckGo search.
    tavily_api_key: str = field(default_factory=lambda: _get("TAVILY_API_KEY"))

    # Protecting the public app (and your cloud bill)
    access_code: str = field(default_factory=lambda: _get("ACCESS_CODE"))          # empty = open to everyone
    max_messages: int = field(default_factory=lambda: _int("MAX_MESSAGES_PER_SESSION", 40))

    def check(self):
        missing = [n for n, v in [("LLM_BASE_URL", self.llm_base_url),
                                  ("LLM_API_KEY", self.llm_api_key),
                                  ("CHAT_MODEL", self.chat_model)] if not v]
        if missing:
            raise RuntimeError(f"Missing settings: {', '.join(missing)}. "
                               "Add them to .env (local) or the app's Secrets (Streamlit Cloud).")
        return self


settings = Settings()
