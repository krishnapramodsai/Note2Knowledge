
import sys
from pathlib import Path
from typing import Optional
 
# Make ai_engine.py and extractor.py (repo root) importable on Vercel
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
 
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse
 
from ai_engine import generate_study_package
from extractor import extract_text
 
app = FastAPI(title="NotesGenius AI API", version="1.0.0")
 
 
@app.get("/")
def home():
    index_file = ROOT / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)
 
 
# Registered under several paths so it works no matter how Vercel
# forwards the URL to this function.
@app.get("/api/health")
@app.get("/health")
@app.get("/api/index")
def health():
    return {"ok": True, "service": "NotesGenius AI", "status": "running"}
 
 
@app.post("/api/generate")
@app.post("/generate")
@app.post("/api/index")
@app.post("/api/index.py")
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
                raise HTTPException(status_code=413, detail="File too large (max 8 MB).")
            try:
                extracted = extract_text(file.filename, data)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not extract text: {exc}")
            source_text = (source_text + "\n\n" + extracted).strip()
 
        if not source_text:
            raise HTTPException(status_code=400, detail="Paste notes or upload a PDF/TXT/MD file first.")
 
        source_text = source_text[:60000]
 
        package = generate_study_package(
            source_text, provider=provider, api_key=api_key, model=model
        )
        return JSONResponse({"ok": True, "package": package})
 
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Study pack generation failed: {exc}") from exc
 
 
# Debug catch-all: shows the exact path Vercel passed, instead of a bare "Not Found"
@app.api_route("/{full_path:path}", methods=["GET", "POST"])
async def catch_all(full_path: str, request: Request):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Not Found. Function received {request.method} /{full_path}"},
    )
