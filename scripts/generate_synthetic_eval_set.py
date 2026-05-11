"""Generate deterministic synthetic RAG evaluation cases."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.evaluation.synthetic_dataset import generate_synthetic_cases


def main() -> int:
    """Read chunks from JSON and write JSONL synthetic cases."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    chunks = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cases = generate_synthetic_cases(chunks)
    lines = [json.dumps(case, ensure_ascii=False) for case in cases]
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
