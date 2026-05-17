# 00. Overview

Datalake is an agentic data-preparation system for universities. It ingests institutional documents and runs a dense multi-pass agent loop on Wafer that produces a **catalog record** (what is this, who owns it, what compliance applies) and a **rich label payload** (methodology, novelty, claims, evidence, citations) per document.

This doc tree is the **implementation spec**. Product reasoning lives in [`../PRD.md`](../PRD.md). Open this file first; everything else is reachable from the coverage map below.

## Purpose

Build a demo-quality MVP for the Wafer "Best Inference" hackathon track that:
- Ingests a folder of research papers and grant proposals.
- Runs a 6-pass agent loop per doc on Wafer with `N=3` parallel proposers.
- Emits a Hugging Face-compatible labeled dataset + a compliance catalog.
- Runs a side-by-side quality eval vs single-pass GPT-4 on ~200 held-out docs.
- Streams everything to a Streamlit dashboard so judges see the loop live.

## Non-purpose (MVP boundary)

Not in scope and explicitly not designed for:
- Real institutional connectors (S3, SharePoint, DSpace) — local folder only.
- Production compliance certification — heuristic labels with confidence scores only.
- Buyer-side marketplace integration — file export only.
- Human-in-the-loop review — full automation with `partial=true` flag on failures.
- Multi-tenancy, auth, durable queues, multi-process workers.

## Demo north star

The 60-second judge experience:

1. Open the dashboard. Document records stream onto the screen faster than a human can read; counter ticks past 1k docs.
2. The agent-loop visualizer shows a sampled doc going through `propose → critique → refine → vote → enrich` in real time. Three parallel proposal bubbles, three critique bubbles.
3. The cost meter shows Wafer at $0.02 cumulative; the GPT-4 foil counter at $187 and climbing.
4. Click "Filter: license-ready" — the corpus collapses to its sellable subset with an estimated $2.3M market value chip.
5. Side-by-side panel shows Datalake beating GPT-4 on 71% of pairs.

Every panel in this list is non-mocked. If a panel can't be made live, it doesn't ship.

## Success criteria (measurable)

| Metric | Target | Reference |
|---|---|---|
| End-to-end per-doc loop | <5s | PRD §9 |
| Datalake win rate vs GPT-4 | ≥65% | PRD §9 |
| Cost per doc vs GPT-4 | ≤30% | PRD §9 |
| Wafer demo budget | <$30 cumulative | PRD §9 |

## Glossary

| Term | Meaning |
|---|---|
| **Catalog** | The compliance/ownership/commercial record per document. See [`04`](04-data-model.md). |
| **Label** | The AI-lab-ready metadata payload (methodology, novelty, claims). See [`04`](04-data-model.md). |
| **Pass** | One stage of the agent loop (`propose`, `critique`, `refine`, `vote`, `enrich`). See [`02`](02-agent-loop.md). |
| **Call** | One inference API call. A pass may comprise 1 or more calls (e.g., `propose` = 3 parallel calls). |
| **Proposal** | A draft record from one proposer agent. 3 per doc. |
| **Critique** | A criticism of a proposal from a critic agent. |
| **Judge** | The eval model that scores Datalake vs GPT-4 pairs. See [`07`](07-evaluation.md). |
| **Voter** | The pass-5 agent that picks the strongest refined proposal. |
| **Run** | One end-to-end invocation across a corpus. Identified by `run_id`. |
| **Verbose-traced doc** | Every Kth doc (K=10) where prompts + responses are captured inline for the visualizer. |

## Coverage map

| PRD section | Topic | Home doc |
|---|---|---|
| §1 Overview | Product framing | This file |
| §2 Problem | Catalog + labeling problem | This file (purpose) |
| **§3 Competitive landscape** | Positioning + cost-meter foils + judge Q&A | [`06-dashboard.md`](06-dashboard.md) (3rd foil), [`08-ops-and-demo.md`](08-ops-and-demo.md) (judge questions) |
| §4 Goals/non-goals | MVP boundary | This file |
| §5 Target users | Hackathon judges + real-world | This file (purpose) |
| §6 User stories | — | Product context, see PRD |
| §7 Agent loop | 6-pass loop mechanics | [`02-agent-loop.md`](02-agent-loop.md) |
| §8.1 Ingestion | Folder/ZIP parsing, PyMuPDF | [`01-architecture.md`](01-architecture.md) |
| §8.2 Catalog output | Catalog schema | [`04-data-model.md`](04-data-model.md), [`03`](03-prompts-and-schemas.md) |
| §8.3 Label output | Label schema | [`04-data-model.md`](04-data-model.md), [`03`](03-prompts-and-schemas.md) |
| §8.4 Live dashboard | All panels | [`06-dashboard.md`](06-dashboard.md) |
| §8.5 Side-by-side eval | Harness, judge | [`07-evaluation.md`](07-evaluation.md) |
| §8.6 Dataset export | JSONL, HF, CSV, dataset_card | [`04-data-model.md`](04-data-model.md) |
| §9 Non-functional reqs | Speed, cost, quality targets | This file (success criteria) |
| §10 Technical architecture | System layout | [`01-architecture.md`](01-architecture.md) |
| §11 Demo corpus | arXiv/NSF + planted edge cases | [`08-ops-and-demo.md`](08-ops-and-demo.md) |
| §12 Success metrics | Rubric mapping | PRD only — pitch artifact, not code |
| §13 Risks/mitigations | Demo failure modes | [`08-ops-and-demo.md`](08-ops-and-demo.md) |
| §14 Future scope | Post-MVP | PRD only |
| §15 Open questions | Resolved defaults | [`02`](02-agent-loop.md), [`04`](04-data-model.md), [`07`](07-evaluation.md) |

## Reading order

If you're new: read this file, then [`01-architecture.md`](01-architecture.md) for system shape, then [`02-agent-loop.md`](02-agent-loop.md) (the core innovation), then whichever module-specific doc matches what you're about to code.
