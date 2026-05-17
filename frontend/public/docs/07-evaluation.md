# 07. Evaluation

Side-by-side quality eval: same docs through Datalake's loop and through single-pass GPT-4, scored blind by a Wafer-hosted judge model. The answer to "are the labels actually useful?"

## Scope

- **~200 held-out docs** drawn from the same arXiv + NSF corpus, sampled for content-type and discipline diversity.
- **Separate CLI subcommand**: `datalake eval --n 200 --run-id <id>`. Independent of `datalake run`; can run before or after the main corpus loop.
- **The only place GPT-4 actually executes end-to-end.** Real OpenAI API spend, ~$1–5 per doc baseline depending on length.

## Pair construction (`datalake/eval/harness.py`)

For each held-out doc:

1. Run Datalake's full 6-pass loop → produces a record matching the `RefinedRecord + EnrichedPayload` shape (see [`03`](03-prompts-and-schemas.md)).
2. Run a single-pass GPT-4 baseline with the **combined catalog + label prompt** (one mega-prompt that asks for everything the loop produces, in one call).
3. Insert into `eval_pairs(doc_id, datalake_record, gpt4_record, a_is_datalake)`.

`a_is_datalake` is randomized per pair (50/50). Stored separately from the judge call so the judge never sees the mapping.

GPT-4 baseline prompt: a single user message containing the document text + a system message that asks for the full `ProposalRecord + EnrichedPayload` as one JSON object. Same taxonomies and heuristics injected.

## Judge model

**Single Wafer-hosted stronger model** (resolves PRD §15 #1 — "Wafer-only is a better sponsor story"). Configured in `config.yaml` as `judge_model`; default `qwen-3.5-strong` or whatever is the strongest Wafer-available model on demo day.

Verified during day-1 model selection: judge model must be **distinct from** the loop model (`wafer_loop_model`) — otherwise the judge has the same blind spots as the producer.

## Blinding

```python
# at pair-creation time
import random
a_is_datalake = random.random() < 0.5
record_a = datalake_record if a_is_datalake else gpt4_record
record_b = gpt4_record if a_is_datalake else datalake_record
```

Judge receives `(record_a, record_b, document_text)`. It returns `winner: A | B | tie`. Scoring code joins with `a_is_datalake` to attribute the win.

The judge prompt explicitly says the labels are randomized and that the model should evaluate purely on label quality, not stylistic guess of which is "the AI loop."

## Dimensions scored

Each dimension: 1–5 score per record.

| Dimension | What it measures |
|---|---|
| `methodology_specificity` | Named technique (5) vs vague category (1) |
| `novelty_claim_accuracy` | Claim is verifiably in the source (5) vs hallucinated (1) |
| `evidence_quality` | Strong support from text (5) vs hand-wave (1) |
| `citation_completeness` | All refs parsed + classified (5) vs missing (1) |
| `compliance_correctness` | Flags supported by document text (5) vs missed or invented (1) |
| `ownership_defensibility` | Rationale grounded in document evidence (5) vs guessed (1) |

Aggregate: weighted sum. Weights default to equal but tunable in `datalake/eval/scoring.py` (e.g., upweight `compliance_correctness` since false negatives there are the most expensive type of error).

## Scoring math (`datalake/eval/scoring.py`)

After all eval results in:

```python
n_datalake_wins = count(winner == "datalake")
n_gpt4_wins      = count(winner == "gpt4")
n_ties           = count(winner == "tie")
win_rate         = n_datalake_wins / (n_datalake_wins + n_gpt4_wins)

# per-dimension delta
for dim in DIMENSIONS:
    datalake_avg = mean(scores[pair][dim].datalake for pair in pairs)
    gpt4_avg      = mean(scores[pair][dim].gpt4 for pair in pairs)
    delta[dim]    = datalake_avg - gpt4_avg

# cost per doc (real for both — only place GPT-4 actually runs)
wafer_cost_per_doc = sum(call.cost_micro_usd
                         for call in inference_calls
                         if call.provider == "wafer"
                         and call.doc_id in eval_doc_ids) / n_docs
gpt4_cost_per_doc  = sum(call.cost_micro_usd
                         for call in inference_calls
                         if call.provider == "openai"
                         and call.cost_basis == "actual"
                         and call.doc_id in eval_doc_ids) / n_docs
cost_ratio = wafer_cost_per_doc / gpt4_cost_per_doc  # target ≤ 0.3 per PRD §9
```

Output:

- `eval_results` table rows.
- JSON report at `./.datalake/eval_report_<run_id>.json`.
- Dashboard panel 6 reads from `eval_results`.

## Tuning loop

Judge prompt and dimension rubrics live in `datalake/eval/judge_rubric.yaml`:

```yaml
methodology_specificity:
  5: "Names a specific technique like 'fine-tuned BERT on 12k labeled documents' or 'double-blind RCT with crossover design'"
  3: "Names a broad family like 'machine learning' or 'survey'"
  1: "Vague phrase like 'standard analysis' with no specifics"
# ... per dimension
```

Tweak between dry runs to make the judge consistent. Run `datalake eval --n 20 --dry-run` for fast iteration.

## Self-test

Before each eval run, the harness runs the judge on a **canonical pair** (committed to `tests/fixtures/eval/canonical_pair.json`) — a hand-curated "clearly Datalake wins" case where the Datalake record has rich methodology tags and the GPT-4 record has vague filler.

If the judge calls this canonical pair anything other than "Datalake wins, methodology delta ≥ +2", abort the eval run and surface a warning. This catches:

- Judge model regression.
- Prompt template corruption.
- Blinding-map bugs (the assertion is asymmetric: flipping the side doesn't change the outcome since the canonical record is so much better).

## Output

- `eval_pairs` (one row per evaluated doc).
- `eval_results` (one row per pair).
- `eval_report_<run_id>.json` (summary for the dataset card and dashboard).
- Dashboard panel 6 reads from `eval_results`.
