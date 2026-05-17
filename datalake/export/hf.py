"""Hugging Face `datasets` features dict for explicit schema loading.

Loadable directly via:
    from datasets import load_dataset
    ds = load_dataset("json", data_files="datalake_export.jsonl")

See docs/04-data-model.md §Hugging Face datasets compatibility.

This module returns a plain dict spec rather than `datasets.Features(...)` instances so
the `datasets` library stays an optional dep. Callers can wrap the spec themselves:

    from datasets import Features, Value, Sequence
    features = Features(features_dict())
"""

from __future__ import annotations


def features_dict() -> dict:
    """Explicit HF Features spec mirroring the JSONL schema in docs/04.

    Returned shape uses the string aliases `Value(...)` etc. would normally take, so a
    caller can map them onto the real classes if and when `datasets` is imported.
    Lists of heterogeneous JSON dicts are typed as `Value("string")` (serialized JSON)
    rather than nested Sequences — the dataset library struggles with truly schema-less
    nested arrays, and judges/users will deserialize on demand.
    """
    catalog_features = {
        "content_type": _value("string"),
        "content_type_confidence": _value("float32"),
        "ownership": _value("string"),
        "ownership_confidence": _value("float32"),
        "ownership_rationale": _value("string"),
        "compliance_flags": _seq(_value("string")),
        "commercial_score": _value("int32"),
        "commercial_action": _value("string"),
    }
    label_features = {
        "structured_abstract": _value("string"),  # JSON-encoded dict
        "methodology": _value("string"),  # JSON-encoded {named, other_freetext}
        "novelty_claim": _value("string"),
        "evidence_quality": _value("string"),  # JSON-encoded dict
        "claim_graph": _value("string"),  # JSON-encoded list[dict]
        "citations": _value("string"),  # JSON-encoded list[dict]
        "domain_tags": _seq(_value("string")),
        "enriched_payload": _value("string"),  # JSON-encoded dict
        "partial": _value("bool"),
    }
    trace_summary_features = {
        "passes_completed": _seq(_value("string")),
        "vote_degraded": _value("bool"),
        "timeout": _value("bool"),
        "n_proposers_succeeded": _value("int32"),
    }
    costs_features = {
        "wafer_usd": _value("float64"),
        "gpt4_equivalent_usd": _value("float64"),
        "human_labeler_equivalent_usd": _value("float64"),
    }
    return {
        "id": _value("string"),
        "source_path": _value("string"),
        "source_hash": _value("string"),
        "run_id": _value("string"),
        "catalog": catalog_features,
        "label": label_features,
        "trace_summary": trace_summary_features,
        "costs": costs_features,
        "model_versions": _value("string"),  # JSON-encoded dict
    }


def _value(dtype: str) -> dict:
    return {"_type": "Value", "dtype": dtype}


def _seq(inner: dict) -> dict:
    return {"_type": "Sequence", "feature": inner}
