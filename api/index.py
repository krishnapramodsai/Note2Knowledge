"""
Vercel entry point for NotesGenius AI.

The original Streamlit app is kept as app_streamlit_backup.py.
This FastAPI layer exposes the same core functionality through /api/generate,
which is suitable for Vercel serverless deployment.
"""
import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ai_engine import generate_study_package
from extractor import extract_text

app = FastAPI(title="NotesGenius AI API", version="1.0.0")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "NotesGenius AI"}


@app.post("/api/generate")
async def generate(
    notes: str = Form(""),
    provider: str = Form("Auto-Detect"),
    api_key: str = Form(""),
    model: str = Form(""),
    file: Optional[UploadFile] = File(None),
):
    try:
        source_text = (notes or "").strip()

        if file is not None and file.filename:
            data = await file.read()
            if len(data) > 8 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File is too large. Maximum size is 8 MB.")
            try:
                extracted = extract_text(file.filename, data)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            source_text = (source_text + "\n\n" + extracted).strip()

        if not source_text:
            raise HTTPException(
                status_code=400,
                detail="Paste notes or upload a PDF/TXT/MD/image file first.",
            )

        # Keep request sizes reasonable for a serverless function.
        source_text = source_text[:60000]

        package = generate_study_package(
            source_text,
            provider=provider,
            api_key=api_key,
            model=model,
        )
        return JSONResponse({"ok": True, "package": package})

    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose API keys or internal stack traces.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
