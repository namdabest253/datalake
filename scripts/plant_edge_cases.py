"""Plant ~30 hand-crafted compliance edge cases into the demo corpus.

These drive the "compliance catching" moments judges remember. Files saved with
SYNTHETIC_ prefix so they're disclosable in the demo narrative.

See docs/08-ops-and-demo.md §Data license notes and PRD §11.

Categories (PRD §11):
  - Papers with mixed publisher exclusivity language
  - Grant-funded papers where ownership is contested
  - Papers describing human subjects research (IRB-restricted)
  - Pre-cleared, university-press-released datasets (license-ready, high value)
"""

from __future__ import annotations

from pathlib import Path

SYNTHETIC_DIR = Path("demo_corpus/synthetic")


def main() -> None:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError(
        "TODO: hand-author or template ~30 markdown/PDF docs that exercise each "
        "compliance heuristic in datalake/prompts/heuristics.yaml. "
        "Filenames: SYNTHETIC_<category>_<n>.{md,pdf}."
    )


if __name__ == "__main__":
    main()
