
import json
import os
import re
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "quotes.json"
DATA_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add your key to the .env file."
    )

client = genai.Client(api_key=API_KEY)
history_lock = threading.Lock()


class QuoteResponse(BaseModel):
    theme: str = Field(
        description="A meaningful 2 to 5 word title with one relevant emoji"
    )
    quote: str = Field(
        description="A thoughtful, engaging English motivational message"
    )
    hindiLine: str = Field(
        description="A natural and simple Hindi translation in Devanagari"
    )
    closing: str = Field(
        description="A memorable one-line morning closing with suitable emojis"
    )


SYSTEM_PROMPT = """
You are a thoughtful and creative morning-message writer for the
Sanskar Family community.

Create original, meaningful, emotionally engaging morning messages.
The writing should feel like it was written by a thoughtful human,
not a generic motivational quote generator.

Return ONLY valid JSON with exactly these four string fields:
theme, quote, hindiLine, closing.

Do not include the greeting. The application adds the greeting separately.

THEME:
- A meaningful title of 5 to 6 words.
- Add one relevant emoji at the end.
- Make it attractive,simple, specific, and connected to the message.

ENGLISH QUOTE:
- Write simple approximately 15 to 25 words.
- Use 1 or 2 meaningful sentences.
- Make it insightful, relatable, polished, and emotionally engaging.
- Explain one clear idea through an everyday-life situation.
- It should inspire reflection and practical action.
- Avoid clichés, copied sayings, and overused motivational slogans.
- Do not include an author name.
- Do not use emojis in the English quote.

HINDI TRANSLATION:
- Write in natural, simple,daily usuage Hindi.
- Use 1 or 2 short sentences.
- Convey the meaning of the English quote accurately.
- Make it easy for an ordinary Hindi learner to understand.
- Avoid difficult vocabulary and unnatural literal translations.

CLOSING:
- Write one memorable, uplifting line.
- Use 2 or 3 short phrases or sentences.
- Make it practical and suitable for a morning message.
- Add 1 or 2 relevant emojis.
- Do not simply repeat the English quote.

GENERAL RULES:
- The topic must guide the message.
- Use fresh examples and perspectives.
- Do not repeat or closely imitate previous messages.
- Keep the tone warm, positive, professional, and meaningful.
- Return JSON only. No Markdown or code fences.
"""


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(items):
    temp_file = HISTORY_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temp_file.replace(HISTORY_FILE)


def word_count(value):
    return len(re.findall(r"\b[\w’'-]+\b", value, flags=re.UNICODE))


def validate_quote(data, previous_quotes):
    required = {"theme", "quote", "hindiLine", "closing"}

    if not isinstance(data, dict) or set(data.keys()) != required:
        return False, "The response did not contain the required fields."

    if not all(
        isinstance(data[key], str) and data[key].strip()
        for key in required
    ):
        return False, "Every field must contain non-empty text."

    if not 2 <= word_count(data["theme"]) <= 5:
        return False, "The theme must contain 2 to 5 words."

    if not 20 <= word_count(data["quote"]) <= 45:
        return False, "The English quote must contain approximately 25 to 40 words."

    for key in required:
        if "\n" in data[key] or "\r" in data[key]:
            return False, f"{key} must be a single line."

    normalized = re.sub(
        r"\s+", " ", data["quote"].lower()
    ).strip()

    for old_quote in previous_quotes:
        old = re.sub(
            r"\s+", " ", str(old_quote).lower()
        ).strip()

        if old and (
            normalized == old
            or SequenceMatcher(None, normalized, old).ratio() >= 0.78
        ):
            return False, "This message is too similar to a previous one."

    return True, ""


def generate_quote(topic, context):
    with history_lock:
        previous_quotes = [
            item.get("quote", "")
            for item in load_history()[-30:]
        ]

    previous_text = "\n".join(
        f"- {quote}" for quote in previous_quotes
    ) or "None yet."

    user_prompt = f"""
Create one complete morning message for the Sanskar Family.

TOPIC:
{topic}

ADDITIONAL CONTEXT:
{context or "Choose a meaningful and relatable everyday-life perspective."}

PREVIOUS ENGLISH QUOTES TO AVOID:
{previous_text}

Remember:
- Theme: 2 to 5 words and one relevant emoji.
- English quote: approximately 15 to 25 words.
- Hindi translation: simple, natural Devanagari.
- Closing: one memorable line with suitable emojis.
- Return exactly four JSON fields.
"""

    last_error = "The AI response did not pass validation."

    for attempt in range(3):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=QuoteResponse,
                temperature=0.9,
                max_output_tokens=700,
            ),
        )

        try:
            result = json.loads(response.text or "")
            result = {
                key: result[key].strip()
                for key in ("theme", "quote", "hindiLine", "closing")
            }
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            last_error = "Gemini returned an invalid JSON response."
            user_prompt += "\nReturn valid JSON with exactly four fields."
            continue

        valid, reason = validate_quote(result, previous_quotes)

        if valid:
            return result

        last_error = reason
        user_prompt += (
            f"\nYour previous response failed validation: {reason} "
            "Generate a fresh message and follow every rule."
        )

    raise ValueError(last_error)


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/generate-quote")
def api_generate_quote():
    payload = request.get_json(silent=True) or {}

    topic = str(payload.get("topic", "personal growth")).strip()[:160]
    context = str(payload.get("context", "")).strip()[:500]

    if not topic:
        return jsonify({"error": "Please enter a topic."}), 400

    try:
        quote = generate_quote(topic, context)

        entry = {
            **quote,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }

        with history_lock:
            items = load_history()
            items.append(entry)
            save_history(items[-100:])

        return jsonify(entry)

    except Exception as exc:
        app.logger.exception("Quote generation failed")

        error_text = str(exc)
        status_code = (
            getattr(exc, "code", None)
            or getattr(exc, "status_code", None)
        )

        if status_code == 429 or "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
            return jsonify({
                "error": "Gemini's request limit may have been reached. Please wait and try again."
            }), 429

        if status_code == 503 or "503" in error_text or "UNAVAILABLE" in error_text:
            return jsonify({
                "error": "Gemini is temporarily busy. Please wait a few minutes and try again."
            }), 503

        return jsonify({
            "error": "Could not generate the message. Please check your API settings and try again."
        }), 500


@app.get("/api/quotes")
def api_quotes():
    with history_lock:
        items = load_history()

    return jsonify(list(reversed(items)))


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )
