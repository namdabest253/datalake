"""Hugging Face `datasets` features dict for explicit schema loading.

Loadable directly via:
    from datasets import load_dataset
    ds = load_dataset("json", data_files="datalake_export.jsonl")

See docs/04-data-model.md §Hugging Face datasets compatibility.
"""

from __future__ import annotations


def features_dict() -> dict:
    """Return the explicit HF `Features` mapping.

    Build with `datasets.Features({...})` at the call site. Keeping it as a dict here
    avoids a hard import of the `datasets` package, which is not in core deps.
    """
    raise NotImplementedError(
        "TODO: mirror the JSONL schema shape from docs/04 as a Features({...}) mapping."
    )
