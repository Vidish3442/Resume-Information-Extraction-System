"""
Unit tests for extractor.py
"""
import pytest
import extractor
from extractor import (
    extract_email,
    extract_phone,
    extract_skills,
    extract_links,
    extract_keyword_lines,
    EDUCATION_KEYWORDS,
)


# ---------------------------------------------------------------------------
# 7.1 – extract_email: returns the FIRST email when multiple are present
# Requirements: 3.1
# ---------------------------------------------------------------------------
def test_extract_email_returns_first_of_multiple():
    text = "Contact: first@example.com or second@test.org"
    result = extract_email(text)
    assert result == "first@example.com"


# ---------------------------------------------------------------------------
# 7.2 – extract_email: returns None when no email is present
# Requirements: 3.2
# ---------------------------------------------------------------------------
def test_extract_email_returns_none_when_no_email():
    result = extract_email("No email here")
    assert result is None


# ---------------------------------------------------------------------------
# 7.3 – extract_email: returns None for malformed @ tokens
# Requirements: 3.4
# ---------------------------------------------------------------------------
def test_extract_email_returns_none_for_malformed_at_tokens():
    assert extract_email("user@@example") is None
    assert extract_email("noreply@") is None


# ---------------------------------------------------------------------------
# 7.4 – extract_phone: returns None for a 9-digit string (too short)
# Requirements: 4.4
# ---------------------------------------------------------------------------
def test_extract_phone_returns_none_for_nine_digits():
    result = extract_phone("123456789")
    assert result is None


# ---------------------------------------------------------------------------
# 7.5 – extract_phone: returns None for a 16-digit string (too long)
# Requirements: 4.4
# ---------------------------------------------------------------------------
def test_extract_phone_returns_none_for_sixteen_digits():
    result = extract_phone("1234567890123456")
    assert result is None


# ---------------------------------------------------------------------------
# 7.6 – extract_phone: returns matched string for a standard 10-digit US number
# Requirements: 4.1, 4.3
# ---------------------------------------------------------------------------
def test_extract_phone_returns_match_for_standard_us_number():
    result = extract_phone("Call me at 555-867-5309")
    assert result is not None


# ---------------------------------------------------------------------------
# 7.7 – extract_skills: returns [] when load_skills is patched to return set()
# Requirements: 6.4
# ---------------------------------------------------------------------------
def test_extract_skills_empty_when_skills_dict_empty(monkeypatch):
    monkeypatch.setattr(extractor, "load_skills", lambda: set())
    result = extract_skills("Python SQL FastAPI")
    assert result == []


# ---------------------------------------------------------------------------
# 7.8 – extract_skills: does NOT match a skill embedded inside a longer token
# Requirements: 6.5
# ---------------------------------------------------------------------------
def test_extract_skills_no_substring_match(monkeypatch):
    monkeypatch.setattr(extractor, "load_skills", lambda: {"sql"})
    # "nosql123" contains "sql" as a substring but it is not a standalone token
    result = extract_skills("nosql123 is a database")
    assert result == []


# ---------------------------------------------------------------------------
# 7.9 – extract_links: returns LinkedIn URL for all four prefix variants
# Requirements: 7.1, 7.5
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "linkedin.com/in/johnsmith",
    "www.linkedin.com/in/johnsmith",
    "http://linkedin.com/in/johnsmith",
    "https://www.linkedin.com/in/johnsmith",
])
def test_extract_links_linkedin_variants(text):
    linkedin, _ = extract_links(text)
    assert linkedin is not None
    assert "linkedin.com/in/johnsmith" in linkedin


# ---------------------------------------------------------------------------
# 7.10 – extract_links: returns (None, None) when no URLs are present
# Requirements: 7.3, 7.4
# ---------------------------------------------------------------------------
def test_extract_links_returns_none_tuple_when_no_urls():
    linkedin, github = extract_links("No links here")
    assert linkedin is None
    assert github is None


# ---------------------------------------------------------------------------
# 7.11 – extract_keyword_lines: at most 5 lines, no duplicates
# Requirements: 8.2, 8.4, 9.2, 9.4
# ---------------------------------------------------------------------------
def test_extract_keyword_lines_limit_and_deduplication():
    # 7 lines containing "university", 2 of which are exact duplicates
    lines = [
        "ABC University 2020",
        "DEF University 2021",
        "GHI University 2022",
        "JKL University 2023",
        "MNO University 2024",
        "ABC University 2020",   # duplicate of line 0
        "PQR University 2025",   # 7th unique-ish line (but limit should cap at 5)
    ]
    text = "\n".join(lines)
    result = extract_keyword_lines(text, EDUCATION_KEYWORDS)

    # Must not exceed the default limit of 5
    assert len(result) <= 5

    # Must not contain duplicate lines (case-insensitive check mirrors implementation)
    lowered = [r.lower() for r in result]
    assert len(lowered) == len(set(lowered))
