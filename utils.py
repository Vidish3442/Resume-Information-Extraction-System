import re
from pathlib import Path


def clean_text(text: str) -> str:
    # Replace null bytes with a single space
    text = text.replace("\x00", " ")
    # Collapse 2+ consecutive spaces/tabs per line (preserves newlines)
    lines = text.split("\n")
    lines = [re.sub(r"[ \t]{2,}", " ", line) for line in lines]
    text = "\n".join(lines)
    # Reduce 3+ consecutive newlines to exactly two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_skills(file_path: str = "skills.txt") -> set[str]:
    path = Path(file_path)
    if not path.exists():
        return set()

    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def unique_preserve_order(values):
    seen = set()
    output = []
    for value in values:
        key = value.lower() if isinstance(value, str) else value
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output
