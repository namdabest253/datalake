"""Download the arXiv + NSF demo corpus to demo_corpus/.

See docs/08-ops-and-demo.md §Data license notes and PRD §11.

Usage:
    python scripts/seed_corpus.py --arxiv-n 15000 --nsf-n 5000
"""

from __future__ import annotations

import argparse
from pathlib import Path

ARXIV_DIR = Path("demo_corpus/arxiv")
NSF_DIR = Path("demo_corpus/nsf")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arxiv-n", type=int, default=15_000)
    parser.add_argument("--nsf-n", type=int, default=5_000)
    args = parser.parse_args()
    ARXIV_DIR.mkdir(parents=True, exist_ok=True)
    NSF_DIR.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError(
        f"TODO: fetch {args.arxiv_n} arXiv PDFs (varied disciplines: CS, biology, physics, "
        f"economics) into {ARXIV_DIR}, and {args.nsf_n} NSF grant abstracts into {NSF_DIR}. "
        "Respect arXiv terms of use."
    )


if __name__ == "__main__":
    main()
