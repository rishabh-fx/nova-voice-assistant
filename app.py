"""
Nova web app: talk to the assistant from any device with a browser.

    streamlit run app.py

Voice in : the browser's own speech recognition (Web Speech API), via streamlit-mic-recorder.
Brain    : a cloud LLM with function calling (assistant/agent.py).
Voice out: the browser's own speech synthesis.
Actions  : opening sites / music happens in the VISITOR's browser, not on the server.
"""
import json
import re

import streamlit as st
import streamlit.components.v1 as components
from streamlit_mic_recorder import speech_to_text

from assistant.agent import make_client
from assistant.config import settings
from assistant.factory import build_agent

st.set_page_config(page_title="Nova · Voice Assistant", page_icon="🎙️", layout="centered")

LANGUAGES = {"English": "en-US", "Hindi": "hi-IN"}
EXAMPLES = ["What's the weather in Bengaluru today?", "What is 18% of 2,450?",
            "Play some lofi music", "What's the latest news about ISRO?"]
AVATARS = {"user": "🧑", "assistant": "🎙️"}

# Nova's voice. Voices come from the visitor's device, so each language lists names to try in
# order (macOS/iOS, Chrome, Windows/Edge, Android); the first one the device has is used.
VOICES = {
    "en-US": ["Samantha", "Google US English", "Microsoft Aria", "Microsoft Jenny",
              "Microsoft Zira", "Ava", "Allison", "Susan"],
    "hi-IN": ["Lekha", "Google हिन्दी", "Microsoft Swara", "Microsoft Kalpana"],
}

st.markdown("""
<style>
  #MainMenu, footer {visibility: hidden;}
  .block-container {padding-top: 2.2rem; max-width: 760px;}
  .nova-hero {text-align: center; margin: .5rem 0 1.4rem;}
  .nova-hero h1 {font-size: 2.6rem; margin: 0; letter-spacing: -.02em;
                 background: linear-gradient(90deg, #7c5cff, #2fb7ff);
                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
  .nova-hero p {opacity: .75; margin: .3rem 0 0;}
  .nova-tools {font-size: .78rem; opacity: .6; margin-top: .2rem;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ setup
@st.cache_resource
def get_client():
    return make_client(settings.check())


def get_agent():
    if "agent" not in st.session_state:
        tz = getattr(st.context, "timezone", None) or "UTC"      # visitor's timezone, from their browser
        st.session_state.agent = build_agent(settings, timezone=tz, client=get_client())
    return st.session_state.agent


def for_speech(text):
    """Strip markdown symbols so the browser voice doesn't read them out."""
    return re.sub(r"[*_#`>\[\]]", "", text)


def run_in_browser(reply=None, voice_lang="en-US", voice_names=(), urls=()):
    """Speak the reply and open URLs on the visitor's device. Uses the parent page's
    speechSynthesis so speech continues even after Streamlit re-renders."""
    js_text = json.dumps(for_speech(reply) if reply else "").replace("</", "<\\/")
    js_urls = json.dumps(list(urls)).replace("</", "<\\/")
    _embed_script(f"""
    <script>
      const w = (() => {{ try {{ return window.parent.speechSynthesis ? window.parent : window; }}
                          catch (e) {{ return window; }} }})();
      const text = {js_text}, lang = {json.dumps(voice_lang)}, names = {json.dumps(list(voice_names))};

      function pickVoice(voices) {{
        // 1) a preferred voice by name, 2) any voice with the same language, 3) device default
        for (const n of names) {{
          const v = voices.find(v => v.name.startsWith(n) && v.lang.replace("_", "-").startsWith(lang.slice(0, 2)));
          if (v) return v;
        }}
        return voices.find(v => v.lang.replace("_", "-") === lang) || null;
      }}

      let spoken = false;               // speak once, even if both triggers below fire
      function speak() {{
        if (spoken) return;
        spoken = true;
        w.speechSynthesis.cancel();
        const u = new w.SpeechSynthesisUtterance(text);
        u.lang = lang;
        const v = pickVoice(w.speechSynthesis.getVoices());
        if (v) u.voice = v;
        w.speechSynthesis.speak(u);
      }}

      if (text && w.speechSynthesis) {{
        // Chrome loads its voice list asynchronously; wait for it once if it's still empty.
        if (w.speechSynthesis.getVoices().length) speak();
        else {{
          w.speechSynthesis.addEventListener("voiceschanged", speak, {{ once: true }});
          setTimeout(speak, 700);
        }}
      }}
      for (const url of {js_urls}) {{ try {{ w.open(url, "_blank", "noopener"); }} catch (e) {{}} }}
    </script>""")


def _embed_script(html):
    """Run our own script in a hidden iframe. st.iframe replaces the deprecated
    components.html in newer Streamlit; fall back to it on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=1)          # st.iframe needs a positive height; 1px is invisible
    else:
        components.html(html, height=0)


def show_message(m):
    with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
        st.markdown(m["content"].replace("$", "\\$"))
        if m.get("tools"):
            st.markdown(f"<div class='nova-tools'>🛠 used: {', '.join(m['tools'])}</div>",
                        unsafe_allow_html=True)
        for a in m.get("actions", []):
            st.link_button(f"{a['label']} ↗", a["url"])


ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("count", 0)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Settings")
    lang = LANGUAGES[st.selectbox("Language", list(LANGUAGES))]
    speak = st.toggle("Read replies aloud", value=True)
    if st.button("New conversation", width="stretch"):
        ss.messages, ss.count = [], 0
        if "agent" in ss:
            ss.agent.reset()
        st.rerun()
    st.divider()
    st.markdown("**What Nova can do**\n\n"
                "- Live weather for any city\n- Search the web and summarise the news\n"
                "- Exact maths\n- Open websites and play music on *your* device\n"
                "- Chat, explain, translate")
    st.caption("Voice input works in Chrome, Edge and Safari. Nova remembers this conversation "
               "only until you close the page.")

# ------------------------------------------------------------------ main
st.markdown("<div class='nova-hero'><h1>Nova</h1>"
            "<p>Your voice assistant, powered by a cloud LLM. Tap the mic or type.</p></div>",
            unsafe_allow_html=True)

chat = st.container()            # messages go here, so the mic stays below them
with chat:
    for m in ss.messages:
        show_message(m)

prompt = None
examples_slot = st.empty()
if not ss.messages:
    cols = examples_slot.container().columns(2)
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 2].button(ex, width="stretch", key=f"ex{i}"):
            prompt = ex

spoken = speech_to_text(language=lang, start_prompt="🎤  Tap to speak", stop_prompt="⏹  Stop listening",
                        just_once=True, use_container_width=True, key="mic")
typed = st.chat_input("Type a message…")
prompt = typed or spoken or prompt

if prompt:
    examples_slot.empty()
    if ss.count >= settings.max_messages:
        with chat:
            st.warning("You've reached the message limit for this session. Start a new conversation "
                       "from the sidebar to continue.")
        st.stop()

    user_msg = {"role": "user", "content": prompt}
    ss.messages.append(user_msg)
    with chat:
        show_message(user_msg)
        with st.spinner("Thinking…"):
            try:
                res = get_agent().run(prompt)
                bot_msg = {"role": "assistant", "content": res.reply or "Sorry, I have no answer for that.",
                           "tools": sorted({t.name for t in res.tool_calls}), "actions": res.actions}
            except RuntimeError as e:                    # missing configuration
                bot_msg = {"role": "assistant", "content": f"Nova isn't configured yet: {e}"}
            except Exception as e:                       # network / provider errors
                print(f"LLM error: {type(e).__name__}: {e}")
                bot_msg = {"role": "assistant",
                           "content": "Sorry, I couldn't reach my language model just now. Please try again."}
        ss.messages.append(bot_msg)
        ss.count += 1
        show_message(bot_msg)

    run_in_browser(bot_msg["content"] if speak else None, lang, VOICES[lang],
                   [a["url"] for a in bot_msg.get("actions", [])])
