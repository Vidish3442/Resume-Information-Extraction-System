import argparse
import json
import sys
from pathlib import Path

from extractor import extract_resume_info
from parser import extract_pdf_annotations, extract_text_from_file
from utils import clean_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract resume information from PDF/DOCX files.")
    parser.add_argument("input_file", help="Path to a PDF or DOCX resume")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output JSON path. Defaults to output/<resume_name>.json",
    )
    return parser.parse_args()


def _resolve_output_path(input_path: Path, output_arg: str | None) -> Path:
    """
    Return the output path for the JSON file.
    - If output_arg is provided, return Path(output_arg).
    - Otherwise return output/<stem>.json.
    """
    if output_arg is not None:
        return Path(output_arg)
    return Path("output") / f"{input_path.stem}.json"


def _add_metadata(result: dict, input_path: Path) -> dict:
    """
    Inject metadata into the result dict.
    Sets result["metadata"]["source_file"] and result["metadata"]["file_type"].
    Returns the mutated dict.
    """
    result["metadata"] = {
        "source_file": str(input_path),
        "file_type": input_path.suffix.lower(),
    }
    return result


def _write_json(data: dict, output_path: Path) -> None:
    """
    Create parent directories if needed, then write data as UTF-8 JSON
    with 2-space indentation to output_path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file)

    # Sub-task 2.1: wrap extraction in error handlers; no raw tracebacks
    try:
        raw_text = extract_text_from_file(input_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    annotations = extract_pdf_annotations(input_path) if input_path.suffix.lower() == ".pdf" else {}
    text = clean_text(raw_text)

    # Sub-task 2.4: pass empty string through rather than short-circuiting;
    # all extractors return None/[] for empty input naturally (Req 12.4).
    result = extract_resume_info(text if text.strip() else "", annotations=annotations)

    # Sub-task 2.2: add metadata via helper
    _add_metadata(result, input_path)

    # Sub-task 2.2 / 2.3: resolve output path and write file
    output_path = _resolve_output_path(input_path, args.output)
    _write_json(result, output_path)

    # Print JSON to stdout and confirm save location
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
