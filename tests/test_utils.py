"""Unit tests for utils.py — clean_text, load_skills, unique_preserve_order."""
import pytest
from utils import clean_text, load_skills, unique_preserve_order


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

class TestCleanText:

    def test_removes_null_bytes(self):
        """6.1 — Validates: Requirements 2.1"""
        result = clean_text("hello\x00world")
        assert "\x00" not in result

    def test_collapses_spaces_and_tabs_per_line(self):
        """6.2 — Validates: Requirements 2.2"""
        text = "foo   bar\nbaz\t\tqux"
        result = clean_text(text)
        lines = result.split("\n")

        # Neither line should contain 2+ consecutive spaces or tabs
        for line in lines:
            assert "  " not in line, f"Double space found in: {repr(line)}"
            assert "\t\t" not in line, f"Double tab found in: {repr(line)}"

        # The two lines must still be independent — one's collapse must not
        # bleed into the other
        assert len(lines) == 2, "Line count should be preserved"

    def test_reduces_triple_newlines_to_double(self):
        """6.3 — Validates: Requirements 2.3"""
        result = clean_text("a\n\n\n\nb")
        assert "\n\n" in result
        assert "\n\n\n" not in result

    def test_strips_leading_and_trailing_whitespace(self):
        """6.4 — Validates: Requirements 2.4"""
        result = clean_text("  hello world  ")
        assert result == "hello world"

    def test_preserves_single_blank_line_between_sections(self):
        """6.5 — Validates: Requirements 2.5"""
        result = clean_text("Section A\n\nSection B")
        assert "\n\n" in result


# ---------------------------------------------------------------------------
# load_skills
# ---------------------------------------------------------------------------

class TestLoadSkills:

    def test_returns_empty_set_when_file_missing(self):
        """6.6 — Validates: Requirements 6.4"""
        result = load_skills("/nonexistent/path/skills.txt")
        assert result == set()

    def test_skips_comments_and_blank_lines(self, tmp_path):
        """6.7 — Validates: Requirements 6.1"""
        skills_file = tmp_path / "skills.txt"
        skills_file.write_text("# comment\npython\n\njavascript\n", encoding="utf-8")

        result = load_skills(str(skills_file))
        assert result == {"python", "javascript"}


# ---------------------------------------------------------------------------
# unique_preserve_order
# ---------------------------------------------------------------------------

class TestUniquePreserveOrder:

    def test_removes_case_insensitive_duplicates_preserving_first_seen(self):
        """6.8 — Deduplication preserves original casing of first occurrence."""
        result = unique_preserve_order(["Python", "python", "SQL", "sql", "React"])
        assert result == ["Python", "SQL", "React"]
