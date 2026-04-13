# Dataset Schema

Every item in `data/<domain>/v1.json` is an element of a JSON array. Each file contains all 30 items for that domain as a pretty-printed JSON array for easy reading and contribution.

---

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique item identifier, e.g. `philosophy_L3_001`, `teams_C_002` |
| `domain` | string | One of: `philosophy`, `software`, `law`, `science`, `content`, `teams` |
| `category` | string | Structural category (see below) |
| `conflict_level` | int \| null | Reasoning depth 0–5 for conflict items; `null` for consistent/ambiguous |
| `difficulty` | string | `easy` (L0–L1), `medium` (L2–L3), `hard` (L4–L5); `n/a` for consistent |
| `input` | object | The two passages and the question posed to the model |
| `label` | object | Ground-truth annotation (see below) |
| `metadata` | object | Provenance information |

---

## `input` Object

```json
{
  "passages": [
    { "id": "A", "text": "...", "source": "..." },
    { "id": "B", "text": "...", "source": "..." }
  ],
  "question": "Do these passages present a conflict, are they consistent, or is the relationship ambiguous?"
}
```

---

## `label` Object

### Conflict item

```json
{
  "verdict": "conflict",
  "conflict_level": 3,
  "reasoning_chain": [
    "Step 1 — From A: ...",
    "Step 2 — From Step 1: ...",
    "Step 3 — ...",
    "CONFLICT — ..."
  ],
  "explanation": "Prose summary of why the conflict is non-obvious and what makes it semantically significant.",
  "conflicting_spans": [
    { "passage_id": "A", "span": "exact or near-verbatim span from passage A" },
    { "passage_id": "B", "span": "exact or near-verbatim span from passage B" }
  ],
  "ambiguity_reason": null
}
```

### Consistent item

```json
{
  "verdict": "consistent",
  "conflict_level": null,
  "reasoning_chain": null,
  "explanation": null,
  "conflicting_spans": null,
  "ambiguity_reason": null
}
```

### Ambiguous item

```json
{
  "verdict": "ambiguous",
  "conflict_level": null,
  "reasoning_chain": [
    "Step 1 — ...",
    "Step 2 — ...",
    "AMBIGUOUS — ..."
  ],
  "explanation": null,
  "conflicting_spans": null,
  "ambiguity_reason": "Plain-language explanation of why the relationship is underdetermined."
}
```

---

## Field Rules

### `conflict_level`
- Integer 0–5 for conflict items, representing the minimum number of 100%-certain inference steps required to detect the conflict.
- `null` for consistent and ambiguous items.

### `explanation`
- Required for conflict and ambiguous items; `null` for consistent items (there is no conflict to explain).
- Prose description that (a) describes the surface appearance that makes the conflict non-obvious, (b) identifies what derivation is required, and (c) articulates the core conflict in plain language.
- Consistent items intentionally have no explanation field populated — this is by design, not missing data.

### `conflicting_spans`
- Required for conflict items; `null` for consistent and ambiguous.
- An array of objects: `[{"passage_id": "A", "span": "..."}, {"passage_id": "B", "span": "..."}]`.
- `passage_id` must be `"A"` or `"B"`. Spans should be exact or near-verbatim extracts from the passage text.
- Multiple spans per passage are permitted for high-level items where the conflict involves multiple textual anchors.

### `reasoning_chain`
- Required for conflict and ambiguous items; `null` for consistent.
- Each entry is a string. Conflict chains end with `"CONFLICT — ..."`. Ambiguous chains end with `"AMBIGUOUS — ..."`.
- Every step must follow from the previous with **100% logical certainty** — no probabilistic leaps.
- Words like "may", "might", "arguably", or "likely" are **not permitted** in conflict item chains — only in ambiguous item chains where the underdetermination is the point.

### `category`
| Value | Meaning |
|-------|---------|
| `cross_document` | Conflict arises between two separate documents |
| `temporal` | One passage reflects an earlier state; the other a later state |
| `intra_document` | A single creator/entity contradicts itself across time |
| `normative` | Conflict between a stated rule/norm and a described practice |
| `state_divergence` | Two systems or agents hold incompatible beliefs about shared state |

### `difficulty`
| Value | Levels |
|-------|--------|
| `easy` | L0–L1 |
| `medium` | L2–L3 |
| `hard` | L4–L5 |

### `metadata`

Every item carries provenance metadata:

```json
{
  "created_by": "human",
  "version": "1.0",
  "source_type": "paraphrased_real",
  "source_verifiability": "verifiable"
}
```

| Field | Values | Meaning |
|-------|--------|---------|
| `source_type` | `real` | Verbatim extract from a real document |
| | `paraphrased_real` | Paraphrase of a real source; arguments/claims are historically grounded |
| | `composite` | Combines a real statute/text with a synthetic contract or scenario |
| | `synthetic` | Fully invented text (realistic documents, not toy examples) |
| `source_verifiability` | `verifiable` | Claims can be traced to real sources |
| | `illustrative` | Realistic but not intended to map to a specific real document |
| | `fictional` | Invented personas and documents; represents realistic but fictional scenarios |

**Per-domain provenance:**

| Domain | `source_type` | `source_verifiability` | Notes |
|--------|--------------|----------------------|-------|
| philosophy | `paraphrased_real` | `verifiable` | Named primary sources (Kant, Nietzsche, etc.) |
| software | `synthetic` | `illustrative` | Realistic system docs, configs, ADRs |
| law | `composite` | `verifiable` | Real statutes + synthetic contracts |
| science | `paraphrased_real` | `verifiable` | Real theories and papers, cited |
| content | `synthetic` | `fictional` | Invented creator profiles and posts |
| teams | `synthetic` | `fictional` | Invented team docs and Slack messages |

---

## Multi-Hop Difficulty Levels

| Level | Name | Definition |
|-------|------|-----------|
| 0 | Surface | Contradiction is explicitly stated in the text |
| 1 | Immediate | One certain inference from a stated premise collides with the other passage |
| 2 | Two-hop | Two chained inferences expose the conflict |
| 3 | Three-hop | Three chained inferences |
| 4 | Four-hop | Four chained inferences |
| 5 | Deep | Five chained inferences |

---

## Per-Domain Distribution (30 items per domain)

| Verdict | Count | Detail |
|---------|-------|--------|
| conflict | 18 (60%) | 3 items × levels 0–5 |
| consistent | 8 (27%) | No conflict level |
| ambiguous | 4 (13%) | Genuine underdetermined cases |

---

## Contributing New Items

1. Choose a domain and identify the target conflict level.
2. Write two passages that contain the conflict at exactly that depth.
3. Write the `reasoning_chain` — every step must follow with 100% certainty from the previous.
4. Verify: can the conflict be detected in fewer steps? If so, lower the level.
5. Add the item to `data/<domain>/v1.jsonl` as a single JSON line.
6. Run `python -m pytest tests/` to validate the dataset loads correctly.

### Reasoning chain quality checklist

- [ ] Each step is labelled `"Step N — ..."` (conflict) or uses `"AMBIGUOUS — ..."` (ambiguous)
- [ ] Final step of conflict chain starts with `"CONFLICT — "`
- [ ] No step makes a probabilistic or cultural inference — only 100% logical entailment
- [ ] The conflict cannot be detected by skipping any step
- [ ] Both passages are plausibly real (sourced to a realistic document or person)
