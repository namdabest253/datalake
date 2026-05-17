"""Settings loaded from .env then config.yaml then CLI flags.

See docs/05-inference-client.md §Client config.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Paths(BaseModel):
    sqlite_db: Path = Path("./.datalake/datalake.db")
    logs_dir: Path = Path("./.datalake/logs")
    heuristics: Path = Path("./datalake/prompts/heuristics.yaml")
    judge_rubric: Path = Path("./datalake/eval/judge_rubric.yaml")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Secrets
    wafer_api_key: str = ""
    openai_api_key: str | None = None
    judge_api_key: str = ""

    # Models
    wafer_base_url: str = "https://api.wafer.ai/v1"
    wafer_loop_model: str = "qwen-3.5-397b"
    judge_model: str = "qwen-3.5-strong"
    openai_baseline_model: str = "gpt-4-turbo"

    # Concurrency
    wafer_concurrency: int = 64
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


def load_settings(config_yaml: Path | str = "config.yaml") -> Settings:
    """Merge YAML defaults with .env / env vars. CLI flags overlay this at the call site."""
    yaml_path = Path(config_yaml)
    yaml_data: dict = {}
    if yaml_path.exists():
        yaml_data = yaml.safe_load(yaml_path.read_text()) or {}
    return Settings(**yaml_data)
