import sys
from pathlib import Path
from typing import Optional

# Let Python find ai_engine.py and extractor.py in the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ai_engine import generate_study_package
from extractor import extract_text


app = FastAPI(
    title="Note2Knowledge API",
    version="1.0.0",
)


# =========================
# FRONTEND
# =========================

@app.get("/")
def home():
    index_file = Path(__file__).resolve().parent.parent / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend index.html not found"
        )

    return FileResponse(index_file)


# =========================
# HEALTH CHECK
# =========================

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "Note2Knowledge",
        "status": "running"
    }


# =========================
# GENERATE STUDY PACK
# =========================

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

        # Uploaded file
        if file is not None and file.filename:
            file_bytes = await file.read()

            if len(file_bytes) > 8 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="File is too large. Maximum size is 8 MB."
                )

            try:
                extracted_text = extract_text(file.filename, file_bytes)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not extract text: {exc}"
                ) from exc

            if extracted_text:
                if source_text:
                    source_text += "\n\n" + extracted_text
                else:
                    source_text = extracted_text

        # Validate notes
        if not source_text:
            raise HTTPException(
                status_code=400,
                detail="Paste notes or upload a PDF/TXT/MD file first."
            )

        # Prevent very large requests
        source_text = source_text[:60000]

        package = generate_study_package(
            source_text,
            provider=provider,
            api_key=api_key,
            model=model,
        )

        return JSONResponse(content={"ok": True, "package": package})

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Study pack generation failed: {exc}"
        ) from exc
