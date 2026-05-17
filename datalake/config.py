"""Settings loaded from .env then config.yaml then CLI flags.

Precedence (lowest → highest): code defaults < config.yaml < environment variables
(via .env or shell) < CLI flags.

See docs/05-inference-client.md §Client config.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Paths(BaseModel):
    sqlite_db: Path = Path("./.datalake/datalake.db")
    logs_dir: Path = Path("./.datalake/logs")
    heuristics: Path = Path("./datalake/prompts/heuristics.yaml")
    judge_rubric: Path = Path("./datalake/eval/judge_rubric.yaml")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    # Secrets
    wafer_api_key: str = ""
    judge_api_key: str = ""

    # Models. Env-var names mirror Wafer's onboarding convention (FAST = loop, BIG = judge).
    wafer_base_url: str = "https://api.wafer.ai/v1"
    wafer_loop_model: str = Field(default="qwen-3.5-397b", validation_alias="WAFER_MODEL_FAST")
    judge_model: str = Field(default="qwen-3.5-strong", validation_alias="WAFER_MODEL_BIG")
    openai_baseline_model: str = "gpt-4-turbo"
    # Single-pass baseline runs on the same Wafer family — the experimental variable
    # is "loop vs no-loop", not "Wafer vs GPT-4". Cost numbers for the GPT-4 column in
    # the eval report come from estimate_gpt4_cost on the observed token counts.
    baseline_model: str = Field(default="qwen-3.5-397b", validation_alias="WAFER_MODEL_FAST")

    # Concurrency
    # Wafer key is on a 1-at-a-time tier — parallel calls return HTTP 429
    # ("concurrency_limit_exceeded"). The client-side semaphore serialises calls
    # so the loop never self-DDoSes its own quota. Bump only if you've been
    # moved to a higher tier.
    wafer_concurrency: int = 1
    openai_concurrency: int = 8
    judge_concurrency: int = 4
    per_doc_concurrency: int = 8

    # Loop shape
    n_proposers: int = 3
    per_doc_budget_seconds: float = 30.0
    trace_sample_k: int = 10

    # Cost ceiling — hard kill switch (docs/05-inference-client.md §Hard kill switch)
    wafer_spend_ceiling_usd: float = 30.0

    paths: Paths = Paths()


def _aliases_for_field(field_name: str, model: type[BaseSettings]) -> set[str]:
    """Env-var names that pydantic-settings will accept for this field."""
    info = model.model_fields.get(field_name)
    names = {field_name.upper()}
    if info and info.validation_alias is not None:
        alias = info.validation_alias
        names.add(str(alias).upper())
    return names


def load_settings(config_yaml: Path | str = "config.yaml") -> Settings:
    """Compose YAML defaults with env vars. Env wins over YAML; YAML wins over code defaults.

    The pydantic-settings kwargs override env, so we filter YAML to drop keys that the
    user has explicitly set via environment.
    """
    yaml_path = Path(config_yaml)
    yaml_data: dict = {}
    if yaml_path.exists():
        yaml_data = yaml.safe_load(yaml_path.read_text()) or {}

    yaml_filtered: dict = {}
    for k, v in yaml_data.items():
        env_names = _aliases_for_field(k, Settings)
        if any(name in os.environ for name in env_names):
            continue  # env is set — let pydantic-settings pick it up
        yaml_filtered[k] = v

    return Settings(**yaml_filtered)
