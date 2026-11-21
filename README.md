# Morning Quote Generator

A Python + Flask AI application that creates original morning motivational messages in English and simple Hindi using Google's Gemini API.

## Features

- AI-generated theme, quote, Hindi translation, practical explanation, and closing line
- Enforces an 8–9 word, single-line English quote
- Requests exactly five JSON fields
- Checks generated quotes against recent history to reduce repetition
- Stores the latest 100 generated messages locally
- Responsive frontend with copy and history features
- API key stored in `.env`, not in frontend code

## Requirements

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup on Windows

Open Command Prompt in this project folder:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API key:

```env
GEMINI_API_KEY=your_actual_key
GEMINI_MODEL=gemini-3.8-flash
PORT=5000
FLASK_DEBUG=false
```

Never commit `.env` or share your API key.

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000

## API endpoints

- `POST /api/generate-quote` — JSON body: `{"topic":"discipline","context":"..."}`
- `GET /api/quotes` — returns saved quote history

## Notes

Gemini API free-tier availability and rate limits depend on the model, account, and region. Check current limits in Google AI Studio. The app does not enable paid billing automatically.
