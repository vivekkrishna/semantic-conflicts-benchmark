# Benchmark Improvements Backlog

All issues identified through internal critical validation audit (April 2026).
Each issue is assigned a severity tier and an ID for cross-referencing with the roadmap.

Severity tiers:
- **CRITICAL** — invalidates claims being made; must fix before external sharing
- **HIGH** — serious threat to validity; must fix before publication
- **MEDIUM** — weakens credibility; should fix for long-term reliability
- **LOW** — polish and robustness; address when higher-priority items are done

---

## Data Integrity

### I-01 · Content domain step-count errors
**Severity:** CRITICAL

All 18 conflict items in the content domain have reasoning chains with one extra
inference step relative to their stated `conflict_level`. `content_L1_001` is
labeled L1 but has 2 inference steps. `content_L4_001` is labeled L4 but has 5
steps. The pattern is systematic across the entire domain (+1 step in every item).

Either the level assignments are wrong (items are harder than labeled), or the
reasoning chains include an unnecessary step. Both interpretations invalidate the
claimed difficulty calibration for content items.

**Files affected:** `data/content/v1.json` — all 18 conflict items

**Fix options:**
- Option A: Demote all content conflict levels by 1 (L1→L0, L2→L1, ... L5→L4).
  Requires adding 3 new L5 content items to maintain dataset balance.
- Option B: Trim the first or last extra step from each reasoning chain, preserving
  the level assignments.
- Preferred: Manual audit of each item to determine which option is semantically
  correct for that specific conflict.

---

### I-02 · Modal language in "100% certainty" chains
**Severity:** CRITICAL

The schema and README both explicitly prohibit probabilistic or modal language in
conflict-item reasoning chains: "Every step must follow from the previous with 100%
logical certainty — no probabilistic leaps." Eight conflict items still contain
hedging language that violates this rule:

| Item ID | Level | Offending phrase |
|---------|-------|-----------------|
| `philosophy_L4_001` | L4 | "the mind **could**, in principle, have not formed this habit" |
| `philosophy_L4_003` | L4 | "the organism **could** rationally accept death as the price" |
| `software_L3_001` | L3 | "a consumer that has not yet read a message **may find** it removed" |
| `software_L4_001` | L4 | "both workers **may** be processing the same resource concurrently" |
| `law_L4_002` | L4 | "mechanisms that **might** actually benefit competition" |
| `law_L5_002` | L5 | "which it **may** be forced to do if contributions become unsustainable" |
| `teams_L3_001` | L3 | "No service **may** hold a direct connection" *(modal permission, acceptable)* |
| `teams_L4_001` | L4 | "cached responses '**may** contain verbatim fragments'" *(quoting spec, acceptable)* |

Note: `teams_L3_001` and `teams_L4_001` use "may" as a permission/prohibition
modal in a quoted rule, not as an epistemic hedge — these are borderline.

**Files affected:** `data/philosophy/v1.json`, `data/software/v1.json`,
`data/law/v1.json`

**Fix:** Rewrite each offending step as a logically certain consequence. If the step
cannot be made certain, demote the item to `ambiguous` or lower the conflict level.

---

### I-03 · No automated step-count validator
**Severity:** HIGH

There is no automated check that verifies:
- Chain length matches `conflict_level + 1` numbered steps + 1 CONFLICT line
- No step contains prohibited modal words
- The final step starts with "CONFLICT —"

These checks are listed in the schema's contribution checklist but are not enforced
by any test or validation script. The content domain errors (I-01) slipped through
precisely because this validation is manual-only.

**Files affected:** `tests/`, `benchmark/` (new validation utility needed)

**Fix:** Add a `validate_dataset.py` script and corresponding pytest tests that
enforce schema constraints programmatically on every item in every domain.

---

### I-04 · Level minimality unverified
**Severity:** HIGH

The schema requires that `conflict_level` represents the **minimum** number of
inference steps to detect the conflict — meaning the conflict cannot be found by
skipping any step. No automated or manual verification exists that levels are truly
minimal. Spot-check of `philosophy_L4_001` shows the conflict can be detected in
3 steps rather than 4.

If levels are not minimal, the difficulty calibration is not meaningful — a "Level 4"
item could be detectable by a shallow model, making the LW-F1 metric reward structure
misleading.

**Files affected:** All conflict items in `data/`

**Fix:** For each L3–L5 item, run a human minimality check: "Can the conflict be
detected by skipping any single step?" If yes, either shorten the chain or lower the
level. Prioritize L4–L5 items first.

---

## Annotation Quality

### I-05 · No inter-annotator agreement
**Severity:** CRITICAL

All 180 items were labeled by a single annotator. No inter-rater reliability (IRR)
metric (Cohen's kappa, Fleiss' kappa) has been measured. Without IRR:

- There is no evidence that a second expert would agree with the labels
- The ambiguous/consistent boundary in particular is not validated
- Single-annotator bias (fatigue, interpretation drift) cannot be detected or corrected

Industry standard for published NLP benchmarks is κ ≥ 0.70.

**Fix:** Recruit 1–2 independent annotators to label:
- All 24 ambiguous items (highest boundary-fuzziness risk)
- A stratified random sample of 30 conflict items (5 per domain)
- All 48 consistent items (verify none should be ambiguous)
Compute κ. Reconcile all disagreements. Report κ in the README.

---

### I-06 · Ambiguous/consistent boundary is unvalidated
**Severity:** HIGH

The distinction between `consistent` (no conflict exists) and `ambiguous` (conflict
depends on unstated context) is inherently subjective. Multiple items in the dataset
are defensible as either label under different interpretations.

Example: `philosophy_A_004` (Stoic "live according to nature" vs. Nietzsche "overcome
nature") is labeled ambiguous because the word "nature" may carry different meanings.
But under a charitable reading, both passages are consistent (referring to different
senses of nature by design). Whether this is "ambiguous" or "consistent" requires
an interpretation judgment that a single annotator cannot validate alone.

Without a validated decision rule for this boundary, the ambiguous class is
unreliable — models penalized for predicting "consistent" on an item the annotator
labeled "ambiguous" may in fact be correct.

**Fix:** Write an explicit decision rule for the ambiguous/consistent boundary in
`data/schema.md`. Apply the rule consistently in a two-annotator pass (see I-05).

---

### I-07 · Reasoning chain premises sometimes contested
**Severity:** MEDIUM

Some conflict items build their chains on philosophical premises that are themselves
contested, not universally accepted. If an expert rejects the premise, the entire
conflict does not follow.

Example: `philosophy_L3_003` (Sartre vs. Aristotle) begins from "there is no
pre-given human nature" — Sartre's position. An Aristotelian expert would reject
this premise and therefore reject the conflict. The chain's "100% certainty" claim
only holds conditional on accepting the Sartrean starting point.

This is especially common in philosophy and law domains.

**Fix:** For items where the chain's first step encodes a contested premise, add a
`premise_note` field in the label making the conditional explicit. Or rewrite the
item so the conflict follows from both passages' stated positions without requiring
a contested exogenous premise.

---

## Statistical Rigor

### I-08 · L4–L5 subsets are statistically underpowered
**Severity:** CRITICAL

Each difficulty level has exactly 18 conflict items. The 95% confidence interval on
conflict-class F1 with n=18 is approximately ±0.33 — so a measured score of 0.61
could plausibly be anywhere from 0.28 to 0.94.

Concrete consequence: Sonnet's L4 score (0.611) vs. haiku's L4 score (0.651) differ
by 0.04, which is entirely within noise. The README commentary on level-specific
performance differences is not supported by the data.

Any per-level claim in the leaderboard is unreliable with 18 items.

**Fix:** Expand each level to a minimum of 50 conflict items (currently 18). This
requires ~192 additional items total (32 per level × 6 levels, minus existing 18).
With 50 items per level, the 95% CI narrows to approximately ±0.14, which is
sufficient to support per-level comparisons.

---

### I-09 · Single-run evaluation, no temperature/seed control
**Severity:** HIGH

The evaluator runs each model once with no reported temperature, top-p, or random
seed. Generative model outputs are stochastic — two runs of the same model on the
same prompt may produce different verdicts. The published LW-F1 scores are
point estimates with unknown variance.

At 180 items, per-item stochasticity is not negligible. A single borderline item
flipping could change LW-F1 by ~0.005–0.01.

**Fix:**
- Report temperature used for each run (add to adapter and results JSON)
- Run each model 3–5 times; report mean ± std in leaderboard
- Add `temperature` and `seed` fields to the results JSON schema

---

## Metric Validity

### I-10 · LW-F1 weighting function is arbitrary and unvalidated
**Severity:** HIGH

The primary metric uses weight = (L+1), meaning L5 items count 6× more than L0.
This is justified in the README as "deeper conflicts require genuine multi-hop
reasoning and should count more," but:

- The linear (L+1) function is one of many possible choices (L, L², 2^L, unweighted)
- No ablation shows that (L+1) produces a more meaningful ranking than alternatives
- Under L² weighting, the sonnet–haiku gap narrows; under 2^L it widens
- The metric advantages the levels with the widest confidence intervals (I-08)

**Fix:** Run an ablation study with at least 3 weighting functions and compare
rankings. Either justify (L+1) empirically or switch to unweighted macro-F1 (industry
standard). Document the choice clearly with the ablation results.

---

### I-11 · BERTScore is near-constant and unvalidated for reasoning
**Severity:** HIGH

Explanation BERTScore-F1 across all current models and levels is approximately
0.81–0.82 — a range of only 0.009 between haiku and sonnet. This suggests the
metric is not sensitive to reasoning quality.

Root cause: BERTScore (distilbert-base-uncased) measures semantic similarity
(paraphrase overlap) between prediction and reference. It does not validate logical
structure. A model that writes plausible-sounding but logically inverted reasoning
chains would score nearly identically to a model with correct chains.

No ablation exists showing that BERTScore F1 correlates with conflict-label
correctness or reasoning chain validity.

**Fix:**
- Construct a deliberate test: take correct reasoning chains, invert one step,
  measure BERTScore — if it does not drop, the metric is not useful for reasoning
- If BERTScore proves insensitive, replace with a more appropriate metric or remove
  explanation scoring from the primary leaderboard
- Alternatively, use a stronger model (e.g., DeBERTa-large) as the BERTScore
  backbone and re-evaluate sensitivity

---

### I-12 · Binary Conflict F1 masks the conflict/ambiguous distinction
**Severity:** MEDIUM

The `binary_conflict_f1` metric collapses conflict and ambiguous into a single
positive class against consistent. Both current models score ~0.94 on this metric.
This high score masks the fact that models struggle significantly to distinguish
conflict from ambiguous — sonnet's ambiguous-class F1 is only 0.43 (README).

A model that always predicts "conflict" for anything non-consistent would score
~0.94 on binary F1 while completely failing at the 3-class task. The metric creates
a false impression of model capability.

**Fix:** Either remove binary F1 from the primary leaderboard view, or reframe it
explicitly as a "flagging" metric (not a quality metric) with a clear caveat that
high binary F1 does not imply good conflict/ambiguous discrimination.

---

## Leakage & Contamination

### I-13 · Philosophy domain has uncontrolled training data leakage
**Severity:** HIGH

The philosophy domain uses canonical historical philosopher pairings (Kant vs.
Bentham, Hobbes vs. Rousseau, Hume vs. Kant, Nietzsche vs. Schopenhauer) that are
extensively discussed in LLM training corpora. A model encountering "Kant: murder is
always wrong" and "Bentham: aggregate welfare is the moral standard" may correctly
classify the conflict from memorized knowledge rather than from reasoning over the
passage text.

This makes philosophy scores unreliable as a measure of reasoning ability. The domain
gap (sonnet: philosophy 0.76 vs. law 0.59) may partly reflect memorization advantage,
not reasoning depth advantage.

**Fix:**
- Construct a "low-leakage" philosophy variant using novel or obscure pairings
  (minor philosophers, non-canonical positions, invented philosophical positions with
  realistic-sounding names and sourcing)
- Test model performance on canonical vs. low-leakage variants; report the gap as a
  leakage estimate
- In the near term: add a `leakage_risk` field (high/medium/low) to each item's
  metadata

---

### I-14 · Science domain has moderate leakage on landmark paradigm shifts
**Severity:** MEDIUM

The science domain includes well-known paradigm shift conflicts (H. pylori vs. acid
theory, Big Bang vs. steady-state, Lamarck vs. Mendel/Crick). These are covered
extensively in popular science writing and are likely in training data. Less canonical
conflicts (TOFT vs. SMT in cancer biology, quantum decoherence) have lower leakage risk.

**Fix:** Tag each science item with estimated leakage risk. Consider replacing the
highest-risk items (H. pylori, Big Bang) with more recent or obscure conflicts where
training data coverage is lower.

---

## Reproducibility & Infrastructure

### I-15 · No dataset version pinning in evaluation
**Severity:** MEDIUM

The evaluator loads `data/<domain>/v1.json` at runtime. If the dataset files change
(as happened multiple times during development), historical run results become
non-comparable — the same run ID cannot be reproduced.

**Fix:** Add a dataset hash to each results JSON. Compute a deterministic hash of
all 180 items at eval time and store it in `results.json` alongside the run ID.
Flag mismatches when loading historical results for comparison.

---

### I-16 · No standardized test split
**Severity:** MEDIUM

The entire dataset is used for evaluation. There is no held-out test split, no
dev split, and no standard split definition. This means:
- Researchers who build on this benchmark can inadvertently overfit to the full set
- There is no "challenge set" that is kept private to prevent gaming

**Fix:** Define a canonical 80/20 split (144 train / 36 test) or a 3-way split
(train/dev/test). Lock the test split and do not publish its labels publicly.
Run leaderboard evaluations only on the test split.

---

### I-17 · Results JSON schema not version-controlled
**Severity:** LOW

The results JSON structure has changed multiple times during development (ROUGE-L
removed, BERTScore added, field renames). Historical runs use different schemas,
making automated comparison fragile.

**Fix:** Add a `schema_version` field to results JSON. Define a changelog for
schema versions. Add a migration script for loading older results.

---

### I-18 · No Hugging Face dataset card or hosted dataset
**Severity:** HIGH

The dataset is not published on Hugging Face Hub. This is the primary discovery and
citation channel for NLP benchmarks. Without it:
- Researchers cannot `load_dataset("...")` it programmatically
- It will not appear in benchmark discovery searches
- Papers citing it must point to a GitHub repo, which is not citable via DOI

Compare: ConflictBank, MMKC-Bench, TruthfulQA — all have HF Hub presence.

**Files affected:** New: `data/hf_dataset_card.md`, HF Hub repository

**Fix:**
- Write a `README.md` for the HF dataset card (task description, format, splits,
  citation, licensing)
- Push `data/` to a Hugging Face dataset repository using `huggingface_hub`
- Add a DOI via Zenodo (free, permanent, citable)
- Link the HF dataset from the GitHub README

---

### I-19 · No adversarial or paraphrase robustness examples
**Severity:** MEDIUM

All 180 items are clean, well-formed passages. The dataset does not test whether
models degrade under:
- Paraphrase perturbations (same logical content, different surface form)
- Distractors (an additional passage that is irrelevant or misleading)
- Negation traps (a passage that superficially looks like a conflict but is not)

Without these, a model that does surface pattern matching on distinctive keywords
cannot be distinguished from a model doing genuine semantic reasoning.

**Files affected:** New items in `data/` under a `robustness/` subdataset or
as additional metadata fields on existing items

**Fix:**
- For each L0–L1 conflict item, write one paraphrase variant that preserves the
  logical structure but changes the surface vocabulary
- For 20 consistent items, write a "distractor" version where one passage contains
  a negation that looks like a conflict but isn't (e.g., "not X is wrong" ≠ "X is right")
- Report model performance on original vs. paraphrase vs. distractor variants
  as a robustness score in the leaderboard

---

### I-20 · No pinned dependency lockfile
**Severity:** LOW

There is no `requirements.txt`, `uv.lock`, or equivalent pinned lockfile. Package
versions for `scikit-learn`, `bert-score`, `tabulate`, and others can drift silently
across environments. A future `pip install` could produce different BERTScore or
F1 values without any indication that something changed.

This undermines the reproducibility guarantee that the `dataset_hash` and
`run_id` fields are intended to provide — the hash confirms the data was unchanged
but says nothing about whether the metrics were computed identically.

**Files affected:** `pyproject.toml`, new lockfile

**Fix:** Add a `requirements-lock.txt` (or `uv.lock`) pinned to exact versions
used in all published runs. Document in the README which lockfile was used to
produce the leaderboard results.

---

## Baselines & Comparisons

### I-21 · No external model baselines on the leaderboard
**Severity:** HIGH

The leaderboard currently contains only two Claude models from the same provider
(Anthropic). This means:
- There is no cross-provider comparison, so readers cannot judge where the
  benchmark sits in the broader model landscape
- It is impossible to tell whether a score of 0.73 LW-F1 is "good" without a
  reference point from GPT-4o, Llama, Mistral, or Gemini
- A single-provider leaderboard raises the appearance (if not the reality) of
  a benchmark optimised for one model family

Without at least one open-source model and one non-Anthropic frontier model,
the leaderboard does not support comparative claims.

**Fix:**
- Run the benchmark on at least: GPT-4o (OpenAI), one open-source model
  (e.g., Llama-3-70B or Mistral-Large via the HF adapter)
- Add these as rows in `results/leaderboard.csv` before any external sharing
- The "always-predict-conflict" floor (LW-F1 = 0.333) and a rule-based
  NLI baseline (e.g., DeBERTa-NLI) would also anchor the lower end of the scale

---

### I-22 · "Always-predict-conflict" baseline not a leaderboard row
**Severity:** LOW

The README correctly documents that a model always predicting "conflict" scores
LW-F1 ≈ 0.333. However, this floor is only described in prose — it is not an
actual row in `results/leaderboard.csv`. A reader comparing model scores has no
anchor point without mentally computing it.

**Fix:** Add a static "baseline_always_conflict" row to `leaderboard.csv` with
pre-computed scores (LW-F1 = 0.333, accuracy = 0.600, macro_f1 = 0.333,
binary_conflict_f1 = 0.750). Add it as a fixed header row, not an appended run,
so it always appears at the top of the leaderboard.

---

## Interpretability

### I-23 · No failure taxonomy in reports
**Severity:** LOW

The Markdown reports generated by `reporter.py` show the first 5 incorrect items
verbatim but do not quantify failure categories. Patterns visible in current results
(e.g., "conflict predicted as ambiguous at L4+", "consistent predicted as ambiguous")
are evident from the data but are not surfaced as structured counts.

Without a failure taxonomy, it is impossible to say whether different models fail
in the same way or different ways — which is precisely the insight that distinguishes
a diagnostic benchmark from an accuracy leaderboard.

**Files affected:** `benchmark/reporter.py`, `benchmark/evaluator.py`

**Fix:** Add a `failure_breakdown` section to the Markdown report and results JSON
that counts failures by type:
- `conflict_as_ambiguous` — conflict item predicted ambiguous
- `conflict_as_consistent` — conflict item predicted consistent
- `consistent_as_conflict` — consistent item predicted conflict
- `consistent_as_ambiguous` — consistent item predicted ambiguous
- `ambiguous_as_conflict` — ambiguous item predicted conflict
- `ambiguous_as_consistent` — ambiguous item predicted consistent

Report counts and percentages per failure type, and break down by level for
the two most common types.

---

## Automated Data Quality Monitoring

### I-24 · No CI gate for dataset validator
**Severity:** HIGH

`scripts/validate_dataset.py` exists and catches structural violations, but it is
never run automatically. A contributor can introduce a chain-length error, wrong
AMBIGUOUS prefix, or modal-language violation by editing a JSON file — and nothing
will catch it until someone manually re-runs the validator. The content domain's
18-item step-count error (I-01) went undetected precisely because this check was
manual-only.

R-1.2 mentions CI in passing ("Add this script to CI"), but there is no GitHub
Actions workflow, pre-commit hook, or equivalent gate that actually runs it.

**Files affected:** `.github/workflows/` (new), or `.pre-commit-config.yaml`

**Fix:** Add a CI workflow (e.g., `.github/workflows/validate.yml`) that runs
`python scripts/validate_dataset.py --strict` on every push and pull request that
touches `data/`. Exit code 1 on any violation blocks the merge.

---

### I-25 · No distributional invariant tests
**Severity:** MEDIUM

The dataset has several structural invariants that must remain stable across edits:
- 30 items per domain (6 domains × 30 = 180 total)
- 30 items per difficulty level (L0–L5)
- Fixed class distribution per level (18 conflict / 8 consistent / 4 ambiguous)

No automated test verifies these properties. A data edit that accidentally changes
the class balance — e.g., demoting a conflict item to consistent without adding a
replacement — will silently corrupt the dataset's distributional integrity. The
`dataset_hash` detects that something changed but not whether the distribution is
still valid.

**Files affected:** `tests/test_dataset_distribution.py` (new)

**Fix:** Add a pytest test file that loads all 180 items and asserts:
- Total count == 180
- Per-domain count == 30
- Per-level count == 30
- Per-level verdict split == {conflict: 18, consistent: 8, ambiguous: 4}
- All conflict items have non-null `conflict_level` and `reasoning_chain`
- All consistent/ambiguous items have null `conflict_level`

Run in CI alongside the structural validator (I-24).

---

### I-26 · No automated BERTScore regression on chain edits
**Severity:** MEDIUM

`R-4.2` proposes a one-time sensitivity test to validate whether BERTScore detects
reasoning errors. But there is no ongoing regression test that flags when a chain
edit degrades semantic quality. When a reasoning chain is rewritten to fix a modal
violation (as in I-02), the rewrite could technically pass structural validation
while degrading the logical content of the chain — and nothing catches this.

The `dataset_hash` changes whenever any chain is edited, but the hash does not
indicate whether the change improved or degraded quality.

**Files affected:** `tests/` or `scripts/` (new regression harness)

**Fix:** After computing a clean baseline BERTScore for each item's reasoning chain
against its `explanation` field, store per-item scores in `data/quality_baseline.json`.
On any chain edit, run BERTScore for the modified items and assert the score does
not drop below `baseline - 0.05`. Integrate into CI or as a pre-commit check that
runs only when `data/` files change.

---

### I-27 · No canary model or model-as-judge probing for data quality
**Severity:** MEDIUM

There is no mechanism to detect when a data edit unintentionally changes item
difficulty. For example, simplifying a reasoning chain to fix a modal violation
(I-02) could inadvertently reduce the item from L3 to L2 difficulty — detectable
only by re-running a model and noticing a performance jump on that level.

Two complementary techniques exist for this:

**Canary model probe:** Run a cheap, stable reference model (e.g., `gpt-4o-mini`
at temperature=0) on the full dataset after any batch of edits. Track per-level
accuracy against a stored baseline. A sudden improvement on a domain or level after
a data edit is a red flag — the items may have gotten easier, not the model better.
The `dataset_hash` already provides the key to correlate metric changes with exact
data states.

**Model-as-judge:** Prompt a strong judge model (Claude Opus, GPT-4o) with a rubric
to rate a random sample of items on: (1) is the conflict real and unambiguous?
(2) is the reasoning chain logically sound? (3) does the difficulty level match the
chain complexity? Run on any revision touching >5 items. Cheaper than human review;
catches regressions between annotation audit cycles.

**Files affected:** `scripts/canary_probe.py` (new), `data/canary_baseline.json` (new)

**Fix:**
- Store a canary baseline: run the reference model once on all 180 items, store
  per-item predictions and per-level accuracy in `data/canary_baseline.json`
- After any batch of data edits, re-run and diff against baseline; flag any level
  with >5% accuracy change for human review
- For model-as-judge: write a `scripts/judge_sample.py` that samples 10% of items,
  prompts a judge model with a structured rubric, and reports a quality score

---

## Summary Table

| ID | Title | Severity | Effort |
|----|-------|----------|--------|
| I-01 | Content domain step-count errors | CRITICAL | Medium |
| I-02 | Modal language in "certain" chains | CRITICAL | Low |
| I-03 | No automated step-count validator | HIGH | Low |
| I-04 | Level minimality unverified | HIGH | High |
| I-05 | No inter-annotator agreement | CRITICAL | High |
| I-06 | Ambiguous/consistent boundary unvalidated | HIGH | Medium |
| I-07 | Contested premises in chains | MEDIUM | Medium |
| I-08 | L4–L5 statistically underpowered | CRITICAL | High |
| I-09 | Single-run, no temperature control | HIGH | Low |
| I-10 | LW-F1 weighting unprincipled | HIGH | Medium |
| I-11 | BERTScore insensitive to reasoning | HIGH | Medium |
| I-12 | Binary F1 masks conflict/ambiguous | MEDIUM | Low |
| I-13 | Philosophy domain leakage | HIGH | High |
| I-14 | Science domain leakage (partial) | MEDIUM | Medium |
| I-15 | No dataset hash in results | MEDIUM | Low |
| I-16 | No standardized test split | MEDIUM | Medium |
| I-17 | Results JSON schema not versioned | LOW | Low |
| I-18 | No Hugging Face dataset card or hosted dataset | HIGH | Medium |
| I-19 | No adversarial / paraphrase robustness examples | MEDIUM | High |
| I-20 | No pinned dependency lockfile | LOW | Low |
| I-21 | No external model baselines on leaderboard | HIGH | Medium |
| I-22 | "Always-predict-conflict" baseline not a leaderboard row | LOW | Low |
| I-23 | No failure taxonomy in reports | LOW | Low |
| I-24 | No CI gate for dataset validator | HIGH | Low |
| I-25 | No distributional invariant tests | MEDIUM | Low |
| I-26 | No automated BERTScore regression on chain edits | MEDIUM | Medium |
| I-27 | No canary model or model-as-judge probing | MEDIUM | Medium |
