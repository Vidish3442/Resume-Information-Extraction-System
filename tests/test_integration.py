"""
Integration tests for the Resume Information Extraction System end-to-end pipeline.

Validates Requirements: 10.1, 10.4, 11.1, 11.2, 11.3, 11.4, 12.1, 12.2
"""

import json
import subprocess
from pathlib import Path

PYTHON = r"C:\Users\vidis\anaconda3\python.exe"
CWD = r"d:\Programs\resumeaiparser"
SAMPLE_RESUME = Path(CWD) / "sample_resumes" / "sample_resume.docx"
SAMPLE_PDF_RESUME = Path(CWD) / "sample_resumes" / "Vidish_CV.pdf"
REQUIRED_KEYS = {
    "full_name",
    "email",
    "phone",
    "skills",
    "education",
    "linkedin",
    "github",
    "work_experience",
    "metadata",
}


def test_end_to_end_pipeline_with_sample_resume(tmp_path):
    """
    10.1 — End-to-end pipeline with a real sample resume.

    Validates: Requirements 11.1, 11.2, 11.3, 10.1
    """
    result = subprocess.run(
        [PYTHON, "app.py", str(SAMPLE_RESUME)],
        cwd=CWD,
        capture_output=True,
        text=True,
    )

    # Pipeline should exit cleanly
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )

    # Default output file should have been written
    expected_output = Path(CWD) / "output" / f"{SAMPLE_RESUME.stem}.json"
    assert expected_output.exists(), (
        f"Expected output file {expected_output} was not created."
    )

    # JSON must contain all 9 required top-level keys
    data = json.loads(expected_output.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - set(data.keys())
    assert not missing, f"Output JSON is missing keys: {missing}"


def test_custom_output_flag(tmp_path):
    """
    10.2 — Pipeline honours the --output flag.

    Validates: Requirements 11.4, 10.4
    """
    custom_output = tmp_path / "custom_output" / "result.json"

    result = subprocess.run(
        [PYTHON, "app.py", str(SAMPLE_RESUME), "-o", str(custom_output)],
        cwd=CWD,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )

    assert custom_output.exists(), (
        f"Expected custom output file {custom_output} was not created."
    )

    data = json.loads(custom_output.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - set(data.keys())
    assert not missing, f"Output JSON is missing keys: {missing}"


def test_cli_uses_pdf_annotations_for_contact_links(tmp_path):
    """
    PDF contact links can live in hyperlink annotations instead of visible text.
    The CLI should extract them the same way the API/Streamlit path does.
    """
    custom_output = tmp_path / "vidish.json"

    result = subprocess.run(
        [PYTHON, "app.py", str(SAMPLE_PDF_RESUME), "-o", str(custom_output)],
        cwd=CWD,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )

    data = json.loads(custom_output.read_text(encoding="utf-8"))
    assert data["phone"] == "+919654403155"
    assert data["linkedin"] == "https://www.linkedin.com/in/vidishkumar/"
    assert data["github"] == "https://github.com/Vidish3442"


def test_error_exit_for_missing_file():
    """
    10.3 — Pipeline exits with code 1 and prints an error for a non-existent file.

    Validates: Requirement 12.1
    """
    result = subprocess.run(
        [PYTHON, "app.py", "nonexistent_file.pdf"],
        cwd=CWD,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, (
        f"Expected exit code 1, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    assert "Error:" in result.stderr, (
        f"Expected 'Error:' in stderr, got: {result.stderr!r}"
    )


def test_error_exit_for_unsupported_extension(tmp_path):
    """
    10.4 — Pipeline exits with code 1 for an unsupported file extension.

    Validates: Requirement 12.2
    """
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text("This is a plain text resume.", encoding="utf-8")

    result = subprocess.run(
        [PYTHON, "app.py", str(txt_file)],
        cwd=CWD,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, (
        f"Expected exit code 1, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
