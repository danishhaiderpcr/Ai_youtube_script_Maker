# 🎬 YouTube Script Generator

Enter a topic title and get a structured, ready-to-record YouTube script written by Google's Gemini Flash model. Built with Streamlit.

## Features

- Script structure: Hook, Intro, Main Content, Call to Action, Outro
- Accuracy-focused: low temperature, strict "never invent facts" instructions, and optional **Google Search grounding** with source links
- **Fact-check notes** section listing claims you should verify before publishing
- Controls for video length, tone, language, target audience and extra instructions
- Optional visual/B-roll cues and section timestamps
- Title ideas, description and tags for the video
- Download the script as a Markdown file

## Project structure

```
.
├── app.py             # Streamlit app
├── requirements.txt   # Python dependencies
└── README.md
```

## Run locally

1. Install Python 3.9 or newer.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).
4. Provide the key in **one** of these ways:
   - Create `.streamlit/secrets.toml` next to `app.py`:
     ```toml
     GEMINI_API_KEY = "your-api-key-here"
     ```
   - or set an environment variable: `export GEMINI_API_KEY="your-api-key-here"`
   - or paste it into the sidebar when the app is running.
5. Start the app:
   ```bash
   streamlit run app.py
   ```

> Never commit your API key or `.streamlit/secrets.toml` to GitHub.

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository (`app.py`, `requirements.txt`, `README.md`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **Create app**, choose your repository and branch, and set **Main file path** to `app.py`.
4. Open **Advanced settings → Secrets** and add:
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
5. Click **Deploy**.

## Settings

| Setting | Where | Notes |
|---|---|---|
| Gemini model | Sidebar | Default `gemini-2.5-flash`. Change it if Google releases a newer Flash model. |
| Google Search grounding | Sidebar | On by default. If unavailable for your key, the app falls back to a normal script and shows a warning. |

## Troubleshooting

- **"Gemini rejected the API key"**: check the key and make sure it is saved in secrets without extra spaces or quotes.
- **"Rate limit or quota reached"**: the free tier has per-minute and daily limits. Wait and retry.
- **"Model not found"**: update the model name in the sidebar.
- **Empty response**: the topic may have triggered safety filters. Reword it.

## Disclaimer

AI can still make mistakes. Always verify names, numbers, dates and sensitive claims before publishing a video.
