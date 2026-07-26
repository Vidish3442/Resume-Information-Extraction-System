# Feature: resume-information-extraction
from hypothesis import given, settings, strategies as st, assume
import re
import json
import pytest
import extractor
from utils import clean_text
from extractor import (
    extract_email,
    extract_phone,
    extract_skills,
    extract_links,
    extract_keyword_lines,
    EDUCATION_KEYWORDS,
    EXPERIENCE_KEYWORDS,
)
from app import _add_metadata
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Property 1: Text Preprocessor output invariants
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 1
@settings(max_examples=25)
@given(st.text())
def test_property1_clean_text_invariants(text):
    """
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5

    For any string input, clean_text must:
    (a) contain no null bytes
    (b) have no line with two or more consecutive spaces/tabs
    (c) contain no triple newlines
    (d) have no leading/trailing whitespace
    """
    result = clean_text(text)

    # (a) No null bytes
    assert "\x00" not in result

    # (b) No line contains 2+ consecutive spaces or tabs
    for line in result.splitlines():
        assert re.search(r"[ \t]{2,}", line) is None, (
            f"Line has consecutive whitespace: {line!r}"
        )

    # (c) No triple (or more) consecutive newlines
    assert "\n\n\n" not in result

    # (d) No leading/trailing whitespace
    assert result == result.strip()


# ---------------------------------------------------------------------------
# Property 2: Email extractor returns first match for any conforming input
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 2
@settings(max_examples=25)
@given(
    st.from_regex(r"[A-Za-z0-9._%+-]{1,10}", fullmatch=True),
    st.from_regex(r"[A-Za-z0-9-]{1,10}", fullmatch=True),
    st.from_regex(r"[A-Za-z]{2,4}", fullmatch=True),
    st.text(alphabet=st.characters(blacklist_categories=("Cc",), blacklist_characters="@"), max_size=20),
)
def test_property2_email_first_match(local_part, domain, tld, suffix):
    """
    Validates: Requirements 3.1, 3.3

    For any conforming email placed at the start of text, extract_email
    must return that exact email.
    """
    email = f"{local_part}@{domain}.{tld}"

    # Ensure our constructed email is actually valid per the pattern
    assume(re.match(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", email))

    # Build text: email at the start, some suffix that doesn't contain another @ address
    text = email + " " + suffix

    # Skip if the suffix accidentally forms another valid email earlier
    # (we only care that the *first* match is our email)
    first_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    assume(first_match is not None and first_match.group(0) == email)

    assert extract_email(text) == email


# ---------------------------------------------------------------------------
# Property 3: Email extractor rejects near-matches
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 3
@settings(max_examples=25)
@given(
    st.from_regex(r"[A-Za-z0-9]{3,10}", fullmatch=True),
    st.from_regex(r"[A-Za-z0-9]{3,10}", fullmatch=True),
)
def test_property3_email_rejects_near_matches(word1, word2):
    """
    Validates: Requirements 3.2, 3.4

    Strings of the form "word@word2" where neither part has a valid TLD
    (no dot followed by 2+ letters) must return None.
    """
    # word2 must not contain a dot-followed-by-2+-letters pattern (no valid TLD)
    assume(not re.search(r"\.[A-Za-z]{2,}", word2))

    text = f"{word1}@{word2}"

    # Also verify the full text doesn't inadvertently match the email pattern
    assert extract_email(text) is None


# ---------------------------------------------------------------------------
# Property 4: Phone extractor digit-count gate
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 4

@settings(max_examples=25)
@given(st.integers(min_value=1, max_value=9))
def test_property4_too_few_digits(n):
    """
    Validates: Requirements 4.1, 4.2, 4.3, 4.4

    A string of n digits (n < 10) must not be extracted as a phone number.
    """
    text = "1" * n
    assert extract_phone(text) is None


@settings(max_examples=25)
@given(st.integers(min_value=16, max_value=20))
def test_property4_too_many_digits(n):
    """
    Validates: Requirements 4.1, 4.2, 4.3, 4.4

    A string of n digits (n > 15) must not be extracted as a phone number.
    """
    text = "1" * n
    assert extract_phone(text) is None


def test_property4_valid_ten_digits():
    """
    Validates: Requirements 4.1, 4.2, 4.3, 4.4

    A standard 10-digit phone format must be extracted successfully.
    """
    result = extract_phone("555-867-5309")
    assert result is not None


# ---------------------------------------------------------------------------
# Property 5: Skills output is deduplicated, sorted, and title-cased
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 5

FIXED_SKILLS_P5 = {"python", "sql", "react", "docker"}


@settings(max_examples=25)
@given(
    st.lists(
        st.sampled_from(sorted(FIXED_SKILLS_P5)),
        min_size=1,
        max_size=4,
        unique=True,
    )
)
def test_property5_skills_dedup_sorted_titlecased(skill_subset):
    """
    Validates: Requirements 6.2, 6.3

    For any subset of known skills present in text, extract_skills must
    return a sorted, deduplicated, title-cased list.
    """
    text = " ".join(skill_subset)

    with patch("extractor.load_skills", return_value=FIXED_SKILLS_P5):
        result = extract_skills(text)

    # Sorted in ascending lexicographic order
    assert result == sorted(result), f"Not sorted: {result}"

    # No duplicates (case-insensitive)
    lower_results = [s.lower() for s in result]
    assert len(result) == len(set(lower_results)), f"Duplicates found: {result}"

    # All entries are title-cased
    assert all(s == s.title() for s in result), f"Not all title-cased: {result}"


# ---------------------------------------------------------------------------
# Property 6: Skills whole-word boundary enforcement
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 6

FIXED_SKILLS_P6 = {"python", "sql", "react"}


@settings(max_examples=25)
@given(
    st.sampled_from(sorted(FIXED_SKILLS_P6)),
    st.from_regex(r"[a-z]{2,5}", fullmatch=True),
    st.from_regex(r"[a-z]{2,5}", fullmatch=True),
)
def test_property6_skills_whole_word_boundary(skill, prefix, suffix):
    """
    Validates: Requirements 6.1, 6.5

    A skill embedded inside a longer alphanumeric token (no spaces around
    it) must NOT be extracted from the text.
    """
    # Build text where skill is sandwiched: no word boundaries on either side
    text = f"{prefix}{skill}{suffix}"

    with patch("extractor.load_skills", return_value={skill}):
        result = extract_skills(text)

    assert skill.title() not in result, (
        f"Skill '{skill}' was extracted from '{text}' but should not have been "
        f"(embedded inside alphanumeric token)"
    )


# ---------------------------------------------------------------------------
# Property 7: URL extractors match all valid format variants
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 7

PREFIXES = ["", "www.", "http://", "https://", "http://www.", "https://www."]


@settings(max_examples=25)
@given(
    st.from_regex(r"[A-Za-z0-9][A-Za-z0-9_-]{0,28}[A-Za-z0-9]", fullmatch=True),
    st.sampled_from(PREFIXES),
)
def test_property7_url_format_variants(username, prefix):
    """
    Validates: Requirements 7.1, 7.2, 7.5, 7.6

    extract_links must recognise LinkedIn and GitHub URLs across all
    common prefix variants.
    """
    linkedin_url = f"{prefix}linkedin.com/in/{username}"
    github_url = f"{prefix}github.com/{username}"
    text = f"{linkedin_url} {github_url}"

    li, gh = extract_links(text)

    assert li is not None and "linkedin.com/in/" in li, (
        f"LinkedIn URL not extracted from '{linkedin_url}'"
    )
    assert gh is not None and "github.com/" in gh, (
        f"GitHub URL not extracted from '{github_url}'"
    )


# ---------------------------------------------------------------------------
# Property 8: Section extractor output is unique and bounded
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 8

@settings(max_examples=25)
@given(
    st.lists(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(blacklist_categories=("Cc",)),
        ),
        min_size=0,
        max_size=20,
    )
)
def test_property8_section_extractor_unique_and_bounded(lines):
    """
    Validates: Requirements 8.1, 8.2, 8.4

    For any input text, extract_keyword_lines must return:
    - At most 5 entries
    - All entries unique after strip
    - All entries contain at least one education keyword
    """
    # Inject 3 lines that definitely contain an education keyword
    keyword_lines = [
        "B.Tech Computer Science at ABC university 2020",
        "Master of Science, XYZ university 2022",
        "Graduated from state university with honours",
    ]
    all_lines = lines + keyword_lines
    text = "\n".join(all_lines)

    result = extract_keyword_lines(text, EDUCATION_KEYWORDS)

    # Bounded to at most 5
    assert len(result) <= 5, f"Result has {len(result)} entries, expected <= 5"

    # All entries are unique after stripping
    stripped = [r.strip() for r in result]
    assert len(result) == len(set(stripped)), f"Duplicate entries found: {result}"

    # Every returned line contains at least one education keyword
    for entry in result:
        lower_entry = entry.lower()
        assert any(kw in lower_entry for kw in EDUCATION_KEYWORDS), (
            f"Entry does not contain any education keyword: {entry!r}"
        )


# ---------------------------------------------------------------------------
# Property 9: JSON output always contains all required fields
# ---------------------------------------------------------------------------
# Feature: resume-information-extraction, Property 9

REQUIRED_KEYS = {
    "full_name", "email", "phone", "skills", "education",
    "linkedin", "github", "work_experience", "metadata",
}

_opt_str = st.one_of(st.none(), st.text(max_size=30))
_str_list = st.lists(st.text(max_size=20), max_size=5)


@settings(max_examples=25)
@given(
    st.fixed_dictionaries(
        {
            "full_name":       _opt_str,
            "email":           _opt_str,
            "phone":           _opt_str,
            "skills":          _str_list,
            "education":       _str_list,
            "linkedin":        _opt_str,
            "github":          _opt_str,
            "work_experience": _str_list,
        }
    )
)
def test_property9_json_required_fields(result_dict):
    """
    Validates: Requirements 10.1, 10.6

    After adding metadata and serialising, the JSON object must:
    - Contain exactly the 9 required top-level keys
    - Represent None values as JSON null
    - Represent empty lists as JSON []
    """
    # Add metadata (mutates result_dict in place, returns same dict)
    _add_metadata(result_dict, Path("test.pdf"))

    serialised = json.dumps(result_dict)
    parsed = json.loads(serialised)

    # Exactly the required keys are present
    assert set(parsed.keys()) == REQUIRED_KEYS, (
        f"Key mismatch. Got: {set(parsed.keys())}, expected: {REQUIRED_KEYS}"
    )

    # None values survive the round-trip as JSON null (Python None after parse)
    for key in ("full_name", "email", "phone", "linkedin", "github"):
        if result_dict[key] is None:
            assert parsed[key] is None, (
                f"Expected null for key '{key}', got {parsed[key]!r}"
            )

    # Empty lists survive the round-trip as []
    for key in ("skills", "education", "work_experience"):
        if result_dict[key] == []:
            assert parsed[key] == [], (
                f"Expected [] for key '{key}', got {parsed[key]!r}"
            )
