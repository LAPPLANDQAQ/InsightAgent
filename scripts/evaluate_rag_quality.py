"""Evaluate RAG quality from a JSON case file."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.evaluation.ragas_style import build_report


def main() -> int:
    """Read cases from JSON and write a JSON report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = build_report(cases)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
