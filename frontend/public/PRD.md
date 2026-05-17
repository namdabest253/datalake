# Product Requirements Document: Datalake

**Version:** 0.4 (Hackathon MVP — competitive landscape added)
**Owner:** [Your name]
**Last updated:** May 16, 2026
**Status:** Draft
**Hackathon track:** Wafer — Best Inference

---

## 1. Overview

Datalake is an agentic data preparation system built specifically for universities and research institutions. It ingests raw institutional data — research papers, grant proposals, datasets, faculty work — and runs a dense multi-pass agent loop on Wafer that does two jobs in one pass: **catalog** (what is this, who owns it, what compliance regime governs it) and **label** (rich training-grade metadata: methodology, novelty, claims, citations, structure).

The output is a sellable, AI-lab-ready dataset. Institutions get an inventory of what they own *and* a value-multiplied version of their rights-clean data, packaged for direct sale to AI labs.

The agent loop is the product. Cheap, fast inference on Wafer is what makes the loop economically viable — at GPT-4 prices, the per-document cost would erase the entire commercial margin institutions could ever earn from licensing the data.

## 2. Problem

Universities hold the most valuable untapped training corpus on earth: decades of original research, grant-funded work, and expert-written analysis that AI labs are actively trying to license. The market exists today — major AI companies are reaching out to university presses asking to buy data — but the deals don't close.

Two reasons:

**The catalog problem.** Institutions don't know what they own. Files are scattered across departments, ownership is ambiguous (faculty? university? publisher? grant funder?), and compliance is a minefield (FERPA, HIPAA, IRB consent, publisher exclusivity). Without an inventory tagged by rights status, the legal office cannot approve a single sale.

**The labeling problem.** Even rights-clean raw research data isn't directly sellable as training data. AI labs want enriched corpora: papers tagged with methodology, novelty claims, supporting evidence, citation graphs, and structured metadata. Raw PDFs are worth pennies; richly labeled papers are worth dollars. Universities don't have the labor or the labeling infrastructure to do this conversion.

Both problems block the same revenue stream. Both are inference-bound. **Solving them together unlocks the trillion-dollar institutional data market that has stayed frozen for two years.**

## 3. Competitive landscape

The AI data labeling market is large and crowded — Scale AI, Surge AI, Labelbox, Snorkel, SuperAnnotate, V7, Encord, Appen, Sama, iMerit. Most do one of three things: managed human labeling (Scale, Surge, Appen, Sama, iMerit), labeling platform software for in-house teams (Labelbox, SuperAnnotate, V7, Encord), or programmatic weak-supervision labeling (Snorkel). The market reached roughly $19B in 2025 and is projected to hit $57B by 2030.

**None of them serve the institutional seller.** Every incumbent assumes the customer already has the data, knows what it is, and has the legal right to use it. That assumption breaks completely for universities — which is precisely why AI labs are knocking on university presses and the deals aren't closing.

### What's structurally different about Datalake

| | Existing labelers (Scale, Surge, Snorkel, Labelbox) | Datalake |
|---|---|---|
| **Customer** | AI labs (data buyers) | Institutions (data sellers) |
| **Workflow start** | "Here's data; label it" | "Here's a chaotic file share; tell me what we own" |
| **Compliance / ownership inference** | Not in scope; assumed pre-cleared | First-class output, every document |
| **Cost structure** | $30–$100/hr human experts → $30–$60 per scientific paper | Fractions of a cent per document on Wafer |
| **Ontology setup** | Customer defines | Pre-built for institutional data |
| **Workflow integration** | Standalone labeling step | Catalog + labeling as one combined inference pipeline |

The economics are the most decisive piece. AI labs pay roughly $1–$10 per high-quality scientific datapoint. Expert scientific annotation at Surge-tier rates is $30–$60 per paper. **The seller has no margin if labeling runs through a human-labeling vendor**, which is why incumbents are structurally locked out of this market regardless of intent.

### Why labeling, not just cataloging

A reasonable question: if the unique value is catalog + compliance inference, why not catalog with Datalake and hand the rights-clean subset to Scale for labeling? Five reasons it has to be one product:

1. **The economics only work end-to-end.** Handoff to Scale at $30–$60 per paper kills the seller's margin on every datapoint. Wafer at fractions of a cent per document is the only price point at which institutional data licensing is profitable for the seller. Routing customers to Scale routes them to an economic dead end.

2. **Catalog and label share the same inference.** When the agent loop reads a document to infer compliance and ownership, it's already extracting methodology, claims, structure, and citations. Splitting these into two vendor pipelines duplicates work and discards the architectural advantage of compounding context across passes.

3. **Vendor handoff is exactly the friction that froze the market.** Institutional legal offices spent the last two years not approving data deals because every additional vendor, contract, data transfer, and review cycle adds risk. "Now ship the rights-clean subset to a third party" reintroduces every friction the catalog step was meant to remove.

4. **Compliance signal has to ride with the labels.** The catalog pass discovers granular rights constraints ("this paper is partially derived from a grant restricting commercial redistribution") that change what an AI lab can do with the datapoint. Independent labeling loses that context and creates legal exposure for the seller.

5. **Catalog alone isn't a defensible business.** Catalog is a one-time engagement per institution. Labeling scales with the data, recurs, and is where lifetime value lives. A catalog-only product is consulting; a catalog + label product is permanent infrastructure inside the institution.

**Synthesis:** catalog is the wedge, labeling is the business. We don't compete with Scale — we serve a customer Scale's cost structure cannot reach. In the long term, traditional human-labeling vendors are a *partner* for final-mile expert review on high-value rights-clean subsets, not a competitor.

### One-line positioning

**"Scale AI labels data. Datalake makes university data labelable in the first place."**

## 4. Goals and non-goals

**Goals (MVP)**
- Ingest a folder of institutional documents (research papers + grant proposals for the demo slice).
- Run a dense agent loop per document that produces both a **catalog record** (type, ownership, compliance, commercial viability) and a **rich label payload** (methodology, novelty claims, evidence quality, citations, structured abstract).
- Demonstrate the agent loop visibly: judges see proposal → critique → refine → vote streaming live.
- Output a Hugging Face-compatible labeled dataset alongside the catalog.
- Run a side-by-side quality comparison: same documents labeled by single-pass GPT-4 vs. Wafer agent loop, with measurable quality delta on a held-out set.

**Non-goals (MVP)**
- Real institutional data connectors (S3, SharePoint, DSpace).
- Production compliance certifications.
- Buyer-side marketplace integration.
- Human-in-the-loop review.
- Domain coverage beyond research papers and grant proposals (lectures, datasets, admin docs are future scope).

## 5. Target users

**Primary (hackathon judges):** Wafer track. Rubric weights: Leverage of Fast Inference (7), Novelty (6), Demo (4), Impact (3).

**Primary (real-world):**
- University Chief Data Officers and Provosts' offices exploring data licensing as a revenue stream.
- Compliance and IP officers who need a defensible inventory before any external sale.
- AI labs (Anthropic, OpenAI, Google, Meta) sourcing high-quality scientific training data.
- Data marketplaces like Kled that want institutional supply.

**Validated demand:** We've already heard directly from a Chicago university CTO that major AI companies are knocking on university presses' doors trying to license data, that those deals haven't closed because of catalog and compliance gaps, and that the institution is in the process of building an internal data lake precisely to make this kind of work possible.

## 6. User stories

- As a university CDO, I want one tool that tells me what we own, what we can legally sell, *and* turns the sellable part into a high-value labeled dataset, so I can go from "we have data somewhere" to "we have a $5M revenue line" without standing up a labeling org.
- As a compliance officer, I want every document tagged with its applicable compliance regime and ownership chain, so I can approve or block licensing decisions with evidence.
- As an AI lab data buyer, I want to receive datasets that are not just rights-clean but also richly labeled with methodology, claims, and structured metadata — so the data is immediately useful for training without further preprocessing on my side.
- As a hackathon judge, I want to see a dense agent loop running live and understand that the loop's economics only work because of Wafer.

## 7. The agent loop (core innovation)

Every document runs through a multi-pass loop on Wafer. The loop does catalog and labeling in a single shared inference pipeline so the model's understanding compounds across passes.

1. **Read & extract** — Parse the document, extract text, structure, and references.
2. **Propose** — N parallel agents independently produce a draft record covering both catalog fields (type, ownership, compliance, commercial score) and label fields (methodology, novelty, claims, evidence, citations).
3. **Critique** — Separate agents critique each proposal against domain rules: Is the methodology label specific enough? Is the ownership inference defensible? Are the compliance flags complete?
4. **Refine** — Proposals revised in light of critiques.
5. **Vote** — Consensus agent selects strongest refined record or flags for low confidence.
6. **Enrich** — Final agent produces a rich descriptive payload: structured abstract, claim graph, novelty rationale, citation context — the kind of metadata AI labs actually pay for.

Total inference calls per document: 10–20. At Wafer prices this is fractions of a cent. At GPT-4 prices, ~$1 per document on a 10M-file corpus is $10M — gone before the institution sees a dollar of licensing revenue. **The loop is the product. Wafer's economics are what make the product real.**

## 8. Functional requirements

### 8.1 Ingestion
- Folder or ZIP upload of `.pdf`, `.txt`, `.md`, `.json`.
- Text extraction via PyMuPDF for PDFs.
- Reference extraction (citations parsed where present).
- Demo slice: research papers from arXiv + grant abstracts from NSF/NIH databases.

### 8.2 Catalog output (per document)
- **Content type:** `research_paper`, `grant_proposal`, `dataset_description`, `faculty_publication`, `other`.
- **Ownership inference:** `institution`, `faculty`, `third_party_publisher`, `funder`, `joint`, `unclear`, with confidence score and one-sentence rationale.
- **Compliance flags:** multi-label across `ferpa`, `hipaa`, `irb_restricted`, `publisher_exclusive`, `public_domain`, `clean`, `unclear`.
- **Commercial viability:** 0–100 score and action: `license_ready`, `needs_consent`, `do_not_sell`, `archive`.

### 8.3 Label output (per document) — the AI-lab-ready payload
- **Structured abstract:** problem, approach, findings, limitations.
- **Methodology:** specific techniques used (e.g., "fine-tuned BERT," "double-blind RCT," "ethnographic field study"), with taxonomic tags.
- **Novelty claim:** the specific contribution the paper claims to make, extracted verbatim where possible.
- **Evidence quality:** type of evidence (empirical / theoretical / simulation / survey), strength assessment, sample size if applicable.
- **Claim graph:** main claims with supporting evidence pointers within the document.
- **Citations:** parsed reference list with cited-work classification.
- **Domain tags:** field, subfield, application area.

This is the metadata that turns a raw PDF (pennies of value) into a training-grade datapoint (dollars of value).

### 8.4 Live dashboard
The dashboard is the demo. Required panels:

- **Document stream:** finalized records flow onto the screen faster than a human could read. Counter ticks: documents per second, total processed.
- **Agent loop visualizer:** for a sampled document, render the proposal → critique → refine → vote cycle live. Make the loop tangible.
- **Quality metrics:** inter-agent agreement, average confidence, low-confidence flag rate, all live-updating.
- **Cost meter:** running inference cost on Wafer with a parallel "GPT-4 equivalent" counter climbing 50–100x faster. The economic argument visible at all times.
- **Catalog filter view:** post-run, filter the corpus by compliance status. Toggle "show only license-ready" to collapse the corpus to its sellable subset, with estimated total market value.
- **Side-by-side quality panel:** results of the GPT-4 baseline comparison (see 8.5).

### 8.5 Side-by-side quality evaluation
- On a held-out subset (~200 documents), run two pipelines in parallel:
  - **Baseline:** single-pass GPT-4 producing the same combined catalog + label payload.
  - **Datalake:** full Wafer agent loop.
- A third stronger judge model evaluates each pair against the same domain criteria and computes:
  - Win rate of Datalake vs GPT-4
  - Average quality delta on each label dimension
  - Cost per document for each pipeline
- Display in a dedicated panel during demo. **This is the answer to "are the labels useful?"**

### 8.6 Dataset export
- JSONL with one row per document: source reference, full catalog record, full label payload, agent trace, costs.
- Hugging Face `datasets`-compatible format.
- Auto-generated `dataset_card.md` with corpus stats, methodology, quality metrics, comparison to GPT-4 baseline, total cost.
- Separate catalog CSV for the institution's compliance team.

## 9. Non-functional requirements

- **Speed visible in demo:** label stream outpaces reading speed; per-document loop completes in <5 seconds end-to-end.
- **End-to-end live:** every screen reachable from one CLI command. No mocked panels.
- **Cost transparency:** demo run under $30 of Wafer credits, displayed live with GPT-4 counter as foil.
- **Quality delta:** Datalake ≥ 65% win rate vs single-pass GPT-4 baseline on held-out eval. Cost-per-document ≤ 30% of GPT-4 baseline.

## 10. Technical architecture

**Stack**
- Python 3.11+, `asyncio` + `aiohttp` for parallel inference, semaphore-bounded concurrency.
- Inference: Wafer Serverless (Qwen3.5-397B) for the loop; OpenAI GPT-4 for baseline only; one stronger model as judge.
- Parsing: PyMuPDF for PDFs.
- Storage: SQLite (catalog records, label payloads, full agent traces, costs).
- Frontend: Streamlit for fast iteration. Real-time updates via auto-refresh.

**Data flow**

```
Folder → PDF Parser → Text Queue
       → Agent Loop (Propose × N → Critique → Refine → Vote → Enrich)
       → Catalog Store + Label Store + Trace Store
       → Side-by-side Evaluator (Wafer vs GPT-4)
       → Streamlit Dashboard + JSONL Export
```

Each pass is a separate Wafer call with a tightly scoped prompt and JSON schema. Proposals fan out via `asyncio.gather`; critiques fan out across proposals; refinement merges critiques; voting consolidates. State machine logs trace at every transition.

## 11. Demo corpus

A focused synthetic-but-realistic corpus that mirrors what a university actually holds:

- **15,000 arXiv papers** across multiple disciplines (CS, biology, physics, economics) — varied methodologies, citation densities, novelty levels.
- **5,000 NSF grant abstracts** with PI info, funding amounts, abstracts — provides ownership ambiguity test cases (university vs faculty vs federal funder).
- **~30 hand-crafted compliance edge cases** planted throughout:
  - Papers with mixed publisher exclusivity language
  - Grant-funded papers where ownership is contested
  - Papers describing human subjects research (IRB-restricted)
  - Pre-cleared, university-press-released datasets (license-ready, high value)

Folder structure mimics a real university file share. Edge cases drive the "compliance catching" moments judges remember.

Live demo: type the heuristics for label fields (e.g., "for methodology, prefer specific named techniques over general categories") in front of judges to prove the system is configurable, not pre-baked.

## 12. Success metrics (mapped to the Wafer rubric)

| Criterion | Pts | How Datalake scores it |
|---|---|---|
| **Leverage of Fast Inference** | 7 | The agent loop is 10–20 calls per document. The product is economically dead at GPT-4 prices — institutions earn licensing revenue measured in dollars per document, so prep cost must be cents. Dense critique-refine loops with speculative parallelism = "treat tokens as cheap" exactly as the rubric describes. |
| **Novelty of the Idea** | 6 | Not a chatbot. Not RAG. An institution-specific data preparation system that does catalog and labeling in one inference pipeline, targeting a market (university data licensing) that didn't exist eighteen months ago and has no incumbent product. |
| **Execution & Demo** | 4 | Live document stream, live agent loop visualizer, live cost meter with GPT-4 foil, live filter for license-ready subset, live quality comparison. Speed is shown, not asserted. |
| **Impact / Real-World Fit** | 3 | Already-validated demand from a Chicago university CTO. Major AI labs actively trying to license this data today. Multi-billion-dollar market unlocked by solving a concrete inference-bound bottleneck. Points at a much bigger product (every R1 institution, hospital system, museum, research lab). |

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Agent loop labels don't beat GPT-4 on the eval | Pick label dimensions where multi-pass critique demonstrably helps (subjective, multi-attribute, ambiguous fields like novelty claim, methodology specificity). Tune prompts against the held-out set before demo. |
| Compliance inference looks too aggressive or too lenient on edge cases | Plant the edge cases with detectable signals; tune the critique prompts iteratively until the planted cases land correctly. |
| Synthetic corpus feels fake to judges | Bulk is real (arXiv, NSF) — only the ~30 planted compliance cases are synthetic. Lead with that framing. |
| "Aren't your labels just AI-generated and therefore low-quality?" | Side-by-side quality panel against GPT-4 baseline with an independent judge model is the direct answer. Also: AI labs already train on AI-labeled data; the question is whether the labels beat the alternative, which we prove on stage. |
| Demo crashes or rate-limits mid-run | Pre-process the bulk corpus before stage; live processing runs against a held-back slice. Pre-recorded fallback video ready. |
| Judges ask "why universities specifically, why not just generic labeling?" | Answer: universities are the only place where catalog + label converge into a single workflow with a single buyer (AI labs licensing rights-clean training data). Generic labeling is a crowded market; institutional data prep is empty. |

## 14. Future scope (beyond MVP)

- **Real institutional connectors:** S3, SharePoint, DSpace, Fedora, Box.
- **Coverage expansion:** lectures and course videos (multimodal), datasets, faculty publications, archival material.
- **Active learning:** flag low-confidence items for human review via a Mercor-style on-demand pool of domain experts (postdocs, librarians).
- **Marketplace integration:** one-click publish of license-ready labeled datasets to Kled, Hugging Face Hub, or direct deals with AI labs.
- **Continuous ingestion:** watch institutional repositories for new uploads, incrementally catalog and label.
- **Multi-institution federation:** standardized compliance taxonomy across universities, enabling pooled offerings to AI labs.
- **Vertical expansion:** the same system applied to hospital systems (medical research), museums (archival material), and research labs (experimental data).

## 15. Open questions

- For the judge model in the side-by-side eval, do we use Claude/GPT-4 via API, or another Wafer-hosted model? Wafer-only is a better sponsor story.
- Should the demo include a one-slide reference to the Chicago CTO conversation as the "real customer" proof point? (Recommendation: yes, briefly, in the impact slide.)
- How many proposal agents (N) is the right default for the demo? 3 keeps cost low and the visualizer readable; 5 makes the consensus story stronger.
- Does the JSONL export need to match an existing AI-lab data format convention (Anthropic dataset format, OpenAI fine-tune format)? If so, which one for the demo?