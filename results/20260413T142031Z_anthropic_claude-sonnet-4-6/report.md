# Benchmark Results — anthropic/claude-sonnet-4-6

**Run ID:** `20260413T142031Z`  |  **Items:** 180

## Overall Scores

| Metric                      |   Score |
|-----------------------------|---------|
| **LW-F1** _(primary score)_ |  0.7319 |
| Accuracy                    |  0.8111 |
| Macro-F1 (3-class)          |  0.7211 |
| Binary Conflict F1          |  0.938  |
| Explanation BERTScore-F1    |  0.8223 |
| — Conflict F1               |  0.8889 |
| — Consistent F1             |  0.8431 |
| — Ambiguous F1              |  0.4314 |

## By Difficulty Level

| Level        |   Accuracy |   Macro-F1 |   Conflict-F1 |   BERTScore-F1 |   N |
|--------------|------------|------------|---------------|----------------|-----|
| L0 Surface   |     0.7889 |     0.7474 |        0.8095 |         0.8164 |  90 |
| L1 Immediate |     0.7889 |     0.7457 |        0.8095 |         0.8225 |  90 |
| L2 Two-hop   |     0.7778 |     0.7315 |        0.7805 |         0.8232 |  90 |
| L3 Three-hop |     0.7889 |     0.7474 |        0.8095 |         0.8219 |  90 |
| L4 Four-hop  |     0.7222 |     0.6562 |        0.6111 |         0.8215 |  90 |
| L5 Deep      |     0.7556 |     0.7035 |        0.7179 |         0.8258 |  90 |

## By Domain

| Domain     |   Accuracy |   Macro-F1 |   Conflict-F1 |   BERTScore-F1 |   N |
|------------|------------|------------|---------------|----------------|-----|
| content    |     0.8333 |     0.6707 |        0.973  |         0.8166 |  30 |
| law        |     0.6667 |     0.5858 |        0.7333 |         0.8286 |  30 |
| philosophy |     0.8    |     0.7606 |        0.8485 |         0.8235 |  30 |
| science    |     0.8    |     0.6814 |        0.8824 |         0.8175 |  30 |
| software   |     0.8667 |     0.8159 |        0.9143 |         0.8229 |  30 |
| teams      |     0.9    |     0.8174 |        0.9474 |         0.8239 |  30 |

## By Difficulty Bucket

| Difficulty   |   Accuracy |   Macro-F1 |   Conflict-F1 |   BERTScore-F1 |   N |
|--------------|------------|------------|---------------|----------------|-----|
| easy         |     0.9254 |     0.6304 |        0.9577 |         0.8178 |  67 |
| hard         |     0.7347 |     0.3687 |        0.8395 |         0.8259 |  49 |
| medium       |     0.75   |     0.7227 |        0.8727 |         0.8221 |  64 |

## Example Failures

### Failure 1 — `philosophy_L2_003`
- **Domain:** philosophy  |  **Level:** L2  |  **Difficulty:** medium
- **Label:** `conflict`  |  **Predicted:** `ambiguous`
- **Model explanation:** **Step 1 — Derive implications:**

**From Passage A (Marx):**
- Human consciousness (including ideas, philosophy, culture) is causally produced by social/economic conditions.
- No domain of thought is fully autonomous from material/economic foundations.
- By strong implication: even philosophical an…

### Failure 2 — `philosophy_L4_001`
- **Domain:** philosophy  |  **Level:** L4  |  **Difficulty:** hard
- **Label:** `conflict`  |  **Predicted:** `ambiguous`
- **Model explanation:** Both passages agree that causation is mind-dependent rather than a feature of external reality independent of the mind. However, a potential conflict arises — and whether it is a genuine conflict depends on how key terms are resolved:

**The apparent conflict:**
Hume says causation is "a habit of th…

### Failure 3 — `philosophy_L4_002`
- **Domain:** philosophy  |  **Level:** L4  |  **Difficulty:** hard
- **Label:** `conflict`  |  **Predicted:** `ambiguous`
- **Model explanation:** The two passages address different aspects of political philosophy — the *origin* of property rights (Locke) and the *just distribution* of social and economic outcomes (Rawls) — and do not directly contradict each other on the surface. However, their logical implications pull in potentially incompa…

### Failure 4 — `philosophy_L5_001`
- **Domain:** philosophy  |  **Level:** L5  |  **Difficulty:** hard
- **Label:** `conflict`  |  **Predicted:** `ambiguous`
- **Model explanation:** **Derived Implications:**

**From Passage A (Wittgenstein):**
- The boundary of meaningful discourse coincides exactly with the boundary of what can be stated in clear propositions.
- Anything that cannot be stated clearly either says nothing meaningful or must not be spoken at all.
- There is no le…

### Failure 5 — `philosophy_C_007`
- **Domain:** philosophy  |  **Level:** n/a  |  **Difficulty:** medium
- **Label:** `consistent`  |  **Predicted:** `ambiguous`
- **Model explanation:** Both passages share a rationalist commitment — that reality has a necessary, intelligible structure graspable by reason. At the surface level they appear compatible. However, a potential conflict emerges from their derived implications that cannot be resolved without further context:

**The specific…
