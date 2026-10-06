# Nova: a cloud LLM voice assistant for the web

Nova is a voice assistant you can use from **any device with a browser**: phone, laptop or tablet.
You speak (or type), a **cloud LLM on Azure OpenAI** decides what to do using **function calling**,
Nova runs the right tools, and the answer is **read back to you aloud**.

**🔗 Live demo:** [nova-voice.streamlit.app](https://nova-voice.streamlit.app) · works on phone and desktop (Chrome, Edge or Safari for voice)

```
 🎤 visitor's browser                        ☁️ Streamlit app (server)                    🌐 services
 ────────────────────                        ─────────────────────────                    ───────────
 speech → text (Web Speech API) ───────────► Agent loop ◄──────► Azure OpenAI (function calling)
                                              │  LLM picks tools + JSON args, up to 5 steps
                                              ├─ get_weather ──────────────────────────► Open-Meteo
                                              ├─ web_search ───────────────────────────► DuckDuckGo / Tavily
                                              ├─ calculate (safe AST), get_datetime (visitor's timezone)
                                              └─ open_website / play_music / open_search_page
                                                         │  returned as "actions"
 text → speech (speechSynthesis) ◄── reply ───┘
 new tab opens on the visitor's device ◄── actions
```

## Features

- **Talk or type** from any modern browser. Speech recognition and the voice both run in the browser,
  so there's no audio upload, no extra API cost and no heavy speech model on the server.
- **Cloud function calling**: the LLM chooses among 7 tools and fills in their arguments as typed JSON,
  including several tools in one request (*"weather in Pune and what's 15% of 840?"*).
- **Live web answers**: searches the internet and summarises the results aloud, rather than only opening a tab.
- **Actions on your own device**: "play some lofi" or "open GitHub" opens a new tab for whoever is using it,
  not on the server. A button is also shown in case the browser blocks pop-ups.
- **Correct local time** for every visitor (timezone comes from their browser).
- **Session memory**: follow-up questions work. Nothing is stored after the page is closed.
- **Bilingual**: English and Hindi for voice input and spoken replies.
- **Safe for a public link**: optional access code, a per-session message cap, maths without `eval()`,
  and web results treated as untrusted data.

## Tools

| Tool | What it does | Runs on |
|---|---|---|
| `get_weather` | Current weather + today/tomorrow forecast (Open-Meteo, no key) | server |
| `web_search` | Top web results for news, prices, scores, recent events | server |
| `calculate` | Exact arithmetic through a whitelisted syntax tree | server |
| `get_datetime` | Date and time in the visitor's timezone | server |
| `open_website` | Opens a site (youtube, github, any domain) | visitor's browser |
| `play_music` | Opens YouTube results for a song, artist or mood | visitor's browser |
| `open_search_page` | Opens a Google results page | visitor's browser |

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your Azure endpoint, key and deployment name

streamlit run app.py          # web app with voice -> http://localhost:8501
python main.py --verbose      # terminal mode: shows tool calls, tokens and latency
```

## Put it online (free): Streamlit Community Cloud

1. Push this folder to a **GitHub** repository. `.env` is git-ignored, so check that it is **not** in the repo.
2. Go to **share.streamlit.io** → sign in with GitHub → **Create app** → pick the repo, branch, and `app.py`.
3. Open **Advanced settings → Secrets** and paste your settings in TOML format:
   ```toml
   LLM_BASE_URL = "https://<your-resource>.openai.azure.com/openai/v1/"
   LLM_API_KEY = "<your key>"
   CHAT_MODEL = "<your deployment name>"
   MAX_MESSAGES_PER_SESSION = "40"
   # ACCESS_CODE = "something-only-friends-know"
   # TAVILY_API_KEY = "<optional>"
   ```
4. **Deploy.** You get a public `https://<name>.streamlit.app` link that works on phones and laptops.
   The site is served over HTTPS, which browsers require before they allow microphone access.

**Protect your Azure credit:** set a budget alert in Azure (Cost Management → Budgets), keep
`MAX_MESSAGES_PER_SESSION` low, and set an `ACCESS_CODE` if you share the link widely.

## Project structure

```
app.py               Streamlit web app: chat UI, mic button, spoken replies, browser actions
main.py              terminal mode for quick testing
assistant/
  agent.py           agent loop: LLM ⇄ tools, session history, token/latency tracking
  tools.py           7 tools + JSON schemas, web search, safe maths
  config.py          settings from .env or Streamlit secrets (any OpenAI-compatible endpoint)
  factory.py         wires the client, tools and agent together
.streamlit/config.toml   theme
```

## Design decisions

- **Speech in the browser, intelligence in the cloud.** The Web Speech API costs nothing, adds no latency for
  uploading audio, and keeps the server small. Only the text goes to the LLM.
- **Server tools vs. client actions.** Tools that need data run on the server. Tools that act on a device
  return an *action* that the visitor's browser carries out, so Nova behaves correctly for every user.
- **Temperature 0:** tool choice should be consistent, not creative.
- **Tools never crash the conversation:** errors go back to the LLM as `{"error": ...}`, and it explains them.
- **Max 5 agent steps:** prevents runaway loops and cost.
- **Provider-agnostic:** the OpenAI SDK talks to Azure's v1 endpoint, so changing three settings switches providers.

## Browser support

Voice input works in Chrome, Edge and Safari (desktop and mobile). Firefox doesn't support the
Web Speech API's recognition, so visitors there can type instead. Spoken replies work everywhere.
