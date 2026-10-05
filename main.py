"""
Terminal mode, for quick testing without the web app.

    python main.py             # type commands
    python main.py --verbose   # also show tool calls, tokens and latency

Type "exit" to quit. The web app (voice + UI) is started with:  streamlit run app.py
"""
import argparse

from assistant.config import settings
from assistant.factory import build_agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="show tool calls, tokens and latency")
    opts = ap.parse_args()

    agent = build_agent(settings, timezone=_local_tz())
    print("Nova: Hi, I'm Nova. How can I help?")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower().strip(" .!") in {"exit", "quit", "bye", "goodbye"}:
            break
        res = agent.run(text)
        if opts.verbose:
            for tc in res.tool_calls:
                print(f"  🛠  {tc.name}({tc.args}) -> {str(tc.result)[:300]}")
            print(f"  ⏱  {res.latency_s}s | {res.llm_calls} LLM calls | "
                  f"{res.prompt_tokens}+{res.completion_tokens} tokens")
        print(f"Nova: {res.reply}")
        for action in res.actions:
            print(f"  ↗  {action['label']}: {action['url']}")
    print("Nova: Goodbye!")


def _local_tz():
    """IANA name of this computer's timezone (e.g. 'Asia/Kolkata'), falling back to UTC."""
    try:
        from tzlocal import get_localzone_name
        return get_localzone_name()
    except Exception:
        import os
        link = os.path.realpath("/etc/localtime")
        return link.split("zoneinfo/")[-1] if "zoneinfo/" in link else "UTC"


if __name__ == "__main__":
    main()
