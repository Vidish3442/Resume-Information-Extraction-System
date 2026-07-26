"""
FastAPI server for the Resume Information Extraction System.

Endpoints:
  POST /parse   — Upload a PDF or DOCX resume, returns structured JSON.
  GET  /health  — Health check.

Run with:
  C:\\Users\\vidis\\anaconda3\\python.exe -m uvicorn api:app --reload --port 8000
"""

import io
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from extractor import extract_resume_info
from parser import extract_text_from_file, extract_pdf_annotations
from utils import clean_text

app = FastAPI(
    title="Resume Information Extraction API",
    description="Upload a PDF or DOCX resume and receive structured JSON with extracted fields.",
    version="1.0.0",
)

# Allow the Streamlit frontend (any origin in dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@app.get("/health", tags=["meta"])
def health_check():
    """Returns 200 OK when the service is running."""
    return {"status": "ok"}


@app.post("/parse", tags=["resume"], response_class=JSONResponse)
async def parse_resume(file: UploadFile = File(...)):
    """
    Upload a PDF or DOCX resume file.

    Returns a JSON object with the following fields:
    - full_name, email, phone, linkedin, github  (str | null)
    - skills, education, work_experience          (list[str])
    - metadata                                    (source_file, file_type)
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{suffix}'. Please upload a .pdf or .docx file.",
        )

    # Read upload into a temp file so pdfplumber / python-docx can open it by path
    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        raw_text = extract_text_from_file(tmp_path)
        annotations = extract_pdf_annotations(tmp_path) if suffix == ".pdf" else {}
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")

    tmp_path.unlink(missing_ok=True)

    text = clean_text(raw_text)
    result = extract_resume_info(text if text.strip() else "", annotations=annotations)

    # Attach lightweight metadata
    result["metadata"] = {
        "source_file": file.filename,
        "file_type": suffix,
    }

    return JSONResponse(content=result)
