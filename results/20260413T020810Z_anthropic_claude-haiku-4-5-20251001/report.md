# Benchmark Results — anthropic/claude-haiku-4-5-20251001

**Run ID:** `20260413T015546Z`  |  **Items:** 180

## Overall Scores

| Metric                      |   Score |
|-----------------------------|---------|
| **LW-F1** _(primary score)_ |  0.3333 |
| Accuracy                    |  0.6333 |
| Macro-F1 (3-class)          |  0.329  |
| Binary Conflict F1          |  0.859  |
| Explanation ROUGE-L         |  0.2331 |
| — Conflict F1               |  0.7687 |
| — Consistent F1             |  0.2182 |
| — Ambiguous F1              |  0      |

## By Difficulty Level

| Level        |   Accuracy |   Macro-F1 |   Conflict-F1 |   ROUGE-L |   N |
|--------------|------------|------------|---------------|-----------|-----|
| L0 Surface   |          1 |     0.3333 |             1 |    0.2175 |  18 |
| L1 Immediate |          1 |     0.3333 |             1 |    0.247  |  18 |
| L2 Two-hop   |          1 |     0.3333 |             1 |    0.2564 |  18 |
| L3 Three-hop |          1 |     0.3333 |             1 |    0.2267 |  18 |
| L4 Four-hop  |          1 |     0.3333 |             1 |    0.2422 |  18 |
| L5 Deep      |          1 |     0.3333 |             1 |    0.2311 |  18 |

## By Domain

| Domain     |   Accuracy |   Macro-F1 |   Conflict-F1 |   ROUGE-L |   N |
|------------|------------|------------|---------------|-----------|-----|
| content    |     0.6667 |     0.3879 |        0.8    |    0      |  30 |
| law        |     0.6    |     0.25   |        0.75   |    0.2315 |  30 |
| philosophy |     0.6667 |     0.3942 |        0.7826 |    0.2143 |  30 |
| science    |     0.6333 |     0.3294 |        0.766  |    0.2383 |  30 |
| software   |     0.6333 |     0.3294 |        0.766  |    0.2489 |  30 |
| teams      |     0.6    |     0.25   |        0.75   |    0      |  30 |

## By Difficulty Bucket

| Difficulty   |   Accuracy |   Macro-F1 |   Conflict-F1 |   ROUGE-L |   N |
|--------------|------------|------------|---------------|-----------|-----|
| easy         |     0.6119 |     0.3401 |        0.7347 |    0.2322 |  67 |
| hard         |     0.9184 |     0.3191 |        0.9574 |    0.2291 |  49 |
| medium       |     0.4375 |     0.2356 |        0.6067 |    0.2401 |  64 |

## Example Failures

### Failure 1 — `philosophy_C_002`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** easy
- **Label:** `consistent`  |  **Predicted:** `conflict`
- **Model explanation:** **Derivation of Implications:**

**Passage A implies:**
1. Reason is the highest human faculty
2. Living according to reason produces the noblest/most excellent life
3. Intellectual virtue is superior to other forms of virtue
4. Therefore, actualizing reason is central to human excellence

**Passage…

### Failure 2 — `philosophy_C_003`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** easy
- **Label:** `consistent`  |  **Predicted:** `conflict`
- **Model explanation:** **Step 1 — Derive implications:**

**From Passage A:**
- Events outside our control include: actions of others, reputations, bodies
- Only our judgement, impulse, desire, and aversion are within our power
- Anything not in our power should not be the basis of our wellbeing or virtue
- What we can co…

### Failure 3 — `philosophy_C_004`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** medium
- **Label:** `consistent`  |  **Predicted:** `conflict`
- **Model explanation:** **Reasoning:**

**Step 1 — Derive implications:**

From Passage A:
- Locke and Rousseau reject force-based justification for political authority
- Locke and Rousseau reject tradition-based justification for political authority
- Legitimate political authority requires justification to the governed
-…

### Failure 4 — `philosophy_C_006`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** easy
- **Label:** `consistent`  |  **Predicted:** `conflict`
- **Model explanation:** **Reasoning:**

**Step 1 — Derive implications from each passage:**

*From Passage A (Aristotle):*
- The universe has a natural, ordered structure
- Every natural thing has a proper end or function (telos)
- Ethics is grounded in natural teleology
- Therefore: ethical principles derive from examinin…

### Failure 5 — `philosophy_C_007`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** medium
- **Label:** `consistent`  |  **Predicted:** `conflict`
- **Model explanation:** **Explanation:**

**Derived implications:**

From Passage A:
- All events and facts follow necessarily from the nature of God/Nature
- Human actions and thoughts are determined by this logical necessity
- There is no contingency or genuine alternative possibility in reality

From Passage B:
- All tr…
