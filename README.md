# Resume Information Extraction System

A lightweight Python tool that converts unstructured PDF and DOCX resumes into structured JSON — no LLM, no OCR, no cloud service required. Includes a FastAPI backend and a Streamlit web UI for interactive use.

---

## Features

- Extracts **name, email, phone, skills, education, certifications, LinkedIn, GitHub, and work experience**
- Reads **PDF hyperlink annotations** to reliably extract URLs and phone numbers from modern LaTeX-style CVs (where URLs are icons, not plain text)
- Section-aware extraction for **Experience** and **Certifications** — avoids polluting results with summary paragraphs or skill lists
- FastAPI REST endpoint (`POST /parse`) for programmatic access
- Streamlit web UI for drag-and-drop resume parsing
- Full test suite: 41 unit, property-based (Hypothesis), and integration tests

---

## Project Structure

```
resumeaiparser/
├── app.py              # CLI entry point
├── ui.py               # Streamlit web UI
├── parser.py           # Document_Reader — PDF/DOCX text + annotation extraction
├── extractor.py        # All extraction logic (regex, spaCy NER, section parsing)
├── utils.py            # Text preprocessor + helper functions
├── skills.txt          # Skill dictionary (one skill per line)
├── requirements.txt    # Pinned dependencies
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_utils.py
│   ├── test_extractor.py
│   ├── test_properties.py  # Hypothesis property-based tests
│   └── test_integration.py
├── sample_resumes/     # Place test resumes here (gitignored)
└── output/             # JSON results written here (gitignored)
```

---

## Setup

### 1. Prerequisites

This project requires the **Anaconda Python** environment (or any Python 3.11+). All commands below use the full path to the Anaconda interpreter — adjust to your own Python if different.

### 2. Install dependencies

```bash
C:\Users\<you>\anaconda3\python.exe -m pip install -r requirements.txt
```

### 3. Download the spaCy model

Required for name extraction via Named Entity Recognition. The system falls back to a title-case heuristic if the model is absent, but accuracy is better with it.

```bash
C:\Users\<you>\anaconda3\python.exe -m spacy download en_core_web_sm
```

---

## Usage

### Option A — Command Line

Parse a single resume and print JSON to stdout:

```bash
C:\Users\<you>\anaconda3\python.exe app.py sample_resumes/resume.pdf
```

Save to a custom output path:

```bash
C:\Users\<you>\anaconda3\python.exe app.py sample_resumes/resume.docx -o results/john_doe.json
```

Output is always written to `output/<stem>.json` by default if `-o` is not specified.

### Option B — Web UI (Streamlit)

```bash
C:\Users\<you>\anaconda3\python.exe -m streamlit run ui.py
```

Open **http://localhost:8501** in your browser. Upload a PDF or DOCX resume, and the extracted fields are displayed in a structured layout. A **Download JSON** button is provided for saving the result.

---

## JSON Output Schema

```json
{
  "full_name": "Vidish Kumar",
  "email": "vidishkumar890@gmail.com",
  "phone": "+919654403155",
  "skills": ["Deep Learning", "Git", "Machine Learning", "Python", "Sql"],
  "education": [
    "2023 – 2027 Bachelor of Technology (Computer Science and Business Systems)"
  ],
  "certifications": [
    "Design Thinking for Innovation – University of Virginia",
    "Databases and SQL for Data Science with Python – IBM",
    "Machine Learning for All – University of London"
  ],
  "linkedin": "https://www.linkedin.com/in/vidishkumar/",
  "github": "https://github.com/Vidish3442",
  "work_experience": [
    "Infosys Springboard – Internship 6.0 Dec 2025 – Feb 2026"
  ],
  "metadata": {
    "source_file": "resume.pdf",
    "file_type": ".pdf"
  }
}
```

Missing fields appear as `null` (scalars) or `[]` (lists) — never omitted.

---

## Running Tests

Run the full test suite (41 tests):

```bash
C:\Users\<you>\anaconda3\python.exe -m pytest tests/ -v
```

Run a specific file:

```bash
C:\Users\<you>\anaconda3\python.exe -m pytest tests/test_extractor.py -v
C:\Users\<you>\anaconda3\python.exe -m pytest tests/test_properties.py -v
```

---

## Approach

### Extraction pipeline

```
Resume (PDF / DOCX)
  └─► parser.py
        ├─ pdfplumber  → raw text (text layer)
        ├─ pdfplumber  → hyperlink annotations (URIs embedded in PDF)
        └─ python-docx → paragraph text
  └─► utils.py         → normalise whitespace, strip null bytes
  └─► extractor.py
        ├─ Regex        → email, phone (fallback), LinkedIn/GitHub (fallback)
        ├─ Annotations  → LinkedIn, GitHub, phone from PDF URI metadata
        ├─ spaCy NER    → full name (PERSON entity, first 8 lines)
        ├─ PhraseMatcher / regex → skills (whole-word, case-insensitive)
        ├─ Section parser → certifications, work experience (heading-bounded)
        └─ Keyword scan → education (filtered for bullet/cert bleed-through)
  └─► app.py / api.py  → assemble JSON, add metadata, write to disk
```

### Key design decisions

**Regex before NLP for structured fields.**
Email, phone, and URLs follow deterministic patterns. Regex is faster, more accurate, and has no model dependency for these fields. spaCy is reserved for name extraction where language understanding matters.

**PDF annotation extraction for URLs and phone.**
Modern CV templates (LaTeX, Overleaf) embed contact details as clickable hyperlinks rather than plain text — the text layer may show only an icon character. `parser.py` reads `page.annots` to get the actual URIs (`linkedin.com/in/...`, `tel:+91...`) directly from the PDF metadata, making URL/phone extraction reliable regardless of how the PDF renders text.

**Section-based extraction for Experience and Certifications.**
Keyword scanning the full document picks up false positives — a summary mentioning "Software Engineering" or a project description mentioning "developer" would pollute work experience. Instead, `extract_section()` finds the section heading and reads only the lines until the next heading, then filters out long prose bullets (>160 chars) to keep only job title / company / date lines.

**Skills dictionary (`skills.txt`).**
Matching against a curated list with whole-word boundaries prevents false positives like `sql` matching inside `nosql123`. The boundary pattern `(?<![A-Za-z0-9+#.])skill(?![A-Za-z0-9+#.])` handles skills with special characters (`c++`, `node.js`).

**Certifications as a separate field.**
Certifications appear in their own section in many modern CVs and are semantically distinct from academic education. The system extracts them separately rather than mixing them into the `education` list.

---

## Assumptions

- Resumes are **text-based** PDFs or DOCX files — not scanned images.
- The document is written in **English**.
- The candidate's name appears in the **first 8 non-empty lines**.
- LinkedIn and GitHub URLs, if present, follow standard path structures (`/in/<user>`, `/<user>`).
- Skills are only detected if they appear in `skills.txt`. Add entries freely — one skill per line, `#` for comments.
- Only the **first** email and phone number are extracted.

---

## Limitations

- **Scanned PDFs are not supported.** OCR is intentionally out of scope.
- **Multi-column layouts** can cause text extraction order to be non-linear, which may confuse section detection.
- **Name extraction** is heuristic. Unusual formats (single-word names, names preceded by titles) may not be detected.
- **Work experience bullet details** are intentionally omitted — only job title/company/date lines are kept. Full bullet content would require semantic parsing.
- **Skills outside `skills.txt`** will not be detected. The dictionary ships with common tech skills but is not exhaustive.
- **Phone regex** targets 10–15 digit numbers with common separators. Unusual international formats may be missed; the `tel:` annotation is used as the primary source for PDF files when available.

---

## Future Improvements

- OCR support for scanned PDFs via `pytesseract`.
- Multi-column layout handling via `pdfplumber`'s bounding-box extraction.
- Confidence scores for each extracted field.
- Automatic skill dictionary expansion from a curated dataset.
- Structured education parsing (degree, institution, year as separate fields).
- Docker packaging for one-command deployment.
