"""YouTube Script Generator
Enter a topic title and get a ready-to-record YouTube script written by Gemini Flash.

Run locally:  streamlit run app.py
"""

import os
import re

import streamlit as st
from google import genai
from google.genai import types

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-3.8-flash"  # change in the sidebar if Google releases a newer Flash model
WORDS_PER_MINUTE = 150  # average speaking pace for narration
MAX_TOPIC_CHARS = 200
TEMPERATURE = 0.4  # lower = fewer made-up details

TONES = [
    "Conversational",
    "Educational",
    "Entertaining",
    "Professional",
    "Motivational",
    "Storytelling",
]
LANGUAGES = ["English", "Urdu", "Hindi", "Arabic", "Spanish", "French", "German"]

SYSTEM_INSTRUCTION = """You are an expert YouTube scriptwriter and fact-checker.

Accuracy rules (very important):
- State only facts you are confident are true. Never invent statistics, quotes, dates, names, studies, products or sources.
- If a fact is uncertain or cannot be verified, leave it out or flag it inline with [VERIFY].
- Prefer well-established claims over precise numbers unless you can support them.
- If the topic is very recent or you lack reliable information, say so in the Fact-check notes instead of guessing.
- For medical, legal or financial topics, keep claims general and add one short responsible-use note.

Writing rules:
- Write for the ear: short sentences, natural spoken language, no filler.
- Open with a strong hook, keep viewers curious, and give every section a clear purpose.
- Output clean Markdown only, following the structure the user gives you.
"""


# ----------------------------------------------------------------------------
# Helpers (no Streamlit calls, so they are easy to test)
# ----------------------------------------------------------------------------
def build_prompt(topic, minutes, tone, audience, language, notes, visual_cues, timestamps):
    """Build the user prompt sent to Gemini."""
    words = minutes * WORDS_PER_MINUTE
    lines = [
        f'Write a complete YouTube video script for this topic: "{topic}"',
        "",
        "Requirements:",
        f"- Length: about {minutes} minute(s) of spoken narration (roughly {words} words, +/- 10%).",
        f"- Tone: {tone}.",
        f"- Target audience: {audience.strip() or 'general YouTube viewers'}.",
        f"- Language: {language}.",
    ]
    if timestamps:
        lines.append("- Put an approximate timestamp like [00:45] at the start of each section.")
    if visual_cues:
        lines.append(
            "- Add short visual suggestions (B-roll, on-screen text, graphics) in square brackets on their "
            "own line, e.g. [B-roll: ...]. These do not count toward the word target."
        )
    if notes.strip():
        lines.append(f"- Extra instructions from the creator: {notes.strip()}")

    lines += [
        "",
        "Use exactly this Markdown structure:",
        "## Hook (first 15 seconds)",
        "## Intro",
        "## Main Content (split into 3-6 titled sections, each with one clear takeaway)",
        "## Call to Action",
        "## Outro",
        "## Fact-check Notes (list the key factual claims the creator should double-check; "
        "if none, write 'No high-risk claims.')",
        "## YouTube Package (3 title ideas, a 2-3 sentence description, 5-8 tags)",
    ]
    return "\n".join(lines)


def narration_word_count(text):
    """Approximate spoken words: ignore headings and [bracketed] cues."""
    text = re.sub(r"\[[^\]]*\]", " ", text)
    kept = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    return len(" ".join(kept).split())


def extract_sources(response):
    """Return a de-duplicated list of {'title', 'uri'} from Google Search grounding."""
    sources, seen = [], set()
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return sources
        meta = getattr(candidates[0], "grounding_metadata", None)
        for chunk in getattr(meta, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None)
            if uri and uri not in seen:
                seen.add(uri)
                sources.append({"title": getattr(web, "title", None) or uri, "uri": uri})
    except Exception:
        pass  # sources are a bonus; never break the app because of them
    return sources


def generate_script(client, model, prompt, use_search):
    """Call Gemini. Returns {'text', 'sources', 'grounded', 'note'}."""

    def _call(with_search):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=TEMPERATURE,
            tools=[types.Tool(google_search=types.GoogleSearch())] if with_search else None,
        )
        return client.models.generate_content(model=model, contents=prompt, config=config)

    note = ""
    grounded = use_search
    try:
        response = _call(use_search)
    except Exception as first_error:
        if not use_search:
            raise
        # Search grounding can fail (quota, region, plan). Retry once without it.
        response = _call(False)
        grounded = False
        note = (
            "Google Search grounding was unavailable, so this script was written without live "
            f"web data. Double-check the facts. ({type(first_error).__name__})"
        )

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise ValueError(
            "The model returned an empty response (it may have been blocked by safety filters). "
            "Try rewording the topic."
        )
    return {
        "text": text,
        "sources": extract_sources(response) if grounded else [],
        "grounded": grounded,
        "note": note,
    }


def friendly_error(exc):
    """Turn API errors into short, readable messages."""
    msg = str(exc)
    low = msg.lower()
    if "api key" in low or "api_key" in low or "401" in low or "403" in low or "permission" in low:
        return "Gemini rejected the API key. Check that it is correct and enabled."
    if "429" in low or "quota" in low or "resource_exhausted" in low or "rate limit" in low:
        return "Rate limit or quota reached. Wait a minute and try again."
    if "404" in low or "not found" in low:
        return "Model not found. Check the model name in the sidebar."
    return f"Something went wrong: {msg}"


def get_api_key():
    """Look for the key in Streamlit secrets first, then environment variables."""
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        key = None  # no secrets file configured
    return key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def slugify(text):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:50] or "script"


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="YouTube Script Generator", page_icon="🎬", layout="wide")
    st.title("🎬 YouTube Script Generator")
    st.caption("Enter a topic title and get a structured, fact-conscious video script powered by Gemini Flash.")

    api_key = get_api_key()
    with st.sidebar:
        st.header("Settings")
        if not api_key:
            api_key = st.text_input("Gemini API key", type="password", help="Get one free at aistudio.google.com")
        model = st.text_input("Gemini model", value=DEFAULT_MODEL).strip() or DEFAULT_MODEL
        use_search = st.toggle(
            "Ground with Google Search",
            value=True,
            help="Lets Gemini check live web information. Recommended for accuracy.",
        )
        st.info("Always fact-check names, numbers and dates before publishing.")

    with st.form("script_form"):
        topic = st.text_input(
            "Video topic / title",
            max_chars=MAX_TOPIC_CHARS,
            placeholder="e.g. How does the stock market actually work?",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            minutes = st.slider("Video length (minutes)", 1, 30, 8)
        with col2:
            tone = st.selectbox("Tone", TONES)
        with col3:
            language = st.selectbox("Language", LANGUAGES)
        audience = st.text_input("Target audience (optional)", placeholder="e.g. beginners, students, small business owners")
        notes = st.text_area("Extra instructions (optional)", placeholder="e.g. include a short story, avoid jargon, mention my channel name")
        opt1, opt2 = st.columns(2)
        with opt1:
            visual_cues = st.checkbox("Add visual / B-roll cues", value=True)
        with opt2:
            timestamps = st.checkbox("Add section timestamps", value=True)
        submitted = st.form_submit_button("Generate script", type="primary")

    if submitted:
        topic = topic.strip()
        if not topic:
            st.error("Please enter a topic title.")
        elif not api_key:
            st.error("Please add your Gemini API key in the sidebar or in Streamlit secrets.")
        else:
            try:
                with st.spinner("Researching and writing your script..."):
                    client = genai.Client(api_key=api_key)
                    prompt = build_prompt(topic, minutes, tone, audience, language, notes, visual_cues, timestamps)
                    result = generate_script(client, model, prompt, use_search)
                result["topic"] = topic
                st.session_state["result"] = result
            except Exception as exc:
                st.error(friendly_error(exc))

    result = st.session_state.get("result")
    if result:
        st.divider()
        words = narration_word_count(result["text"])
        m1, m2 = st.columns(2)
        m1.metric("Narration words (approx.)", f"{words:,}")
        m2.metric("Estimated speaking time", f"{words / WORDS_PER_MINUTE:.1f} min")

        if result["note"]:
            st.warning(result["note"])
        st.markdown(result["text"])

        if result["sources"]:
            with st.expander(f"Sources used by Google Search ({len(result['sources'])})"):
                for src in result["sources"]:
                    st.markdown(f"- [{src['title']}]({src['uri']})")

        st.download_button(
            "Download script (.md)",
            data=result["text"],
            file_name=f"{slugify(result['topic'])}-script.md",
            mime="text/markdown",
        )
        with st.expander("Copy-friendly plain text"):
            st.code(result["text"], language=None)


if __name__ == "__main__":
    main()
