# Human Annotation Guide

This guide is for anyone reviewing, correcting, or extending items in the
Semantic Conflicts Benchmark dataset. Read it in full before touching any data file.

---

## 1. What the benchmark measures

The benchmark tests whether a reasoning system can detect **semantic conflicts
between two text passages** — disagreements that require genuine inference, not just
surface-level keyword matching.

Each item presents two passages and asks: is their relationship a **conflict**,
**consistent**, or **ambiguous**?

The key challenge is the difficulty gradient:
- **L0 (surface):** The conflict is stated explicitly. Reading both passages is enough.
- **L1–L5 (implicit):** The conflict requires 1 to 5 chained inference steps. A model
  that only matches surface patterns will fail at L2+.

Your job as a reviewer is to verify that items faithfully represent this gradient.

---

## 2. Item structure

Each item in `data/<domain>/v1.json` has this shape:

```json
{
  "id": "philosophy_L3_002",
  "domain": "philosophy",
  "conflict_level": 3,
  "difficulty": "medium",
  "input": {
    "passages": [{"id": "A", "text": "...", "source": "..."}, {"id": "B", ...}],
    "question": "Do these passages present a conflict, are they consistent, or is the relationship ambiguous?"
  },
  "label": {
    "verdict": "conflict",
    "conflict_level": 3,
    "reasoning_chain": ["Step 1 — ...", "Step 2 — ...", "Step 3 — ...", "CONFLICT — ..."],
    "explanation": "...",
    "conflicting_spans": [{"passage_id": "A", "span": "..."}, ...],
    "ambiguity_reason": null
  }
}
```

**Fields you may be asked to review:**
- `verdict` — the label (conflict / consistent / ambiguous)
- `conflict_level` — number of inference steps required (0–5 for conflict items; null for consistent/ambiguous)
- `reasoning_chain` — the step-by-step derivation; must follow strict rules (see section 4)
- `explanation` — prose explanation of why the conflict exists and what makes it hard to spot
- `ambiguity_reason` — for ambiguous items: the specific gap in information that makes the conflict uncertain

---

## 3. Verdict decision rules

### 3.1 When to label an item CONFLICT

Use **conflict** when both of the following are true:

1. The two passages make claims that **cannot both be true at the same time** under any reasonable interpretation.
2. The contradiction can be **derived with 100% logical certainty** — not just suggested or likely.

A conflict does not require the passages to use the same words. It can be implicit (requires inference). But the final step must be logically necessary, not merely plausible.

**Ask yourself:** If I follow the reasoning chain step by step, is there any reading of the passages under which the conflict disappears? If yes, it is not a conflict — reconsider the label.

### 3.2 When to label an item CONSISTENT

Use **consistent** when:

The two passages are compatible under at least one reasonable reading of the words used. They may discuss different aspects of a topic, apply to different contexts, or be reconciled by a plausible background assumption available in the passage text.

**Ask yourself:** Can I construct a short sentence that explains how both passages can be true at the same time, using only information in the passages? If yes, it is consistent.

### 3.3 When to label an item AMBIGUOUS

Use **ambiguous** when:

The conflict **exists under one interpretation** but **disappears under another**, and the passages do not supply enough information to determine which interpretation is correct. The ambiguity must depend on a genuinely unresolvable gap.

**The boundary rule (critical):**

> An item is **AMBIGUOUS** if and only if the conflict's existence depends on an
> unstated empirical, legal, or interpretive fact that cannot be resolved from the
> passage text alone.
>
> An item is **CONSISTENT** if the passages are compatible under any reasonable
> reading of the words used — even if one reading requires a charitable interpretation.

**Borderline test:** If you find yourself saying "it depends on whether X is true, and we can't know from the passages" — that is AMBIGUOUS. If you find yourself saying "well, if you read it generously, both could be fine" — that is CONSISTENT.

### 3.4 Common labeling mistakes

| Mistake | What it looks like | Correction |
|---|---|---|
| Over-labeling conflict | Seeing a conflict where a reasonable reconciliation exists | Ask: can I write one sentence that resolves this? If yes → consistent |
| Under-labeling conflict | Treating a certain contradiction as ambiguous | Ask: is there actually a missing fact, or is the contradiction just subtle? |
| Conflating consistent and ambiguous | Marking "could be either" as consistent | Ambiguous = missing fact decides it. Consistent = no conflict under any reading. |
| Accepting contested premises | Chain step states a contested philosophical claim as fact | Flag as `contested_premise` |

### 3.5 Destructive vs constructive (conflict items only)

Every conflict item also carries a `conflict_polarity`. Decide it with one question:

> **If nobody resolves this conflict and both passages stay in force, what happens?**

| Label | Choose it when | Typical signals |
|---|---|---|
| `destructive` | Leaving the conflict in place causes concrete damage to someone | system failure or corrupted state; legal, regulatory or financial exposure; safety or health risk; a broken commitment that others relied on; wasted work |
| `constructive` | The conflict is a productive tension; working through it improves understanding or a decision, and its existence harms no one | a theory meeting contrary evidence; a dialectical disagreement between schools; a legitimate trade-off raised before anyone acts on it |

**Decision rules**

1. **Judge the situation the passages describe, not the domain.** A lab protocol that contradicts a chemical safety data sheet is destructive even though it is "science"; two engineers debating a design trade-off in review is constructive even though it is "software".
2. **Reliance makes it destructive.** If a third party acts on one passage (a client trusting an API contract, an audience trusting a creator's stated principle, a counterparty relying on a clause), the conflict harms them.
3. **Hard boundaries make it destructive.** If one passage is a legal, contractual, security or safety rule and the other breaches it, label destructive, even if the breach looks well-intentioned.
4. **Proposal-stage trade-offs lean constructive.** When both sides express legitimate goals and nothing has been executed yet, surfacing the conflict forces a better decision. If the proposal *as written* would immediately break something (e.g. merging non-deployable PRs), it is still destructive.
5. **Superseded knowledge is constructive.** A temporal conflict where later evidence overturns an earlier theory is the engine of inquiry. A temporal conflict where stale information is still being *acted on* (e.g. a stale cache) is destructive.

**Worked examples**

| Item | Label | Why |
|---|---|---|
| `software_L0_003` — cache says 247 in stock, DB says 0 | destructive | customers buy stock that does not exist |
| `science_L0_001` — "stomach is sterile" vs H. pylori | constructive | overturned the old model, led to a cure |
| `law_L0_001` — penalty-free exit vs 50% exit fee in one contract | destructive | guaranteed dispute the moment the right is exercised |
| `teams_L1_002` — pin all deps vs always-latest | constructive | a real trade-off whose resolution (automated update PRs) serves both goals |
| `content_L2_002` — "fasting harms women" vs a women's fasting guide | destructive | exposes followers to the health risk she warned about |

Write `polarity_rationale` as **one sentence naming the consequence** that decided the label. Set `polarity_status` to `"reviewed"` once a human has confirmed or corrected it.

**Known limitation:** the v1 labels track domain closely (law, software and content are mostly destructive; science and philosophy entirely constructive). New items should prefer counter-examples — destructive science, constructive law and software — so the label cannot be guessed from the domain.

---

## 4. Reasoning chain rules

The `reasoning_chain` is the most important field. A chain that violates any rule
below is **invalid** and must be rewritten or the item must be relabeled.

### 4.1 Chain length

For conflict items: `len(reasoning_chain) == conflict_level + 1`

- L0 → 1 entry total: just `CONFLICT — ...`
- L1 → 2 entries: `Step 1 — ...` then `CONFLICT — ...`
- L2 → 3 entries: `Step 1 — ...`, `Step 2 — ...`, `CONFLICT — ...`
- L3 → 4 entries, L4 → 5, L5 → 6

For consistent items: typically 1–2 sentences, no Step numbering required.
For ambiguous items: any number of steps, but the **final entry must start with `AMBIGUOUS — `**.

### 4.2 Final entry format

- Conflict items: final entry must start with exactly `CONFLICT — `
- Ambiguous items: final entry must start with exactly `AMBIGUOUS — `
- Consistent items: no special format required

### 4.3 100% certainty rule

**Every step must follow from the previous with 100% logical certainty.**

Prohibited: any language that introduces probability, possibility, or epistemic hedging.

**Banned words in Step N entries:** may, might, could, perhaps, arguably, likely, suggests, possibly, probably, potentially

**Exception — quoted source material:** If a passage or cited document uses a modal
word (e.g., "the contract states 'employees may not...'"), the inference step may
quote this language *only if the quotation itself is the premise*, and the inference
drawn from the quotation is certain. The inference must not use the modal as its own
claim.

Acceptable: `Step 2 — ADR-014 prohibits any service from holding a direct database connection...`
Not acceptable: `Step 2 — ADR-014 states 'No service may hold...' and this means connections may be a violation.`

### 4.4 Minimality rule

The conflict level must represent the **minimum** number of inference steps required
to detect the conflict. No step may be skippable.

**Minimality test:** For each Step N, ask: "If I remove this step and connect the
previous step directly to the next, does the inference still hold?"

If yes → the step is redundant → lower the level by 1 (or remove the step and
renumber).

If removing *any* step breaks the inference → the chain is minimal → the level is correct.

### 4.5 No passage-reading steps

Steps must encode **inferences**, not passage summaries. A step that merely
restates what a passage says is not an inference step and must be removed.

Not acceptable: `Step 1 — Passage A states that X and Y.`
Acceptable: `Step 1 — Since X (from Passage A) and Y is defined as Z, it follows that...`

The conflict_level counts only genuine inferences, not re-readings.

---

## 5. How to review an item

Work through this checklist for every item you are assigned:

**Step 1 — Read the passages without looking at the label.**
Form your own initial verdict (conflict / consistent / ambiguous) and a rough sense
of difficulty. Write it down before reading further.

**Step 2 — Check the verdict.**
Compare your verdict to the stored label. If they differ, apply the decision rules
in section 3. If you still disagree, record the dispute in the review queue.

**Step 3 — Walk through the reasoning chain step by step.**
For each step, verify:
- [ ] Does this step follow with 100% logical certainty from the previous step and the passage text?
- [ ] Does this step use any prohibited modal language?
- [ ] Is this step a genuine inference (not just a passage restatement)?
- [ ] If I skip this step, does the chain break? (minimality)

**Step 4 — Check the final entry.**
- Conflict items: starts with `CONFLICT — `?
- Ambiguous items: starts with `AMBIGUOUS — `?

**Step 5 — Check chain length.**
`len(reasoning_chain) == conflict_level + 1` for conflict items.

**Step 6 — Check the explanation.**
The `explanation` field should describe: (a) what the conflict is, (b) what makes it
hard to detect at first glance, (c) what inference path resolves it. It should not
introduce new arguments not in the chain.

**Step 7 — Record your decision.**
Use one of the outcomes below.

---

## 6. Review outcomes

After reviewing an item, record one of these outcomes in `data/review_queue.json`:

### Accept as-is
The item is correct. Update the queue entry:
```json
{
  "status": "resolved",
  "resolution_note": "Reviewed by [your name]. Chain is minimal, all steps are certain, verdict is correct.",
  "resolved_by": "[your name or handle]",
  "resolved_date": "YYYY-MM-DD"
}
```

### Accept with minor edits
You made a small correction (typo, rewording that does not change meaning). Describe
what you changed in `resolution_note`. Set `status: "resolved"`.

### Flag a dispute
You disagree with the verdict or level but are not certain enough to change it unilaterally.
Set `status: "in_review"` and write your reasoning in `resolution_note`. Bring to the
maintainer for discussion.

### Change the label
You are confident the item is mislabeled. Make the edit in `data/<domain>/v1.json`,
run `python scripts/validate_dataset.py --strict`, and record the change:
```json
{
  "status": "resolved",
  "resolution_note": "Changed verdict from 'conflict' to 'ambiguous'. Original chain assumed [X] with certainty, but X is not stated in either passage — see ambiguity_reason added.",
  "resolved_by": "[your name]",
  "resolved_date": "YYYY-MM-DD"
}
```

### Demote the level
You confirmed the conflict can be detected in fewer steps. Remove the skippable step
from the chain, decrement `conflict_level` by 1, and run the validator. Record in queue.

### Flag as won't fix
The item has a known limitation (e.g., contested philosophical premise) that is
acknowledged but accepted. Set `status: "wont_fix"` and explain why in `resolution_note`.

---

## 7. How to add a new flag

If you identify an issue with an item that is not yet in the review queue, add an
entry to `data/review_queue.json`:

```json
{
  "item_id": "philosophy_L2_001",
  "flag_type": "contested_premise",
  "status": "open",
  "flagged_by": "[your name]",
  "flagged_date": "YYYY-MM-DD",
  "description": "Step 1 asserts that Kant's categorical imperative applies to commercial contracts — this is a contested reading in applied ethics.",
  "resolution_note": null,
  "resolved_by": null,
  "resolved_date": null
}
```

Valid `flag_type` values:
- `minimality` — chain may be over-specified
- `modal_rewrite` — a modal-word fix was applied; needs semantic verification
- `contested_premise` — step encodes a non-universal claim as fact
- `label_dispute` — verdict or level may be wrong
- `leakage_risk` — item uses a canonically famous pairing
- `chain_quality` — logical gap or weak entailment in a step
- `boundary_ambiguity` — item sits on the consistent/ambiguous line
- `canary_regression` — automated probe flagged this item
- `polarity_draft` — drafted destructive/constructive label awaiting human review
- `manual` — anything else (describe in `description`)

---

## 8. Priority order for review

Work in this order:

1. **`modal_rewrite` flags** — these are items where an automated fix may have
   changed meaning. Verifying semantic equivalence is urgent.

2. **L5 `minimality` flags** — L5 items carry 6× weight in the primary metric. A
   mislabeled L5 item has more impact than a mislabeled L0 item.

3. **L4 `minimality` flags** — 5× weight, high impact.

4. **`contested_premise` flags** — affects validity of the entire chain.

5. **L3 `minimality` flags** — 4× weight.

6. **`boundary_ambiguity` flags** — affects the ambiguous class, which is already
   small (4 items per level) and poorly calibrated in current models.

7. **`label_dispute` flags** — resolve via discussion with maintainer.

8. **`polarity_draft` flags** — confirm or correct the drafted `conflict_polarity`,
   then set `label.polarity_status` to `"reviewed"`. Do the `[BORDERLINE]` entries
   first. These labels do not affect LW-F1, but they are not scored at all until reviewed.

---

## 9. Submitting your review

After completing your reviews:

1. Run the validator to confirm no structural errors were introduced:
   ```bash
   python scripts/validate_dataset.py --strict
   ```

2. Commit your changes to `data/<domain>/v1.json` and `data/review_queue.json`
   together in a single commit. Use a message like:
   ```
   Review: resolve minimality flags for philosophy_L4_001, philosophy_L4_002
   ```

3. Open a pull request. In the PR description, list:
   - Items reviewed
   - Items changed and what changed
   - Items you flagged as disputes (needs discussion)
   - Items you accepted as-is

4. Ping the maintainer for any unresolved disputes before merging.

---

## 10. What not to do

- Do not change `conflict_level` without also updating the `reasoning_chain` length.
- Do not change a verdict without updating `ambiguity_reason` (for ambiguous items) or `conflicting_spans` (for conflict items).
- Do not add modal language to inference steps. If a step cannot be made certain, the item must be relabeled or the level lowered.
- Do not accept a chain step that is purely a passage restatement — all steps must be genuine inferences.
- Do not merge your own PR without a second reviewer if you changed a verdict or conflict_level.
