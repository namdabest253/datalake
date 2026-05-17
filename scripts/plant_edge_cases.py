"""Plant 20 hand-crafted compliance edge cases into the demo corpus.

These drive the "compliance catching" moments judges remember. Files are saved
with SYNTHETIC_ prefix so they're disclosable in the demo narrative.

Each case is a realistic-looking excerpt with embedded trigger language for one
or two compliance regimes. The `expected_flags` field is the ground-truth
labeling we want the agent to recover — used later by the eval harness.

See docs/08-ops-and-demo.md §Data license notes and PRD §11.

Usage:
    python scripts/plant_edge_cases.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SYNTHETIC_DIR = Path("demo_corpus/synthetic")


@dataclass(frozen=True)
class EdgeCase:
    slug: str
    category: str
    title: str
    body: str
    expected_flags: tuple[str, ...]
    expected_ownership: str
    expected_action: str  # license_ready | needs_consent | do_not_sell | archive


CASES: list[EdgeCase] = [
    # --- publisher exclusivity (3) ---
    EdgeCase(
        slug="elsevier_transfer",
        category="publisher_exclusive",
        title="Transformer-Based Methods for Catalysis Yield Prediction",
        body="""\
# Transformer-Based Methods for Catalysis Yield Prediction

**A. Patel¹, R. Okonkwo¹, M. Levin²**
¹Department of Chemical Engineering, University of Chicago
²Argonne National Laboratory

Published in *Journal of Catalysis*, vol. 412, pp. 88–104, 2024.
© 2024 Elsevier B.V. All rights reserved. This article may not be redistributed,
in whole or in part, without prior written permission from the publisher.

## Abstract
We present a transformer architecture for predicting catalytic yields...

## Acknowledgments
This work was supported in part by internal funds from the Pritzker School of
Molecular Engineering. The authors thank the Argonne LCRC for compute.
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="third_party_publisher",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="acm_exclusive",
        category="publisher_exclusive",
        title="A Type System for Effect Handlers in Distributed Workflows",
        body="""\
# A Type System for Effect Handlers in Distributed Workflows

J. Park, S. Mendes — University of Chicago
Proceedings of POPL 2025.

ACM Reference Format. Permission to make digital or hard copies of part or all
of this work for personal or classroom use is granted without fee provided that
copies are not made or distributed for profit or commercial advantage and that
copies bear this notice and the full citation on the first page. Copyrights for
components of this work owned by others than ACM must be honored. Abstracting
with credit is permitted. To copy otherwise, or republish, to post on servers
or to redistribute to lists, requires prior specific permission and/or a fee.
Request permissions from permissions@acm.org.

## Abstract
We extend algebraic effect handlers to a distributed setting...
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="joint",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="nature_green_oa",
        category="publisher_exclusive",
        title="Cryo-EM Structure of a Eukaryotic Replisome Intermediate",
        body="""\
# Cryo-EM Structure of a Eukaryotic Replisome Intermediate

L. Tanaka, E. Brown (University of Chicago Department of Molecular Genetics)
Nature, vol. 631, pp. 442–449 (2024). https://doi.org/10.1038/s41586-024-XXXXX

This version is the author's accepted manuscript, deposited per Springer Nature's
Green OA policy. The version of record is © Springer Nature. Reuse of the
published version is subject to the publisher's terms; reuse of this accepted
manuscript is permitted for non-commercial scholarly purposes only, with an
embargo of 6 months from the date of online publication.

## Abstract
We report a 2.8 Å structure of...
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="third_party_publisher",
        expected_action="do_not_sell",
    ),

    # --- IRB / HIPAA (3) ---
    EdgeCase(
        slug="clinical_trial",
        category="irb_hipaa",
        title="A Phase II Trial of XJ-7 in Refractory Glioblastoma",
        body="""\
# A Phase II Trial of XJ-7 in Refractory Glioblastoma

PI: M. Alvarez, MD, PhD — University of Chicago Medicine, Section of Neuro-Oncology

ClinicalTrials.gov identifier: NCT0XXXXXXX
IRB Protocol 21-1438 (University of Chicago BSD IRB), approved 2022-03-14.
All participants provided written informed consent. Patient identifiers were
removed per HIPAA Safe Harbor (45 CFR 164.514(b)(2)) prior to analysis.

## Results
Of 64 enrolled patients (median age 58, 41% female), 19 (29.7%) achieved a
partial response at 12 weeks. Adverse events were consistent with the Phase I
safety profile (see Supplementary Table 2).

## Funding
NCI R01-CA-2XXXXX; institutional bridge funding from UCM Comprehensive Cancer
Center.
""",
        expected_flags=("hipaa", "irb_restricted"),
        expected_ownership="joint",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="patient_cohort",
        category="irb_hipaa",
        title="EHR-Derived Risk Scores for Postoperative Sepsis",
        body="""\
# EHR-Derived Risk Scores for Postoperative Sepsis

K. Chen, B. Adekunle — Department of Anesthesia and Critical Care, UChicago Medicine

We trained a gradient-boosted model on de-identified electronic health records
from 41,238 surgical admissions at three UChicago Medicine campuses, 2018–2023.
This study was reviewed and approved by the University of Chicago Biological
Sciences Division IRB (Protocol 22-0917) under a waiver of informed consent
(45 CFR 46.116(f)). All PHI was scrubbed using the Safe Harbor method prior to
researcher access; a limited dataset was used under a Data Use Agreement.

Re-identification, re-distribution, or commercial reuse of the underlying patient
records is strictly prohibited by the DUA and HIPAA Privacy Rule.
""",
        expected_flags=("hipaa", "irb_restricted"),
        expected_ownership="institution",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="mental_health_survey",
        category="irb_hipaa",
        title="Mental Health Outcomes in First-Generation College Students",
        body="""\
# Mental Health Outcomes in First-Generation College Students:
A Multi-Site Longitudinal Study

R. Iqbal, N. Greene — Department of Psychology, University of Chicago

Participants (N=812) completed annual PHQ-9 and GAD-7 assessments alongside
academic record release. The protocol was approved by the UChicago Social and
Behavioral Sciences IRB (Protocol SBS-23-0204). Informed consent included
explicit limits on secondary use: data may be shared only with researchers
approved by the IRB amendment process, and may not be transferred to commercial
entities for model training or other downstream uses.
""",
        expected_flags=("irb_restricted",),
        expected_ownership="institution",
        expected_action="do_not_sell",
    ),

    # --- FERPA (2) ---
    EdgeCase(
        slug="grade_prediction",
        category="ferpa",
        title="Predicting First-Year Retention from Registrar Records",
        body="""\
# Predicting First-Year Retention from Registrar Records

D. Whitfield, A. Romero — Office of Institutional Research, University of Chicago

We linked term-level GPA, course enrollment, and demographic variables for the
incoming undergraduate cohorts of 2019 through 2022 (N=6,401) with retention
outcomes at the start of year two. Data were accessed under a Memorandum of
Understanding with the Office of the University Registrar, in compliance with
the Family Educational Rights and Privacy Act (FERPA, 20 U.S.C. § 1232g).
Identifiable records were not removed from the secure analytics enclave; only
aggregate results were exported.

External redistribution of the underlying student-level data is prohibited.
""",
        expected_flags=("ferpa",),
        expected_ownership="institution",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="course_outcomes",
        category="ferpa",
        title="Effects of Active Learning on Introductory Physics Outcomes",
        body="""\
# Effects of Active Learning on Introductory Physics Outcomes

C. Vasquez, T. Holm — Department of Physics, University of Chicago

We compared exam performance and DFW rates across two PHYS 121 sections in
Autumn 2023 (N=247 students). Roster, enrollment, and grade data were obtained
from the University Registrar under FERPA's "school official with legitimate
educational interest" exception. Per FERPA, individual student records may not
be disclosed without written consent; results in this paper are reported as
section-level aggregates with cell suppression for N<10.
""",
        expected_flags=("ferpa",),
        expected_ownership="institution",
        expected_action="archive",
    ),

    # --- export controls / classified (2) ---
    EdgeCase(
        slug="darpa_distrib_b",
        category="export_controls",
        title="Resilient Routing in Contested RF Environments",
        body="""\
# Resilient Routing in Contested RF Environments

S. Krieger, P. Yamashita — UChicago Computer Science / Tech Strategy Lab

Sponsored by DARPA under contract HR0011-23-C-XXXX. Approved for public release;
**Distribution Statement B**: Distribution authorized to U.S. Government agencies
only. Other requests for this document shall be referred to the Defense Advanced
Research Projects Agency Public Release Center.

Portions of this work describe techniques that may be subject to the Export
Administration Regulations (EAR, 15 CFR 730–774). Authors are responsible for
verifying applicable export-control determinations before any external sharing.
""",
        expected_flags=("export_controlled",),
        expected_ownership="funder",
        expected_action="do_not_sell",
    ),
    EdgeCase(
        slug="itar_flagged",
        category="export_controls",
        title="Hypersonic Boundary-Layer Transition: A Reduced-Order Approach",
        body="""\
# Hypersonic Boundary-Layer Transition: A Reduced-Order Approach

J. Park, M. Olsen — Pritzker School of Molecular Engineering, UChicago, and
Air Force Research Laboratory, Wright-Patterson AFB.

Notice: This document contains technical data whose export is restricted by the
Arms Export Control Act (Title 22, U.S.C. Sec. 2751 et seq.) or the Export
Administration Act of 1979, as amended (Title 50, U.S.C. App. 2401 et seq.).
Violations of these export laws are subject to severe criminal penalties.
Disseminate in accordance with provisions of DoD Directive 5230.25.
""",
        expected_flags=("export_controlled",),
        expected_ownership="joint",
        expected_action="do_not_sell",
    ),

    # --- clean / license-ready (3) ---
    EdgeCase(
        slug="plos_cc_by",
        category="clean",
        title="A Diffusion-Based Generative Model of Protein Backbones",
        body="""\
# A Diffusion-Based Generative Model of Protein Backbones

H. Liu, A. Banerjee — Department of Statistics, University of Chicago

Published in *PLOS Computational Biology*, March 2025.
**This is an open access article distributed under the terms of the Creative
Commons Attribution License (CC-BY 4.0), which permits unrestricted use,
distribution, and reproduction in any medium, provided the original author and
source are credited.**

Funded by NSF Award #2245678. Per NSF Public Access Policy, the version of
record is freely available and no embargo applies.
""",
        expected_flags=("clean", "public_domain"),
        expected_ownership="joint",
        expected_action="license_ready",
    ),
    EdgeCase(
        slug="nist_public_domain",
        category="clean",
        title="Reference Implementations of Post-Quantum KEMs: A Benchmark Suite",
        body="""\
# Reference Implementations of Post-Quantum KEMs: A Benchmark Suite

J. Halevy — National Institute of Standards and Technology (NIST), Cryptographic
Technology Group

NIST contribution; not subject to copyright in the United States (17 U.S.C. § 105).
This work was prepared by a federal employee as part of official duties and is in
the public domain. External reuse, including commercial reuse, is permitted
without restriction; attribution is appreciated but not required.

A companion paper with co-authors at UChicago is forthcoming and will appear
under a separate (non-public-domain) license.
""",
        expected_flags=("public_domain", "clean"),
        expected_ownership="institution",
        expected_action="license_ready",
    ),
    EdgeCase(
        slug="press_cc0_dataset",
        category="clean",
        title="Chicago Newspaper Archive (1900–1950): Cleaned OCR Corpus",
        body="""\
# Chicago Newspaper Archive (1900–1950): Cleaned OCR Corpus

R. Yamamoto, K. Singh — University of Chicago Press, Digital Collections.

Released by the University of Chicago Press under Creative Commons Zero (CC0
1.0 Universal Public Domain Dedication). Rights holders have explicitly waived
all copyright and related rights to the dataset and its derivative works. The
underlying newspapers are out of copyright in the United States. Permitted uses
include, without limitation, commercial machine learning training.

Recommended citation: Yamamoto, R., & Singh, K. (2024). Chicago Newspaper
Archive, 1900–1950. University of Chicago Press Digital Collections.
""",
        expected_flags=("clean", "public_domain"),
        expected_ownership="institution",
        expected_action="license_ready",
    ),

    # --- embargo (2) ---
    EdgeCase(
        slug="pharma_embargo",
        category="embargo",
        title="Mechanism of Action of Compound XJ-7 in Murine Glioma Models",
        body="""\
# Mechanism of Action of Compound XJ-7 in Murine Glioma Models

PI: M. Alvarez — UChicago Medicine, Section of Neuro-Oncology
Co-funded by Helios Biosciences, Inc. under Sponsored Research Agreement SRA-2022-118.

Per the terms of SRA-2022-118 §7.3 (Publication Embargo), all findings, data,
and figures referencing compound XJ-7 are subject to a **24-month publication
embargo** from the date of submission to the sponsor for review (sponsor
submission date: 2024-09-12). External distribution, including deposit in any
public training corpus, is prohibited prior to embargo expiration on 2026-09-12.
""",
        expected_flags=("publisher_exclusive", "embargo"),
        expected_ownership="joint",
        expected_action="needs_consent",
    ),
    EdgeCase(
        slug="industry_sponsor_embargo",
        category="embargo",
        title="Latency Optimization for Real-Time Recommender Inference",
        body="""\
# Latency Optimization for Real-Time Recommender Inference

E. Park, A. Marquez — Toyota Technological Institute at Chicago (TTIC), in
collaboration with NetStream Labs (industry partner).

This manuscript is subject to NetStream Labs' standard pre-publication review
process (NetStream MSA §5.4). Publication and external distribution are
permitted only after sponsor review and explicit written release. As of the
date on this draft, sponsor release has **not** been granted.
""",
        expected_flags=("embargo",),
        expected_ownership="unclear",
        expected_action="needs_consent",
    ),

    # --- contested / industry-funded ownership (3) ---
    EdgeCase(
        slug="google_residency",
        category="contested_ownership",
        title="Scalable Mixture-of-Experts Routing at the 100B+ Parameter Regime",
        body="""\
# Scalable Mixture-of-Experts Routing at the 100B+ Parameter Regime

A. Singh¹², L. Romero¹, J. Park², S. Mendes²
¹University of Chicago, Department of Computer Science
²Google Research (work performed during A. Singh's Google AI Residency, 2023–2024)

This paper describes work performed jointly during the residency program.
Per the Google AI Residency Agreement (Schedule B §4), intellectual property
arising from work performed during the residency is jointly owned, with Google
holding a perpetual, royalty-free, non-exclusive license to commercial use
and the right to first review on any external publication.
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="joint",
        expected_action="needs_consent",
    ),
    EdgeCase(
        slug="pharma_dual",
        category="contested_ownership",
        title="A Generative Model for Lead-Like Small Molecule Design",
        body="""\
# A Generative Model for Lead-Like Small Molecule Design

K. Anand¹, M. Levin², R. Iqbal¹
¹Department of Chemistry, University of Chicago
²Senior Scientist, Vertex Pharmaceuticals (Boston, MA)

M. Levin contributed during a sabbatical jointly funded by Vertex Pharmaceuticals
and the UChicago Department of Chemistry. The author contribution and IP
allocation between Vertex and the University is governed by Sponsored Research
Agreement VRT-2023-091, which has not been disclosed publicly. The authors
have not obtained written permission from Vertex to relicense this work for
commercial training data use.
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="unclear",
        expected_action="needs_consent",
    ),
    EdgeCase(
        slug="consultant_authorship",
        category="contested_ownership",
        title="Causal Inference for Programmatic Ad Auctions",
        body="""\
# Causal Inference for Programmatic Ad Auctions

P. Whitfield — Booth School of Business, University of Chicago

Disclosure: During preparation of this manuscript, the author served as a paid
consultant to AdMetric Analytics, Inc. AdMetric provided proprietary auction
log data under a Non-Disclosure Agreement (NDA-2024-AM-073). The NDA permits
publication of aggregate results in peer-reviewed venues but does not authorize
re-distribution of underlying data, derivative datasets, or trained models
derived from the underlying data.
""",
        expected_flags=("publisher_exclusive",),
        expected_ownership="unclear",
        expected_action="needs_consent",
    ),

    # --- ambiguous / unclear (2) ---
    EdgeCase(
        slug="missing_affiliations",
        category="ambiguous",
        title="Notes on Self-Distillation Dynamics in Transformer Language Models",
        body="""\
# Notes on Self-Distillation Dynamics in Transformer Language Models

J. Park, anonymous co-author

A preliminary write-up. Distribution and re-use rights are not specified in
this document. No funding statement is provided. The author can be reached at
jpark@example.org.
""",
        expected_flags=("unclear",),
        expected_ownership="unclear",
        expected_action="archive",
    ),
    EdgeCase(
        slug="preprint_no_funder",
        category="ambiguous",
        title="A Light-Weight Approach to Token-Level Hallucination Detection",
        body="""\
# A Light-Weight Approach to Token-Level Hallucination Detection

S. Ferreira, H. Liu

Working draft, March 2025. No journal submission yet; no funder statement;
no copyright notice. The authors note that they began this work during a
summer internship at an undisclosed industry lab but have continued it
independently. The terms of the original internship agreement are not on
file with the University.
""",
        expected_flags=("unclear",),
        expected_ownership="unclear",
        expected_action="needs_consent",
    ),
]


def write_case(case: EdgeCase) -> Path:
    path = SYNTHETIC_DIR / f"SYNTHETIC_{case.category}_{case.slug}.md"
    expected = (
        "\n\n<!--\n"
        f"_expected:\n"
        f"  flags: {list(case.expected_flags)}\n"
        f"  ownership: {case.expected_ownership}\n"
        f"  action: {case.expected_action}\n"
        "-->\n"
    )
    path.write_text(case.body.rstrip() + expected)
    return path


def main() -> None:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    assert len(CASES) == 20, f"expected 20 cases, found {len(CASES)}"
    written = [write_case(c) for c in CASES]
    print(f"wrote {len(written)} synthetic edge cases to {SYNTHETIC_DIR}/")
    by_category: dict[str, int] = {}
    for c in CASES:
        by_category[c.category] = by_category.get(c.category, 0) + 1
    for cat, n in sorted(by_category.items()):
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
