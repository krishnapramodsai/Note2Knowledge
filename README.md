# NotesGenius AI — Vercel Edition

This version converts the original Streamlit application into a Vercel-compatible
web app:

- `index.html` — browser UI
- `api/index.py` — FastAPI serverless API
- `ai_engine.py` — original AI/study-pack engine
- `extractor.py` — PDF/TXT/MD extraction
- `vercel.json` — Vercel function/rewrite configuration

## Deploy

1. Push this folder to GitHub.
2. Import the repository into Vercel.
3. Keep the project root as this folder.
4. Deploy.

For real AI generation, add one of these in **Vercel → Project → Settings → Environment Variables**:

- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

You can also enter a key in the UI, but environment variables are preferable.

For a no-key hackathon demo, choose **Demo Mode (Offline / No Key)**.

## Local test

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Then open `index.html` through a local static server, or deploy to Vercel.

## Important OCR note

The original Windows app used the local Tesseract executable for image OCR.
Vercel's Python serverless runtime does not provide that Windows binary, so PDF,
TXT and MD extraction are the reliable Vercel path. If image OCR is required,
replace the Tesseract step with a hosted OCR/vision API.

The original Streamlit UI is preserved as `app_streamlit_backup.py`.
