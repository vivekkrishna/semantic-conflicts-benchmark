# Semantic Conflicts Benchmark — Dataset Card

## 1. Formal Definition

> **A semantic conflict** exists between two passages when they produce mutually
> inconsistent conclusions under chains of logically certain inferences, even though
> each passage is individually coherent and the contradiction is not visible at the
> surface level without reasoning expansion.

This distinguishes the benchmark from prior work that tests surface-level
factual contradiction (e.g., FEVER, TruthfulQA). Items in this benchmark require
a model to operate in **derived semantic space** — enumerating the logical
consequences of each passage and checking whether those consequences are compatible.

Formally, two passages P₁ and P₂ are in semantic conflict at level L if and only if:

1. There exists a chain of L logically certain inference steps from P₁ and/or P₂
   that yields proposition C.
2. C contradicts a claim in P₁, P₂, or an intermediate inference.
3. No shorter chain of fewer than L steps can establish the same contradiction.
4. Every step in the chain follows with 100% logical certainty — no probabilistic
   or epistemic hedging is permitted.

---

## 2. Conflict Taxonomy

Items are categorized along two orthogonal dimensions:

### 2a. Structural category (`category` field)

| Category | Description | Typical domains |
|----------|-------------|-----------------|
| `cross_document` | Conflict arises between two independent sources | philosophy, law, science |
| `temporal` | One passage reflects an earlier state; the other a later one | science, law, content |
| `intra_document` | A single author or entity contradicts itself across two statements | content, teams |
| `normative` | A stated rule or norm conflicts with a described practice | law, teams, software |
| `state_divergence` | Two systems or agents hold incompatible beliefs about shared state | software, teams |

### 2b. Semantic type (implicit in domain and chain structure)

| Type | Description | Example |
|------|-------------|---------|
| **Logical contradiction** | Passages assert mutually exclusive propositions | Kant's universalizability vs. Rand's maxim of self-interest |
| **Epistemic inconsistency** | Passages commit to incompatible claims about what can be known or what exists | Wittgenstein's limits of language vs. Heidegger's project of attending to Being |
| **Temporal conflict** | An earlier belief is incompatible with evidence accepted at a later time | Steady-state cosmology vs. CMB temperature-redshift relation |
| **Normative conflict** | A rule prescribes what an agent must do; a practice description shows they cannot | NLRA collective bargaining right vs. contractual waiver |
| **State conflict** | Two authoritative sources assert contradictory facts about the same object | UserService reporting ACTIVE; BillingService reporting SUSPENDED |
| **Contextual incompatibility** | Passages are locally coherent but jointly incompatible under a shared operational context | EU data-residency mandate vs. global edge-caching architecture |

---

## 3. Dataset Composition

| Property | Value |
|----------|-------|
| Total items | 180 |
| Domains | 6 (philosophy, software, law, science, content, teams) |
| Items per domain | 30 |
| Conflict levels | L0–L5 (6 levels) |
| Conflict items | 108 (60%) — 18 per domain, 3 per level per domain |
| Consistent items | 48 (27%) — 8 per domain |
| Ambiguous items | 24 (13%) — 4 per domain |

### Verdict definitions

| Verdict | Definition |
|---------|------------|
| `conflict` | The passages are logically incompatible under at least one valid reasoning expansion; the conflict is established with 100% logical certainty |
| `consistent` | The passages are compatible under all reasonable readings; a single sentence can reconcile them using only information present in the passages |
| `ambiguous` | A conflict exists under one interpretation but disappears under another, and the passages do not supply enough information to determine which interpretation is correct |

### Difficulty gradient

| Level | Name | Minimum inference steps | Operational definition |
|-------|------|------------------------|------------------------|
| L0 | Surface | 0 | Contradiction is explicitly stated; reading both passages is sufficient |
| L1 | Immediate | 1 | One certain inference from a stated premise collides with the other passage |
| L2 | Two-hop | 2 | Two chained inferences expose the conflict |
| L3 | Three-hop | 3 | Three chained inferences |
| L4 | Four-hop | 4 | Four chained inferences |
| L5 | Deep | 5 | Five chained inferences |

`conflict_level` is the **minimum** number of inference steps required — no step in
the chain may be skippable without breaking the derivation.

---

## 4. Generation Methodology

Items were constructed following a structured protocol:

### 4a. Domain selection

Six domains were chosen to maximise structural diversity across conflict categories
(see Section 2a) while ensuring each domain uses a distinct passage form:

| Domain | Passage form | Conflict class |
|--------|-------------|----------------|
| philosophy | Named primary-source texts (paraphrased) | logical / epistemic |
| software | Realistic system documents — ADRs, runbooks, event logs | state / normative |
| law | Real statutes combined with synthetic contracts | normative / logical |
| science | Paraphrased real theories and empirical findings | temporal / logical |
| content | Invented creator profiles and posts | temporal / intra-document |
| teams | Invented team norms and new-joiner statements | normative / contextual |

### 4b. Item construction

**Conflict items (L0–L5):**

1. **Identify a real conceptual or factual tension.** For `paraphrased_real` and
   `composite` items, the tension must be grounded in primary sources (philosophy,
   science) or real legal instruments (law). For `synthetic` items, the tension
   must represent a realistic architectural, organisational, or personal scenario.

2. **Write two independent passages** such that neither passage is internally
   contradictory — each must be individually coherent and plausible.

3. **Write the reasoning chain.** Starting from the premises in both passages,
   derive intermediate conclusions using only 100%-certain logical entailment until
   a contradiction is reached. The chain length determines the target level.

4. **Verify the target level.** Apply the minimality test: for each step N, check
   whether removing that step and connecting the previous step directly to the next
   preserves the inference. If any step can be removed, the item is over-specified
   and must be revised.

5. **Filter trivial cases.** Items where the conflict is visible without inference
   (i.e., the passages share contradictory surface keywords) are reclassified as L0
   or revised to require at least one genuine inference step.

**Consistent items:**

Passages are selected or constructed such that a single reconciling sentence can be
written using only information present in both passages. Consistent items are
intentionally not assigned `conflict_level`, `reasoning_chain`, or `explanation`.

**Ambiguous items:**

Passages are constructed such that a conflict exists under one interpretation but
not another, and the passages leave the disambiguating fact unstated. The
`ambiguity_reason` field records the specific gap.

### 4c. Source provenance

| `source_type` | Meaning |
|--------------|---------|
| `real` | Verbatim extract from a real document |
| `paraphrased_real` | Paraphrase of a real source; arguments and claims are historically grounded |
| `composite` | Combines a real statute or document with a synthetic contract or scenario |
| `synthetic` | Fully invented text representing a realistic but fictional document or person |

Per-domain provenance:

| Domain | `source_type` | `source_verifiability` | Notes |
|--------|--------------|----------------------|-------|
| philosophy | `paraphrased_real` | `verifiable` | Named primary sources (Kant, Nietzsche, Sartre, Heidegger, Wittgenstein, Rand, Hume, etc.) |
| software | `synthetic` | `illustrative` | Realistic ADRs, runbooks, event logs, system configs |
| law | `composite` | `verifiable` | Real statutes (NLRA, Sherman Act, GDPR, Cal. Labor Code, etc.) + synthetic contracts |
| science | `paraphrased_real` | `verifiable` | Real theories and empirical papers, cited by author and date |
| content | `synthetic` | `fictional` | Invented creator profiles and social posts |
| teams | `synthetic` | `fictional` | Invented team norms, ADRs, and Slack messages |

---

## 5. Validation

### 5a. Structural validation (automated)

`scripts/validate_dataset.py` enforces the following on every item:

- `conflict_level` is an integer 0–5 for conflict items; `null` for consistent and ambiguous.
- `reasoning_chain` length equals `conflict_level + 1` for conflict items (N numbered steps + one `CONFLICT —` terminal entry).
- No step in a conflict chain contains prohibited modal language: `may`, `might`, `could`, `perhaps`, `arguably`, `likely`.
- The final entry of each conflict chain starts with exactly `CONFLICT — `.
- `explanation` is non-null for all conflict and ambiguous items.
- `conflicting_spans` is non-null for all conflict items.

This validator runs automatically on every push or pull request touching `data/` via
`.github/workflows/validate.yml`. All 180 items pass structural validation.

### 5b. Annotation guide

`docs/annotation_guide.md` provides detailed verdict decision rules, reasoning chain
quality criteria (100%-certainty rule, minimality rule, no passage-restatement steps),
and a structured review workflow covering accept, flag, dispute, and label-change outcomes.

### 5c. Human review queue

`data/review_queue.json` tracks per-item flags requiring human review. Flag types include
`minimality` (chain may be over-specified), `modal_rewrite` (automated fix needs semantic
verification), `contested_premise`, and others.

### 5d. Pending validation work

The following validation work is in progress and will be completed before the
first versioned public release:

| Work item | Status | Priority |
|-----------|--------|----------|
| Minimality audit for all L3–L5 conflict items (33 items) | In progress | High |
| Inter-annotator agreement (κ) on a 30-item stratified sample | Not started | Critical for publication |
| External domain-expert review for law and science items | Not started | High |
| Resolution of 3 easy review flags (2 modal rewrites, 1 contested premise) | In progress | Medium |

Until inter-annotator agreement is established, all 180 items should be treated as
having been reviewed by a single annotator. Claims about label quality should be
qualified accordingly in any downstream publication.

---

## 6. Evaluation Tasks

### Task 1 — Verdict Classification (3-class)

**Input:** Two passages P₁ and P₂.

**Task:** Given P₁ and P₂, classify their relationship as one of:
- `conflict` — logically incompatible under valid reasoning expansion
- `consistent` — compatible under all reasonable readings
- `ambiguous` — incompatible under one interpretation, compatible under another, with the disambiguating fact absent from both passages

**Primary metric:** Level-Weighted F1 (LW-F1), defined as:

```
LW-F1 = Σ_L [ (L+1) × conflict_F1_L ] / Σ_L (L+1)
```

where `conflict_F1_L` is the conflict-class F1 computed on the 18 level-L conflict items
plus all 72 consistent and ambiguous items (90 items per level). The non-conflict items
are included at every level so that precision is penalised — a model cannot score high by
predicting `conflict` for everything.

Weights: L0=1×, L1=2×, L2=3×, L3=4×, L4=5×, L5=6×.

Baseline scores: always-predict-conflict = 0.333; random = 0.111; perfect = 1.000.

**Additional metrics:** accuracy, macro-F1 (penalises class collapse), binary conflict F1
(conflict+ambiguous vs. consistent), per-level conflict F1, per-domain conflict F1.

### Task 2 — Explanation Quality

**Input:** A model explanation for a conflict or ambiguous prediction.

**Reference:** The ground-truth `reasoning_chain` field.

**Metric:** BERTScore F1 (distilbert-base-uncased) of the model explanation against the
reference chain. Computed only for conflict and ambiguous items. Measures whether the
model traces the correct logical path, not just predicts the right label.

**Limitation:** BERTScore sensitivity to reasoning errors has not yet been formally
validated on this dataset. Treat explanation scores as diagnostic, not definitive.

---

## 7. Known Limitations

The following limitations are acknowledged and are targets for future work:

| Limitation | Impact | Planned remedy |
|-----------|--------|---------------|
| **Single annotator** — all 180 labels created by one person | Label quality unverified by independent review; no κ statistic | Inter-annotator agreement pass (κ ≥ 0.70 target) on 30-item stratified sample |
| **L4–L5 underpowered** — 18 conflict items per level gives 95% CI ≈ ±0.33 on F1 | Per-level claims at L4–L5 should be treated with wide uncertainty | Expand to 50+ items per level (Phase 3 roadmap) |
| **Anthropic-only baselines** — leaderboard contains only Claude Haiku and Claude Sonnet | Cannot make cross-provider comparative claims | Add GPT-4o and at least one open-source model (Phase 3 roadmap) |
| **Minimality unverified for L3–L5** — 33 items flagged; some may be over-specified | Claimed difficulty levels may be inflated; LW-F1 scores at high levels may not reflect genuine reasoning depth | Formal minimality audit in progress |
| **Philosophy domain leakage risk** — canonical pairings (Kant/Bentham, Hume/Kant) are widely covered in training data | Models may solve these items via memorisation, not reasoning | Leakage stratification (Phase 5 roadmap) |
| **BERTScore insensitivity** — explanation scores near-constant (0.81–0.82) across models and levels | Explanation metric may not be detecting reasoning errors | Sensitivity ablation planned; metric may be replaced with LLM-judge scoring |
| **No train/test split** — full 180-item set used for all evaluations | Benchmark cannot be used for fine-tuning without contamination risk | Stratified 80/20 split to be locked before public release |

---

## 8. Citation

If you use this dataset, please cite:

```bibtex
@dataset{semantic_conflicts_benchmark_2026,
  title   = {Semantic Conflicts Benchmark},
  year    = {2026},
  note    = {A benchmark for measuring multi-hop semantic conflict detection in LLMs across six domains and five reasoning depths.},
  url     = {https://github.com/your-org/semantic-conflicts-benchmark}
}
```

_DOI and Hugging Face Hub link will be added upon versioned public release._

---

## 9. License

See [LICENSE](LICENSE) for terms of use.
