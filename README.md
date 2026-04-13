# Semantic Conflicts Benchmark

A benchmark for measuring the ability of large language models to detect **semantic conflicts** across domains — including implicit conflicts that require multi-hop logical reasoning to uncover.

Modelled after TruthfulQA and FEVER. Plug in any model in one Python class.

---

## Leaderboard

180 items · 6 domains · difficulty levels L0–L5 · evaluated April 2026

### Overall scores

| Model | LW-F1 ↑ | Accuracy | Macro-F1 | Bin-Conflict-F1 | Expl ROUGE-L |
|-------|--------:|--------:|---------:|----------------:|-------------:|
| **Optimal** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| claude-haiku-4-5 | 0.6783 | 0.8056 | 0.6893 | 0.9531 | 0.2307 |

**Metric definitions**

| Metric | Formula | Why chosen | What it diagnoses |
|--------|---------|-----------|-------------------|
| **LW-F1** _(primary)_ | `Σ((L+1) × conflict_F1_L) / Σ(L+1)` where `conflict_F1_L` is the conflict-class F1 computed on 18 level-L conflict items **+ all 72 consistent/ambiguous items**; weights L0=1× … L5=6× | Deeper conflicts require genuine multi-hop reasoning and should count more than surface pattern-matching. Including non-conflict items forces precision to be measured alongside recall, so a model can't score high by predicting "conflict" for everything. | Whether the model actually reasons at depth. Flat scores across levels = single-class predictor. Perfect model = 1.000; always-predict-conflict baseline = 0.333. |
| **Accuracy** | `correct / N` across all 180 items | Interpretable to non-specialists; shows overall verdict quality at a glance. | Gross correctness. Can be gamed by a model that memorises the 60 % conflict base rate, so must be read alongside Macro-F1. |
| **Macro-F1** | `(F1_conflict + F1_consistent + F1_ambiguous) / 3` where each `F1_c = 2PR/(P+R)`, `P = TP/(TP+FP)`, `R = TP/(TP+FN)` | Unweighted average penalises models that collapse predictions to one class. A model that always says "conflict" scores 0.333 regardless of accuracy, exposing the single-class failure mode. | Class balance. Low Macro-F1 with high Accuracy = the model ignores consistent or ambiguous labels entirely. |
| **Bin-Conflict-F1** | Binary F1 with positive = `{conflict, ambiguous}`, negative = `{consistent}`; `F1 = 2PR/(P+R)` | Measures the practically important ability to flag items that need human review (anything not clearly consistent) without requiring the model to distinguish conflict from ambiguous. | Over- vs. under-flagging. High Bin-F1 + low Macro-F1 = model detects risk but can't distinguish ambiguous from outright conflict. |
| **Expl ROUGE-L** | `ROUGE-L F1` of model explanation vs. ground-truth `reasoning_chain`, averaged over conflict and ambiguous items only | Checks whether the model traces the correct logical path, not just gets the label right. ROUGE-L captures longest common subsequence overlap, rewarding step order as well as vocabulary. | Explanation faithfulness. A model can predict "conflict" for the wrong reason; low ROUGE-L exposes this. Not computed for consistent items (no reference chain). |

### By difficulty level — claude-haiku-4-5

_Each level's N = 18 conflict items at that depth + 72 consistent/ambiguous items (90 total). This measures whether the model can identify level-L conflicts **without** over-predicting on non-conflict items._

| Level | Name | Accuracy _(opt: 1.0)_ | Macro-F1 _(opt: 1.0)_ | Conflict-F1 _(opt: 1.0)_ | ROUGE-L _(opt: 1.0)_ | N |
|-------|------|---------------------:|---------------------:|-------------------------:|---------------------:|--:|
| L0 | Surface | 0.7778 | 0.6929 | 0.7391 | 0.2058 | 90 |
| L1 | Immediate | 0.7556 | 0.6642 | 0.6818 | 0.2288 | 90 |
| L2 | Two-hop | 0.7667 | 0.6779 | 0.7111 | 0.2351 | 90 |
| L3 | Three-hop | 0.7667 | 0.6779 | 0.7111 | 0.2152 | 90 |
| L4 | Four-hop | 0.7444 | 0.6510 | 0.6512 | 0.2275 | 90 |
| L5 | Deep | 0.7444 | 0.6510 | 0.6512 | 0.2170 | 90 |

> Conflict-F1 declines from 0.739 at L0 (surface contradictions) to 0.651 at L4–L5 (four/five-hop chains), confirming that haiku does degrade on deeper reasoning. The remaining 35 errors are genuine misclassifications, not parser artifacts — earlier scores were corrupted by a bug where "CONFLICT" appearing in an explanation body was picked up instead of the first-line verdict.

### By domain — claude-haiku-4-5

| Domain | Accuracy _(opt: 1.0)_ | Macro-F1 _(opt: 1.0)_ | Conflict-F1 _(opt: 1.0)_ | ROUGE-L _(opt: 1.0)_ | N |
|--------|---------------------:|---------------------:|-------------------------:|---------------------:|--:|
| philosophy | 0.8000 | 0.6827 | 0.8649 | 0.2143 | 30 |
| software | 0.8000 | 0.5926 | 0.8889 | 0.2517 | 30 |
| law | 0.6000 | 0.5480 | 0.6667 | 0.2315 | 30 |
| science | 0.8000 | 0.6814 | 0.8824 | 0.2394 | 30 |
| content | 0.9333 | 0.8875 | 0.9714 | — | 30 |
| teams | 0.9000 | 0.7744 | 0.9231 | — | 30 |

---

## Quickstart

```bash
git clone https://github.com/your-org/semantic-conflicts-benchmark
cd semantic-conflicts-benchmark
pip install -e ".[anthropic]"

ANTHROPIC_API_KEY=sk-... scbench \
  --adapter anthropic \
  --model claude-haiku-4-5-20251001 \
  --verbose
```

Results are written to `results/` as JSON, Markdown, and a cumulative `leaderboard.csv`.

---

## Custom Model (30 seconds)

Implement one class and run:

```python
# my_model.py
from benchmark.adapters.base import AdapterResponse, ModelAdapter

class MyAdapter(ModelAdapter):
    @property
    def name(self) -> str:
        return "my-model-v1"

    def predict(self, prompt: str) -> AdapterResponse:
        raw = my_model_inference(self.system_prompt, prompt)
        verdict = "conflict" if "CONFLICT" in raw.upper() else \
                  "ambiguous" if "AMBIGUOUS" in raw.upper() else "consistent"
        return AdapterResponse(verdict=verdict, explanation=raw, raw_response=raw)
```

```bash
scbench --adapter-class my_model.MyAdapter
```

See [examples/custom_adapter.py](examples/custom_adapter.py) for a full Ollama example.

---

## Built-in Adapters

| Flag | Model argument | Install extra |
|------|---------------|---------------|
| `--adapter openai` | `--model gpt-4o` | `pip install -e ".[openai]"` |
| `--adapter anthropic` | `--model claude-sonnet-4-6` | `pip install -e ".[anthropic]"` |
| `--adapter hf` | `--model mistralai/Mistral-7B-Instruct-v0.2` | `pip install -e ".[hf]"` |

---

## CLI Reference

```
scbench [options]

  --adapter {openai,anthropic,hf}   Built-in adapter to use
  --adapter-class MODULE.CLASS      Custom adapter class (overrides --adapter)
  --model MODEL                     Model name/ID passed to the adapter
  --domains D1 D2 ...               Subset of domains to evaluate (default: all six)
  --data-dir PATH                   Path to data directory (default: data/)
  --output PATH                     JSON output path (default: results/<run_id>.json)
  --leaderboard PATH                CSV leaderboard path (default: results/leaderboard.csv)
  --verbose                         Print per-item predictions during evaluation
```

---

## Difficulty Levels

Every conflict item is tagged with a `conflict_level` (0–5) representing the **minimum number of logically certain inference steps** required to detect the conflict. Each step must follow from the previous with 100% certainty — no probabilistic leaps allowed.

| Level | Name | Description | Expected model behaviour |
|-------|------|-------------|--------------------------|
| 0 | Surface | Contradiction is explicitly stated | All LLMs detect |
| 1 | Immediate | One certain inference collides with the other passage | Strong base models |
| 2 | Two-hop | Two chained inferences expose the conflict | GPT-4 class usually |
| 3 | Three-hop | Three chained inferences | Frontier models sometimes miss |
| 4 | Four-hop | Four chained inferences | Most models fail |
| 5 | Deep | Five chained inferences | Near-universal failure zone |

### Level-Weighted F1 (LW-F1) — primary score

```
LW-F1 = Σ ((level + 1) × conflict_F1_at_level) / Σ (level + 1)
```

where `conflict_F1_at_level` is the conflict-class F1 computed on the **level-L conflict items plus all consistent/ambiguous items** (90 items per level). Including non-conflict items at every level means precision is penalised — a model that blindly labels everything "conflict" gets low precision and therefore low F1.

Weights: L0=1, L1=2, L2=3, L3=4, L4=5, L5=6. A model that only detects surface conflicts scores ~0.048; a perfect model scores 1.0; a naive always-predict-conflict baseline scores 0.333. This prevents high-accuracy models from hiding shallow reasoning.

---

## Domains

| Domain | Conflict type | Example |
|--------|--------------|---------|
| **philosophy** | Conceptual/ideological conflicts between philosophical positions | Kant's categorical imperative vs Utilitarian calculus |
| **software** | State and contract conflicts in distributed systems | UserService says ACTIVE; BillingService says SUSPENDED |
| **law** | Conflicts between statutes, contracts, and evidence | NLRA's collective bargaining right vs employment contract waiver |
| **science** | Temporal conflicts between hypothesis and incoming evidence | Pre-1984 ulcer theory vs H. pylori discovery |
| **content** | Self-contradictions in an influencer's published statements | "I never take supplements" vs daily whey shake promotion |
| **teams** | Conflicts between team norms and a new joiner's stated principles | Async-only team vs AI agent that requires daily standups |

Each domain contains **30 items**: 18 conflict (3 × L0–L5), 8 consistent, 4 ambiguous.

---

## Tasks and Metrics

### Task 1: Verdict Classification (3-class)

The model reads two passages and classifies the relationship as:

- **conflict** — the passages are logically incompatible (directly or through inference)
- **consistent** — the passages are compatible; no logical contradiction exists
- **ambiguous** — whether a conflict exists depends on information not provided

**Metrics**: accuracy, macro-F1, binary conflict F1 (conflict+ambiguous vs. consistent), per-class F1, **LW-F1** (primary).

### Task 2: Explanation Quality

For conflict and ambiguous predictions, the model's explanation is scored against the ground-truth `reasoning_chain` using **ROUGE-L F1**. This measures whether the model traces the correct logical path, not just gets the label right.

---

## System Prompt Strategy

The built-in `system_prompt` (in `benchmark/adapters/base.py`) instructs models to:

1. **Derive implications**: for each passage, enumerate every statement that follows with 100% logical certainty.
2. **Check for conflicts**: look for contradictions both between literal statements *and* between their derived implications.
3. **Classify**: return exactly `CONFLICT`, `CONSISTENT`, or `AMBIGUOUS` on the first line.

This forces models to work in the *derived semantic space*, not just pattern-match surface text — which is precisely what L2–L5 items require.

---

## Dataset Format

See [data/schema.md](data/schema.md) for the full schema and contribution guide.

Quick example — a level-3 conflict item:

```json
{
  "id": "philosophy_L3_001",
  "domain": "philosophy",
  "conflict_level": 3,
  "difficulty": "hard",
  "input": {
    "passages": [
      { "id": "A", "text": "Rational self-interest is the objective moral standard...", "source": "Ayn Rand" },
      { "id": "B", "text": "Moral values are human constructions...", "source": "Nietzsche" }
    ],
    "question": "Do these passages present a conflict, are they consistent, or is the relationship ambiguous?"
  },
  "label": {
    "verdict": "conflict",
    "conflict_level": 3,
    "reasoning_chain": [
      "Step 1 — From A: 'objective moral standard' entails universal correctness...",
      "Step 2 — Universal correctness entails some values are correct independently of construction...",
      "Step 3 — This entails NOT all values are human constructions...",
      "CONFLICT — Step 3 contradicts B ('moral values are human constructions')."
    ]
  }
}
```

---

## Output Files

After a run, `results/` contains:

| File | Contents |
|------|----------|
| `<run_id>.json` | Full results: overall scores, per-level, per-domain, per-item predictions |
| `<run_id>.md` | Human-readable Markdown report with tables and failure examples |
| `leaderboard.csv` | One row per run, appended — suitable for version-controlled tracking |

---

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## Leaderboard Columns

`model, run_id, n_items, lw_f1, accuracy, macro_f1, binary_conflict_f1, explanation_rouge_l, level_0_f1, level_1_f1, level_2_f1, level_3_f1, level_4_f1, level_5_f1, philosophy_f1, software_f1, law_f1, science_f1, content_f1, teams_f1`

---

## Contributing

1. Read [data/schema.md](data/schema.md) for item format and quality rules.
2. Add items to the appropriate `data/<domain>/v1.json` file (one JSON per line).
3. Run `python -m pytest tests/ -v` to verify everything loads and scores correctly.
4. Open a pull request with a brief description of the items added.

Items at L4–L5 that follow the 100%-certainty step rule are especially welcome.
