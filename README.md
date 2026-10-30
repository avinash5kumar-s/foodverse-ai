# 🍽️ Food Verse AI — Multimodal Food Intelligence Agent

Food Verse AI is a Groq-powered agent that understands food from **photos and text**.
Send a picture of your plate (or just describe it) and it identifies the items, estimates
portions, computes calories and macros with real tools, checks diet fit, and suggests swaps.

## How it works

```
 photo / text ──► Groq vision model ──► identifies foods + portion estimates
                       │
                       ▼  tool-use loop
        analyze_meal · lookup_food · check_diet · suggest_swaps
                       │
                       ▼
            concise answer with totals + suggestions
```

- **Vision**: images are validated, downscaled (max 1568 px) and sent to Groq.
- **Tools**: nutrition math is done in Python against a built-in database, not guessed by the model.
  Foods not in the database come back as `unmatched`, and the model labels its own estimates as such.
- **Diet checks**: vegetarian, vegan, high-protein, low-carb, low-fat.
- **Swaps**: lower-calorie, higher-protein or higher-fibre alternatives.

## Project layout

```
foodverse-ai/
├── app.py                 # FastAPI app = Vercel entrypoint (exports `app`)
├── streamlit_app.py       # Streamlit UI (local use only)
├── vercel.json
├── cli.py                 # Command-line interface
├── foodverse/
│   ├── web.py             # Framework-free request logic
│   ├── page.py            # Single-page HTML UI
│   ├── agent.py           # Groq function-calling loop
│   ├── tools.py           # Tool schemas + implementations
│   ├── nutrition_db.py    # Built-in per-100g nutrition data (~50 foods, many Indian staples)
│   ├── vision.py          # Image validation / resize / encoding
│   ├── schemas.py         # Pydantic models
│   └── config.py          # Env-based settings
├── tests/test_foodverse.py
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt     # includes Streamlit, uvicorn and pytest
copy .env.example .env     # Windows: then put your GROQ_API_KEY in .env
```

## Run

Web app (same FastAPI app that runs on Vercel):
```bash
uvicorn app:app --reload        # open http://127.0.0.1:8000
```

Streamlit UI (local only, it cannot be deployed to Vercel):
```bash
python -m streamlit run streamlit_app.py
```

CLI:
```bash
python cli.py "2 chapati, a bowl of dal and some paneer"
python cli.py --image meal.jpg "is this high protein?" --show-tools
python cli.py --interactive
```

Python:
```python
from foodverse import FoodVerseAgent
agent = FoodVerseAgent()
print(agent.ask_file("meal.jpg", "Is this vegetarian? Total calories?").text)
```

## Tests

```bash
pytest -q
```
The tests cover the database, every tool, image preparation, and the full agent loop using a
fake client, so they need **no API key and no network**.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key | required |
| `FOODVERSE_MODEL` | Groq model ID | `qwen/qwen3.8-27b` |

## Limitations & next steps

- Portion sizes from photos are estimates; treat calories as approximate.
- The built-in database is small. For production, back `lookup_food` with USDA FoodData Central
  or IFCT (Indian Food Composition Tables).
- Not medical advice. Allergies and clinical diets need a qualified professional.
- Ideas: meal logging with daily totals, barcode/label reading, recipe generation from a fridge photo,
  streaming responses in the UI.


## Groq API setup

Create an API key at https://console.groq.com/keys and place it in `.env` as `GROQ_API_KEY=...`. The default model is `qwen/qwen3.8-27b`, which supports both image input and tool use on Groq. Keep `.env` private and never commit it.


## Deploy to Vercel

Streamlit needs a long-running server, which Vercel's serverless functions don't provide. That is
why deploying the old `app.py` failed with `PYTHON_ENTRYPOINT_NOT_FOUND`. `app.py` is now a FastAPI
app that exports `app`, and the Streamlit UI moved to `streamlit_app.py`.

1. Push this folder to GitHub (make sure `.env` is not committed) and import it in Vercel, or run `vercel` from this folder.
2. In **Project Settings → Environment Variables** add `GROQ_API_KEY` (and optionally `FOODVERSE_MODEL`). Redeploy after adding it.
3. Open the deployment URL. The page is served at `/`, the API at `POST /api/analyze`, and `GET /api/health` is a quick check.

Notes: `vercel.json` sets a 60 s function timeout (the vision + tool loop can take a while; Hobby plans cap
this, so lower it if the deploy complains). Photos are shrunk in the browser to stay under Vercel's ~4.5 MB request limit.
