# Benchmark Development Roadmap

This roadmap sequences improvements from `improvements.md` into prioritized phases.
Each roadmap item references the specific improvement IDs it addresses.

Guiding principle: fix data integrity before annotation quality, annotation quality
before statistical rigor, statistical rigor before metric validity, and metric
validity before leakage controls. A benchmark with wrong labels is worse than a
benchmark with fewer labels.

---

## Phase 1 — Data Integrity (Do Now)
**Goal:** Ensure every item in the dataset means what it claims to mean.
**Prerequisite for:** All other work. Nothing downstream is trustworthy until the
labels are internally consistent.

### R-1.1 · Fix content domain step counts
**Maps to:** I-01
**Effort:** 1–2 weeks (manual audit of 18 items)

Audit each of the 18 content conflict items. For each item, determine whether the
reasoning chain has a genuinely redundant step (remove it, preserve level) or whether
the level is understated (demote level by 1). If levels are demoted, add 3 new
content L5 items to restore the 3×L0–L5 distribution.

Acceptance criterion: `chain length == conflict_level + 1 numbered steps + 1 CONFLICT
line` for every content conflict item, verified by the validator added in R-1.2.

---

### R-1.2 · Build automated dataset validator
**Maps to:** I-03
**Effort:** 2–3 days

Write `scripts/validate_dataset.py` that checks every item in every domain:
- Chain length matches `conflict_level` (exactly N numbered steps + CONFLICT line)
- No step in a conflict chain contains: "may", "might", "could", "perhaps",
  "arguably", "likely", "suggests loosely"
- Final step of conflict chain starts with "CONFLICT —"
- `explanation` is non-null for all conflict and ambiguous items
- `conflicting_spans` is non-null and all objects for conflict items
- `conflict_level` is null for consistent and ambiguous items

Add this script to CI so it runs on every commit to `data/`.

---

### R-1.3 · Fix modal language violations in conflict chains
**Maps to:** I-02
**Effort:** 2–3 days

Rewrite the 6 genuine epistemic hedges identified in conflict-item chains
(philosophy_L4_001, philosophy_L4_003, software_L3_001, software_L4_001,
law_L4_002, law_L5_002). Each step must be rewritten as a logically necessary
consequence. If a step cannot be made certain without distorting the argument,
demote the item to ambiguous or lower its level.

The two borderline cases (teams_L3_001 and teams_L4_001 — modal as permission,
not hedge) should be documented with an inline comment in the chain to clarify
why the language is acceptable.

---

### R-1.5 · Add CI gate and distributional invariant tests
**Maps to:** I-24, I-25
**Effort:** 1–2 days

Two companion steps that make the dataset validator self-enforcing:

1. **CI workflow:** Add `.github/workflows/validate.yml` that runs
   `python scripts/validate_dataset.py --strict` on every push or PR touching
   `data/`. This converts the validator from a manual tool into an enforced gate.

2. **Distributional tests:** Add `tests/test_dataset_distribution.py` asserting:
   - 180 items total, 30 per domain, 30 per level
   - Per-level verdict split: {conflict: 18, consistent: 8, ambiguous: 4}
   - All conflict items have non-null `conflict_level` and `reasoning_chain`

   These tests run in CI alongside the structural validator.

Acceptance criterion: any PR that introduces a chain-length error, wrong class
distribution, or modal violation fails CI before it can be merged.

---

### R-1.4 · Level minimality spot-check for L3–L5
**Maps to:** I-04
**Effort:** 1 week (54 items: 18 per level × levels 3–5)

For each L3–L5 conflict item, answer: "Can a reasoner detect the conflict by
skipping any single step in the chain?" If yes, the chain is over-specified and
the level should be lowered, or the skippable step removed and the level preserved.

Prioritize: L5 (6× weight in LW-F1, most impact), then L4, then L3.

---

## Phase 2 — Annotation Quality
**Goal:** Establish that labels reflect expert consensus, not one person's judgment.
**Prerequisite for:** Any publication claim, any comparison to other benchmarks.

### R-2.1 · Inter-annotator agreement on ambiguous items
**Maps to:** I-05, I-06
**Effort:** 2–3 weeks (finding annotators + reconciliation)

Recruit 1–2 independent annotators with domain expertise (philosophy/law at minimum).
Have them label:
- All 24 ambiguous items (highest boundary-fuzziness risk)
- 30 stratified conflict items (5 per domain, 1 per level)
- All 48 consistent items

Compute Cohen's kappa. Target κ ≥ 0.70 for publication readiness.
Reconcile all disagreements via discussion, not majority vote.

Before running the annotation pass, add an explicit decision rule for the
ambiguous/consistent boundary to `data/schema.md`:

> An item is AMBIGUOUS if and only if the conflict's existence depends on an
> unstated empirical, legal, or interpretive fact that cannot be resolved from the
> passage text alone. An item is CONSISTENT if the passages are compatible under
> any reasonable reading of the words used.

Report κ and disagreement rate in README.

---

### R-2.2 · Contested-premise audit for philosophy and law
**Maps to:** I-07
**Effort:** 3–5 days

Review all philosophy and law conflict items where the reasoning chain's first step
encodes a contested claim (e.g., "there is no pre-given human nature"). For these
items, either:
- Rewrite so the chain follows from what both passages explicitly state, without
  requiring exogenous premises, or
- Add a `premise_note` field to the label documenting the conditional: "conflict
  holds under the following premise: [X]"

This is lower priority than R-2.1 but should be done in the same annotation pass.

---

## Phase 3 — Statistical Rigor
**Goal:** Ensure that reported numbers are reliable and per-level claims are credible.
**Prerequisite for:** Trustworthy leaderboard comparisons.

### R-3.1 · Expand L4–L5 to 50+ conflict items per level
**Maps to:** I-08
**Effort:** 4–6 weeks (write, review, validate ~64 new items)

The current 18 conflict items per level give 95% CI ≈ ±0.33 on conflict-class F1.
Expanding to 50 items per level narrows this to ≈ ±0.14.

Prioritize L4 and L5 (highest weight in LW-F1, currently most noisy). Add 32 items
per level (across 6 domains, ~5–6 new items per domain per level). All new items
must pass the validator from R-1.2 and a minimality check.

Until this is done, add a caveat to the README: "Per-level scores at L4–L5 are
based on 18 items each and should be interpreted with wide uncertainty intervals."

---

### R-3.2 · Multi-run evaluation with temperature reporting
**Maps to:** I-09
**Effort:** 1 week (code) + API cost for reruns

Add temperature and seed parameters to the adapter interface and results JSON.
Run each model 3 times. Report mean ± std in leaderboard. Flag results with std > 0.01
as unstable.

Changes needed:
- `ModelAdapter.predict()` → accept optional `temperature` parameter
- `Evaluator` → store temperature in results JSON
- `reporter.py` → show mean ± std in leaderboard when multiple runs exist
- Re-run haiku and sonnet at least 3 times each; update leaderboard

---

### R-3.3 · Define canonical train/test split
**Maps to:** I-16
**Effort:** 2–3 days

Define a stratified 80/20 split (144 train / 36 test), ensuring each domain,
difficulty level, and verdict class is represented proportionally in both splits.
Lock the test split definition in `data/splits.json`. Run all leaderboard
evaluations on the test split only. Publish the train split for community use.

---

### R-3.4 · Add external model baselines to the leaderboard
**Maps to:** I-21
**Effort:** 1–2 days (API cost + run time)

Run the benchmark on at least two additional models before any external sharing:
- One non-Anthropic frontier model: GPT-4o via `--adapter openai --model gpt-4o`
- One open-source model: Llama-3-70B-Instruct or Mistral-Large via `--adapter hf`

Optionally add a rule-based NLI baseline (DeBERTa-NLI zero-shot) as a lower-bound anchor.

Acceptance criterion: `leaderboard.csv` contains at least four rows (two Claude,
one OpenAI, one open-source) before Phase 3 is considered complete. This is a
prerequisite for any credible cross-provider comparative claim.

**Dependency:** Can run in parallel with R-3.1–R-3.3 once Phase 1 is complete,
since Phase 1 ensures the dataset being evaluated is valid.

---

## Phase 4 — Metric Validity
**Goal:** Ensure the primary metric measures what it claims to measure.
**Prerequisite for:** Any paper claim that "LW-F1 measures multi-hop reasoning depth."

### R-4.1 · Ablate LW-F1 weighting function
**Maps to:** I-10
**Effort:** 1 week

Run all current model results through three alternative weighting functions:
- `weight = L` (zero-indexed linear)
- `weight = (L+1)²` (quadratic)
- `weight = 2^L` (exponential)
- `weight = 1` (unweighted macro-F1, industry baseline)

Compare rankings. If (L+1) produces the same ranking as alternatives, justify it on
simplicity grounds. If rankings differ, provide a principled theoretical argument for
the chosen function or switch to unweighted macro-F1.

Document the ablation results in a `docs/metric_design.md` file.

---

### R-4.2 · Validate or replace BERTScore
**Maps to:** I-11
**Effort:** 1–2 weeks

Test BERTScore sensitivity to reasoning errors:
1. Take 20 correct reasoning chains
2. Deliberately invert one step in each
3. Measure BERTScore against the reference chain
4. If BERTScore does not drop by ≥ 0.05 on average, it is not detecting reasoning errors

If BERTScore fails the sensitivity test:
- Option A: Switch backbone to DeBERTa-large and re-test
- Option B: Replace with a prompted LLM judge (e.g., ask a model to score
  reasoning faithfulness on a 1–5 scale) and report inter-rater agreement
- Option C: Remove explanation scoring from the primary leaderboard entirely;
  treat it as an auxiliary diagnostic only

---

### R-4.3 · Reframe Binary Conflict F1
**Maps to:** I-12
**Effort:** 1 day

Move `binary_conflict_f1` out of the primary leaderboard table. Add a note explaining
it measures "flagging ability" (can the model identify items needing human review?),
not reasoning quality. High binary F1 is expected and does not imply competence on
the 3-way task.

Consider replacing it with `ambiguous_class_f1` as the diagnostic metric, since the
conflict/ambiguous distinction is where current models most visibly struggle.

---

### R-4.4 · Add "always-predict-conflict" baseline as a static leaderboard row
**Maps to:** I-22
**Effort:** 1 hour

Add a fixed header row to `leaderboard.csv` representing the trivial baseline of
always predicting "conflict" (LW-F1 = 0.333, accuracy = 0.600, macro_f1 = 0.333,
binary_conflict_f1 = 0.750). This row should not be appended via `write_leaderboard()`
but maintained as a permanent first row so every leaderboard view has an interpretable
lower bound.

Update `reporter.py` to skip appending this row if it already exists.

---

### R-4.5 · Add failure taxonomy to reports
**Maps to:** I-23
**Effort:** 2–3 days

Extend `reporter.py` and `evaluator.py` to produce a structured failure breakdown:

| Type | Example |
|------|---------|
| `conflict_as_ambiguous` | Conflict item predicted ambiguous |
| `conflict_as_consistent` | Conflict item predicted consistent |
| `consistent_as_conflict` | Consistent item predicted conflict |
| `consistent_as_ambiguous` | Consistent item predicted ambiguous |
| `ambiguous_as_conflict` | Ambiguous item predicted conflict |
| `ambiguous_as_consistent` | Ambiguous item predicted consistent |

Add counts and percentages per type to the Markdown report and results JSON.
Break down the two most common types by conflict level. This surfaces whether
models fail by hallucinating conflicts (over-prediction) or by hedging on real
conflicts (under-prediction) — a diagnostic distinction that raw F1 hides.

---

### R-4.6 · Automated BERTScore regression on chain edits
**Maps to:** I-26
**Effort:** 2–3 days

Extend the quality monitoring pipeline so that reasoning chain edits are
automatically checked for semantic quality regression:

1. Compute a clean per-item BERTScore baseline (reasoning chain vs. `explanation`
   field) once the dataset is fully validated, and store in `data/quality_baseline.json`
2. Add a CI check (or pre-commit hook) that re-runs BERTScore for any item whose
   chain was modified and asserts the score does not drop below `baseline - 0.05`
3. Flag items that regress for human review before merging

This complements the structural validator (R-1.5): the validator catches rule
violations; the BERTScore regression catches semantically degrading rewrites that
are structurally valid.

**Dependency:** Requires R-4.2 (BERTScore sensitivity validation) to confirm the
metric is worth regressing on. If R-4.2 finds BERTScore insensitive, replace the
threshold check with an LLM-judge score instead.

---

## Phase 5 — Leakage Controls
**Goal:** Ensure model scores reflect reasoning, not memorization.
**Prerequisite for:** Rigorous comparison of model families.

### R-5.1 · Add leakage risk metadata to all items
**Maps to:** I-13, I-14
**Effort:** 2–3 days

Add `leakage_risk: high | medium | low` to each item's metadata based on:
- **High:** Canonical pairings widely covered in training data (Kant vs. Bentham,
  H. pylori discovery, Big Bang vs. steady-state)
- **Medium:** Real sources but less canonical (minor philosopher pairings,
  recent scientific controversies)
- **Low:** Synthetic documents (software, teams, content), obscure real sources

Report leaderboard scores stratified by leakage risk. A robust model should score
similarly on high- and low-leakage items.

---

### R-5.2 · Construct low-leakage philosophy variants
**Maps to:** I-13
**Effort:** 3–4 weeks

Replace the 6 highest-leakage philosophy items (canonical Kant/Bentham,
Hobbes/Rousseau conflicts) with:
- Novel pairings of minor philosophers
- Invented philosophical positions with realistic sourcing
- Paraphrases that obscure the canonical framing while preserving the logical structure

Test whether model performance drops on the low-leakage variants vs. the canonical
items. Report the gap as an upper-bound leakage estimate in the README.

---

## Phase 5b — Robustness Testing
**Goal:** Verify that model scores reflect semantic reasoning, not surface pattern matching.
**Can run in parallel with Phase 5.**

### R-5.3 · Add paraphrase and distractor robustness variants
**Maps to:** I-19
**Effort:** 3–4 weeks

For a representative subset of existing items:
- Write paraphrase variants (same logical content, different surface vocabulary) for
  all L0–L1 conflict items (18 items → 18 paraphrase twins)
- Write distractor variants for 20 consistent items (negation traps that look like
  conflicts but are not)

Extend the evaluator and leaderboard to report a robustness ratio:
  `robustness = score_on_paraphrase / score_on_original`

A ratio below 0.9 signals surface pattern matching. Report this in the README
alongside the main LW-F1 score.

---

## Phase 6 — Infrastructure & Reproducibility
**Goal:** Ensure the benchmark can be reliably reproduced and extended.

### R-6.1 · Dataset hash in results JSON
**Maps to:** I-15
**Effort:** 1 day

Compute a SHA-256 hash of the sorted, serialized content of all 180 items at eval
time. Store it in `results.json`. On leaderboard comparison, flag runs using
different dataset versions.

---

### R-6.2 · Results JSON schema versioning
**Maps to:** I-17
**Effort:** 1 day

Add `schema_version: "2.0"` to all results JSON files. Write a migration script for
loading v1.x results. Document schema changes in `CHANGELOG.md`.

---

### R-6.3 · Publish to Hugging Face Hub and get a DOI
**Maps to:** I-18
**Effort:** 2–3 days

Steps:
1. Write a HF dataset card (`data/README.md`) covering: task description, conflict
   taxonomy, split definitions, label schema, citation, and license
2. Push the dataset to `huggingface.co/datasets/<org>/semantic-conflicts-benchmark`
   using `huggingface_hub`
3. Register a DOI via Zenodo (free; link your HF or GitHub repo)
4. Update the GitHub README with HF badge, dataset link, and DOI

Acceptance criterion: `datasets.load_dataset("semantic-conflicts-benchmark")` works
and returns the correct splits and schema.

---

### R-6.4 · Pin dependency versions in a lockfile
**Maps to:** I-20
**Effort:** 1 hour

Add a `requirements-lock.txt` pinned to the exact package versions used to produce
all published leaderboard results. Critical packages to pin: `bert-score`,
`scikit-learn`, `tabulate`, `transformers`, `torch`.

Document in the README which lockfile was active for each dataset version. This
closes the gap between the `dataset_hash` reproducibility guarantee (data unchanged)
and full end-to-end score reproducibility (data + code + dependencies unchanged).

---

### R-6.5 · Add failure taxonomy to reports
**Maps to:** I-23
*(Duplicate of R-4.5 — see Phase 4 for the implementation spec. Listed here to
confirm it also belongs in the infrastructure rollout.)*

Ensure the failure taxonomy output is included in the initial public release
(R-6.3) so that the first external users of the benchmark can see structured
error diagnostics, not just raw scores.

---

### R-6.6 · Canary model probe and model-as-judge quality checks
**Maps to:** I-27
**Effort:** 2–3 days

Two lightweight mechanisms for detecting data quality regressions that slip past
structural validation:

**Canary probe:**
- Run a cheap, stable reference model (e.g., `gpt-4o-mini` at temperature=0) on
  all 180 items once the dataset is clean, and store per-item predictions and
  per-level accuracy in `data/canary_baseline.json`
- After any batch of data edits (>3 items changed), re-run the canary and diff
  against baseline; flag any level with >5% accuracy change for human review
- A jump in accuracy on a level after an edit signals items may have gotten easier
- Keyed by `dataset_hash` so baselines from different data versions are never mixed

**Model-as-judge:**
- Write `scripts/judge_sample.py` that samples 10% of items (18 items), prompts
  a judge model with a structured rubric rating: (1) is the conflict real? (2) is
  the chain logically sound? (3) does the difficulty match the level?
- Run before any major release or after any annotation pass
- Report an aggregate quality score alongside the standard validator output

**Dependency:** Can only establish a meaningful canary baseline after Phase 1 data
fixes are complete and the `dataset_hash` is stable.

---

## Roadmap Summary

| Phase | Roadmap Items | Addresses | Blockers | Status |
|-------|--------------|-----------|----------|--------|
| 1 — Data Integrity | R-1.1, R-1.2, R-1.3, R-1.4, R-1.5 | I-01, I-02, I-03, I-04, I-24, I-25 | None | **Start now** |
| 2 — Annotation Quality | R-2.1, R-2.2 | I-05, I-06, I-07 | Phase 1 complete | After Phase 1 |
| 3 — Statistical Rigor | R-3.1, R-3.2, R-3.3, R-3.4 | I-08, I-09, I-16, I-21 | Phase 2 complete | After Phase 2 |
| 4 — Metric Validity | R-4.1, R-4.2, R-4.3, R-4.4, R-4.5, R-4.6 | I-10, I-11, I-12, I-22, I-23, I-26 | Phase 3 data | After Phase 3 |
| 5 — Leakage Controls | R-5.1, R-5.2 | I-13, I-14 | Phase 4 complete | Long-term |
| 5b — Robustness | R-5.3 | I-19 | Phase 3 data | Parallel with Phase 5 |
| 6 — Infrastructure | R-6.1, R-6.2, R-6.3, R-6.4, R-6.5, R-6.6 | I-15, I-17, I-18, I-20, I-23, I-27 | None | Anytime (low effort) |

**Can be done in parallel with any phase:** R-3.2 (temperature control), R-4.3
(reframe binary F1), R-6.1, R-6.2, R-6.3 — these are low-effort and have no blockers.

---

## Publication Readiness Gates

| Gate | Required items | Not required |
|------|---------------|--------------|
| **Share with external researchers** | R-1.1, R-1.2, R-1.3 | Everything else |
| **Blog post / technical report** | All Phase 1 + R-2.1 + R-3.2 + R-3.4 (external baselines) + R-6.3 (HF Hub) | Phases 4–5 |
| **Workshop paper (ACL/EMNLP)** | All Phase 1–3 + R-4.1 + R-4.2 + R-4.5 (failure taxonomy) | Phase 5–6 |
| **Full conference paper (NeurIPS/EMNLP)** | All Phase 1–5 + IRR κ ≥ 0.70 + R-6.4 (lockfile) | R-6.2 |
