"""
Streamlit UI for the Resume Information Extraction System.

Talks to the FastAPI backend at http://localhost:8000/parse.

Run with:
  C:\\Users\\vidis\\anaconda3\\python.exe -m streamlit run ui.py
"""

import json

import requests
import streamlit as st

API_URL = "http://localhost:8000/parse"

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📄 Resume Information Extractor")
st.caption("Upload a PDF or DOCX resume and instantly extract structured information.")

st.divider()

# ── File upload ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload your resume",
    type=["pdf", "docx"],
    help="Supports PDF and DOCX formats. Scanned (image-only) PDFs are not supported.",
)

if uploaded_file is None:
    st.info("Upload a resume above to get started.")
    st.stop()

# ── Send to API ───────────────────────────────────────────────────────────────
with st.spinner("Extracting information…"):
    try:
        response = requests.post(
            API_URL,
            files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the API server. "
            "Make sure it is running:\n\n"
            "```\nC:\\Users\\vidis\\anaconda3\\python.exe -m uvicorn api:app --reload --port 8000\n```"
        )
        st.stop()

if response.status_code != 200:
    detail = response.json().get("detail", response.text)
    st.error(f"API error ({response.status_code}): {detail}")
    st.stop()

data = response.json()

# ── Results layout ────────────────────────────────────────────────────────────
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
    # Render as pill-style badges using columns
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
