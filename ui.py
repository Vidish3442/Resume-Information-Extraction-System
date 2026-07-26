"""
Streamlit UI for the Resume Information Extraction System.

Runs the extraction pipeline directly — no FastAPI server required.

Run with:
  C:\\Users\\vidis\\anaconda3\\python.exe -m streamlit run ui.py
"""

import json
import tempfile
from pathlib import Path

import streamlit as st

from extractor import extract_resume_info
from parser import extract_text_from_file, extract_pdf_annotations
from utils import clean_text

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide",
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📄 Resume Information Extractor")
st.caption("Upload a PDF or DOCX resume and instantly extract structured information.")

st.divider()

# ── File upload ────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload your resume",
    type=["pdf", "docx"],
    help="Supports PDF and DOCX formats. Scanned (image-only) PDFs are not supported.",
)

if uploaded_file is None:
    st.info("Upload a resume above to get started.")
    st.stop()

# ── Run extraction pipeline directly ──────────────────────────────────────────
with st.spinner("Extracting information…"):
    suffix = Path(uploaded_file.name).suffix.lower()

    # Write upload to a temp file so pdfplumber / python-docx can open it by path
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        raw_text = extract_text_from_file(tmp_path)
        annotations = extract_pdf_annotations(tmp_path) if suffix == ".pdf" else {}
    except (FileNotFoundError, ValueError) as exc:
        tmp_path.unlink(missing_ok=True)
        st.error(f"Could not read file: {exc}")
        st.stop()
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        st.error(f"Unexpected error reading file: {exc}")
        st.stop()

    tmp_path.unlink(missing_ok=True)

    text = clean_text(raw_text)
    data = extract_resume_info(text if text.strip() else "", annotations=annotations)
    data["metadata"] = {
        "source_file": uploaded_file.name,
        "file_type": suffix,
    }

# ── Results layout ─────────────────────────────────────────────────────────────
st.success(f"✅ Successfully parsed **{uploaded_file.name}**")
st.divider()

# Row 1 — Contact info
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("👤 Name")
    st.write(data.get("full_name") or "_Not found_")

with col2:
    st.subheader("📧 Email")
    email = data.get("email")
    st.write(f"[{email}](mailto:{email})" if email else "_Not found_")

with col3:
    st.subheader("📞 Phone")
    st.write(data.get("phone") or "_Not found_")

st.divider()

# Row 2 — Links
col4, col5 = st.columns(2)

with col4:
    st.subheader("🔗 LinkedIn")
    linkedin = data.get("linkedin")
    if linkedin:
        url = linkedin if linkedin.startswith("http") else f"https://{linkedin}"
        st.markdown(f"[{linkedin}]({url})")
    else:
        st.write("_Not found_")

with col5:
    st.subheader("🐙 GitHub")
    github = data.get("github")
    if github:
        url = github if github.startswith("http") else f"https://{github}"
        st.markdown(f"[{github}]({url})")
    else:
        st.write("_Not found_")

st.divider()

# Row 3 — Skills
st.subheader("🛠️ Skills")
skills = data.get("skills", [])
if skills:
    cols = st.columns(min(len(skills), 6))
    for i, skill in enumerate(skills):
        cols[i % len(cols)].markdown(
            f'<span style="background:#1f77b4;color:white;padding:4px 10px;'
            f'border-radius:12px;font-size:0.85rem;">{skill}</span>',
            unsafe_allow_html=True,
        )
else:
    st.write("_No skills found_")

st.divider()

# Row 4 — Education & Experience side by side
col6, col7 = st.columns(2)

with col6:
    st.subheader("🎓 Education")
    education = data.get("education", [])
    if education:
        for entry in education:
            st.markdown(f"- {entry}")
    else:
        st.write("_Not found_")

with col7:
    st.subheader("💼 Work Experience")
    experience = data.get("work_experience", [])
    if experience:
        for entry in experience:
            st.markdown(f"- {entry}")
    else:
        st.write("_Not found_")

st.divider()

# Certifications (only shown if present)
certifications = data.get("certifications", [])
if certifications:
    st.subheader("📜 Certifications")
    for cert in certifications:
        st.markdown(f"- {cert}")
    st.divider()

# Raw JSON expander
with st.expander("🔍 View raw JSON output"):
    st.json(data)

# Download button
st.download_button(
    label="⬇️ Download JSON",
    data=json.dumps(data, indent=2, ensure_ascii=False),
    file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_parsed.json",
    mime="application/json",
)
