import re

import spacy

from utils import load_skills, unique_preserve_order


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4})"
)
LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com\s*/\s*in\s*/\s*[A-Za-z0-9_%-]+/?",
    re.I,
)
GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com\s*/\s*[A-Za-z0-9_%-]+(?:\s*/\s*[A-Za-z0-9_%-]+)*/?",
    re.I,
)

EDUCATION_KEYWORDS = (
    "b.tech",
    "bachelor",
    "master",
    "m.tech",
    "mba",
    "b.sc",
    "m.sc",
    "phd",
    "university",
    "college",
)
EXPERIENCE_KEYWORDS = (
    "experience",
    "software engineer",
    "developer",
    "intern",
    "company",
    "worked",
)
CERTIFICATION_KEYWORDS = (
    "certification",
    "certificate",
    "certified",
    "course",
    "coursera",
    "udemy",
    "nptel",
    "edx",
    "internshala",
    "training",
)

# Date pattern used to distinguish job entries from prose
_DATE_PATTERN = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|present|\d{4})\b", re.I
)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = spacy.blank("en")


# ── Regex_Extractor ───────────────────────────────────────────────────────────

def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    match = PHONE_PATTERN.search(text)
    if not match:
        return None
    phone = match.group(0).strip()
    start, end = match.start(), match.end()
    if (start > 0 and text[start - 1].isdigit()) or (end < len(text) and text[end].isdigit()):
        return None
    digits = re.sub(r"\D", "", phone)
    return phone if 10 <= len(digits) <= 15 else None


def extract_links(text: str) -> tuple[str | None, str | None]:
    linkedin = LINKEDIN_PATTERN.search(text)
    github = GITHUB_PATTERN.search(text)

    def _normalise(url: str) -> str:
        return re.sub(r"\s*/\s*", "/", url).strip()

    return (
        _normalise(linkedin.group(0)) if linkedin else None,
        _normalise(github.group(0)) if github else None,
    )


# ── NLP_Extractor ─────────────────────────────────────────────────────────────

def extract_name(text: str) -> str | None:
    first_lines = [line.strip() for line in text.splitlines()[:8] if line.strip()]
    doc = nlp("\n".join(first_lines))

    for entity in doc.ents:
        if entity.label_ == "PERSON" and 2 <= len(entity.text.split()) <= 4:
            return entity.text.strip()

    for line in first_lines:
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(word[:1].isupper() for word in words):
            return line

    return None


def extract_skills(text: str) -> list[str]:
    skills = load_skills()
    lower_text = text.lower()
    found = []
    for skill in skills:
        pattern = rf"(?<![A-Za-z0-9+#.]){re.escape(skill)}(?![A-Za-z0-9+#.])"
        if re.search(pattern, lower_text):
            found.append(skill.title())
    return sorted(unique_preserve_order(found))


# ── Section_Extractor ─────────────────────────────────────────────────────────

def extract_keyword_lines(text: str, keywords: tuple[str, ...], limit: int = 5) -> list[str]:
    """Scan every line; return up to `limit` unique lines containing any keyword."""
    matches = []
    for line in text.splitlines():
        clean_line = line.strip()
        lower_line = clean_line.lower()
        if clean_line and any(keyword in lower_line for keyword in keywords):
            matches.append(clean_line)
    return unique_preserve_order(matches)[:limit]


def extract_section(text: str, section_heading: str) -> list[str]:
    """
    Return all non-empty lines between `section_heading` and the next
    major section heading. Major headings are detected as short (≤3 word)
    title-cased lines with no punctuation characters.
    """
    lines = text.splitlines()
    inside = False
    results = []
    heading_lower = section_heading.lower()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()

        if lower == heading_lower or lower.startswith(heading_lower + " "):
            inside = True
            continue

        if inside:
            words = stripped.split()
            is_heading = (
                len(words) <= 3
                and all(w[0].isupper() for w in words if w)
                and not any(ch in stripped for ch in ("–", "•", "@", ":", ",", "(", ")"))
            )
            if is_heading:
                break
            results.append(stripped)

    return unique_preserve_order(results)[:10]


def extract_certifications(text: str) -> list[str]:
    """
    Extract lines from the Certifications section.
    Falls back to keyword scanning if no explicit section heading is found.
    """
    section_lines = extract_section(text, "Certifications")
    if section_lines:
        return [re.sub(r"^[•\-–]\s*", "", line) for line in section_lines]
    return extract_keyword_lines(text, CERTIFICATION_KEYWORDS, limit=10)


def extract_work_experience(text: str) -> list[str]:
    """
    Extract work experience entries from the Experience section.

    Uses section-based extraction so that summary paragraphs and skill
    mentions in other sections don't pollute the results.

    Only lines that are short enough to be an entry title (≤160 chars)
    are kept; long prose bullet descriptions are dropped because they
    add noise without adding useful structured data.

    Falls back to keyword scanning with prose-filtering when no section
    heading is found.
    """
    for heading in ("Experience", "Work Experience", "Employment", "Professional Experience"):
        lines = extract_section(text, heading)
        if not lines:
            continue

        results = []
        for line in lines:
            stripped = re.sub(r"^[•\-–]\s*", "", line).strip()
            if not stripped:
                continue
            # Keep only job title / company / date lines — skip long prose bullets
            if len(stripped) > 160:
                continue
            results.append(stripped)

        if results:
            return results[:5]

    # Fallback: keyword scan, excluding bare headings and long prose lines
    candidates = []
    for line in extract_keyword_lines(text, EXPERIENCE_KEYWORDS, limit=10):
        if line.lower().strip() in ("experience", "work experience", "employment"):
            continue
        if len(line) > 120 and not _DATE_PATTERN.search(line):
            continue
        candidates.append(line)
    return candidates[:5]


# ── Orchestrator ──────────────────────────────────────────────────────────────

def extract_resume_info(text: str, annotations: dict | None = None) -> dict:
    """
    annotations: optional dict from parser.extract_pdf_annotations() with keys
    linkedin, github, phone — sourced from PDF hyperlink metadata which is more
    reliable than regex on rendered text for modern LaTeX-style CVs.
    """
    annotations = annotations or {}

    linkedin_annot = annotations.get("linkedin")
    github_annot   = annotations.get("github")
    phone_annot    = annotations.get("phone")

    linkedin_regex, github_regex = extract_links(text)

    linkedin = linkedin_annot or linkedin_regex
    github   = github_annot   or github_regex
    phone    = phone_annot    or extract_phone(text)

    education_raw = extract_keyword_lines(text, EDUCATION_KEYWORDS, limit=10)
    education = [
        line for line in education_raw
        # Drop bullet lines — cert entries bleed in via "University" keyword
        if not re.match(r"^[•\-–]", line)
        # Drop lines that are purely certification-related
        and not any(kw in line.lower() for kw in CERTIFICATION_KEYWORDS)
    ]

    return {
        "full_name":       extract_name(text),
        "email":           extract_email(text),
        "phone":           phone,
        "skills":          extract_skills(text),
        "education":       education,
        "certifications":  extract_certifications(text),
        "linkedin":        linkedin,
        "github":          github,
        "work_experience": extract_work_experience(text),
    }
