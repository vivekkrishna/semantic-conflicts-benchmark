"""One-shot data fix script for R-1.1 and R-1.3 (newly discovered violations).

Covers:
  Group 1 — Chain-length trims: law_L0 ×3, science_L0 ×3, teams_L0 ×3
  Group 2 — AMBIGUOUS prefix:   law_A ×4, science_A ×4, content_A ×4
  Group 3 — teams_L1 restructure: teams_L1_001, teams_L1_002, teams_L1_003
  Group 4 — teams_L2 restructure: teams_L2_001, teams_L2_002, teams_L2_003
  Group 5 — Modal language rewrites (genuinely hedged):
             philosophy_L4_001, philosophy_L4_003,
             law_L1_001, science_L5_003,
             software_L3_001, software_L4_001
  Group 6 — Modal language (quoting passage → rephrase inference):
             philosophy_L3_002, philosophy_L4_002,
             software_L1_001, software_L2_002

Run from repo root:
    python scripts/fix_data_r11_r13.py
    python scripts/validate_dataset.py   # verify
"""

import json
from pathlib import Path

DATA_DIR = Path("data")


def load(domain: str) -> list[dict]:
    return json.loads((DATA_DIR / domain / "v1.json").read_text(encoding="utf-8"))


def save(domain: str, items: list[dict]) -> None:
    (DATA_DIR / domain / "v1.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def patch(items: list[dict], item_id: str, **label_fields) -> None:
    for item in items:
        if item["id"] == item_id:
            item["label"].update(label_fields)
            return
    raise KeyError(f"Item not found: {item_id}")


# =============================================================================
# GROUP 1 — Chain-length trims: L0 items whose "steps" just restate passages
# Correct form for L0: single "CONFLICT — ..." entry only.
# =============================================================================

# --- law_L0 ---
law = load("law")

patch(law, "law_L0_001", reasoning_chain=[
    "CONFLICT — The same document directly contradicts itself: Section 4.1 states "
    "termination by the Client carries 'no penalty or further obligation,' while "
    "Section 4.3 imposes a 50% termination fee for the identical act. One clause "
    "eliminates any penalty; the other imposes a substantial financial penalty.",
])

patch(law, "law_L0_002", reasoning_chain=[
    "CONFLICT — California Labor Code § 925 expressly prohibits requiring "
    "California-based employees to adjudicate California claims outside the state. "
    "Clause 19.2 expressly requires adjudication exclusively in Delaware for all "
    "employment disputes. The statute directly forbids exactly what the contract "
    "clause mandates — a surface-level, openly stated contradiction.",
])

patch(law, "law_L0_003", reasoning_chain=[
    "CONFLICT — Section 1 assigns Member Beta a 40% distribution share; Section 5 "
    "assigns the same member a 60% share during the first five fiscal years. Both "
    "provisions govern identical events and explicitly assign different percentages "
    "to the same member — a direct arithmetic contradiction within the same document.",
])

# --- science_L0 ---
science = load("science")

patch(science, "science_L0_001", reasoning_chain=[
    "CONFLICT — Passage A states the stomach is sterile and peptic ulcers are caused "
    "by acid, stress, and diet. Passage B states ulcers are caused by H. pylori "
    "bacterial infection and the stomach is not sterile. The passages directly "
    "contradict each other on both the sterility of the stomach and the etiology "
    "of peptic ulcers — a surface-level, explicitly stated temporal scientific conflict.",
])

patch(science, "science_L0_002", reasoning_chain=[
    "CONFLICT — Passage A states that electrical coupling between neurons does not "
    "occur in the mature vertebrate nervous system. Passage B states that electrical "
    "synapses are widespread in the adult vertebrate CNS and play critical functional "
    "roles. The passages directly and explicitly contradict each other — a surface-level "
    "conflict between early 20th-century doctrine and later empirical findings.",
])

patch(science, "science_L0_003", reasoning_chain=[
    "CONFLICT — Passage A states the universe is static, constant in size, and of "
    "infinite age. Passage B states the universe is expanding, originated 13.8 billion "
    "years ago, and that Einstein himself recanted the static model. The passages "
    "directly contradict each other on the fundamental nature of the universe — a "
    "surface-level conflict between the 1917 static model and Hubble's 1929 discovery.",
])

# --- teams_L0 ---
teams = load("teams")

patch(teams, "teams_L0_001", reasoning_chain=[
    "CONFLICT — Passage A explicitly states 'Breaking changes are not just acceptable "
    "— they are expected' and frames shipping speed above correctness as the team's "
    "core value. Passage B explicitly states 'I have never merged a change that breaks "
    "existing functionality, and I never will' and that backward compatibility is "
    "non-negotiable. Both passages directly state mutually exclusive positions on the "
    "same question — no interpretation is required.",
])

patch(teams, "teams_L0_002", reasoning_chain=[
    "CONFLICT — Passage A states 'There are no synchronous meetings of any kind on "
    "this team — not standups' as an absolute operating constraint. Passage B states "
    "the agent requires a daily 9am synchronous video standup with all team members "
    "as a hard operational requirement. The contradiction is stated directly and "
    "requires no inference.",
])

patch(teams, "teams_L0_003", reasoning_chain=[
    "CONFLICT — Passage A requires 'every architectural decision' to achieve "
    "documented consensus from at least three engineers, and states that unilateral "
    "technical decisions are not permitted at any seniority level. Passage B states "
    "the engineer makes architectural decisions alone, quickly, and views group "
    "consensus as a slowdown to avoid. The positions are mutually exclusive and "
    "explicitly stated.",
])


# =============================================================================
# GROUP 2 — AMBIGUOUS prefix
# law_A and science_A: final step uses "AMBIGUITY —" (should be "AMBIGUOUS —")
# content_A: final step uses "Step 3 —" (should be "AMBIGUOUS —")
# =============================================================================

# --- law_A: rename "AMBIGUITY —" → "AMBIGUOUS —" on final step ---
for item in law:
    if item["label"]["verdict"] == "ambiguous":
        chain = item["label"]["reasoning_chain"]
        if chain and chain[-1].startswith("AMBIGUITY — "):
            chain[-1] = "AMBIGUOUS — " + chain[-1][len("AMBIGUITY — "):]

# --- science_A: same ---
for item in science:
    if item["label"]["verdict"] == "ambiguous":
        chain = item["label"]["reasoning_chain"]
        if chain and chain[-1].startswith("AMBIGUITY — "):
            chain[-1] = "AMBIGUOUS — " + chain[-1][len("AMBIGUITY — "):]

# --- content_A: relabel final "Step N —" as "AMBIGUOUS —" ---
content = load("content")
_AMBIGUOUS_REWRITES = {
    "content_A_001": (
        "AMBIGUOUS — Without knowing what the 'transitional period' in Passage B "
        "entails, it is underdetermined whether Passage B contradicts Passage A "
        "(conflict) or merely signals an update yet to come (consistent evolution). "
        "The relationship is genuinely ambiguous pending the disclosure she withholds."
    ),
    "content_A_002": (
        "AMBIGUOUS — 'I'm not ready to make any public recommendations' explicitly "
        "defers whether her investing behaviour will change. Consistent evolution and "
        "conflict-in-progress are equally plausible given the available information."
    ),
    "content_A_003": (
        "AMBIGUOUS — 'A few other creators' could mean people he has known for years "
        "(consistent with his stated trust threshold) or new relationships he is moving "
        "faster with (potentially conflicting). The passage withholds the information "
        "needed to determine which case applies."
    ),
    "content_A_004": (
        "AMBIGUOUS — Without knowing which formats are being tested in Passage B, it "
        "is impossible to determine whether the experimental period represents a "
        "potential reversal of Passage A's anti-review position or an entirely "
        "unrelated content evolution. The ambiguity is genuine and unresolvable "
        "from the given text."
    ),
}
for item in content:
    if item["id"] in _AMBIGUOUS_REWRITES:
        chain = item["label"]["reasoning_chain"]
        chain[-1] = _AMBIGUOUS_REWRITES[item["id"]]


# =============================================================================
# GROUP 3 — teams_L1 restructures
# Each chain currently has 3 entries: one passage-reading + one real inference + CONFLICT.
# Fix: remove the passage-reading step; chain becomes 2 entries (Step 1 + CONFLICT).
# =============================================================================

patch(teams, "teams_L1_001", reasoning_chain=[
    "Step 1 — The retained fields — name, email address, and geographic location — "
    "are individually identifying and constitute PII under any standard definition.",
    "CONFLICT — One inference step (classifying the retained fields as PII) surfaces "
    "the conflict: the agent retains PII indefinitely, directly violating the team's "
    "hard 30-day retention limit for personal data.",
])

patch(teams, "teams_L1_002", reasoning_chain=[
    "Step 1 — 'Always install the latest stable release' with --upgrade resolves "
    "dependencies to their current latest version at install time — they are not "
    "pinned to a fixed version in a committed lockfile.",
    "CONFLICT — One inference step from the engineer's described practice "
    "(always-latest = not pinned) directly yields a violation of the team policy's "
    "exact-version-pin and committed-lockfile requirement.",
])

patch(teams, "teams_L1_003", reasoning_chain=[
    "Step 1 — Immediate direct calls to senior engineers when blocked is precisely "
    "the behaviour the escalation policy restricts to P0 production incidents; for "
    "all other situations the required first step is filing a written ticket and "
    "waiting twenty-four hours.",
    "CONFLICT — One inference step from 'call immediately when blocked' maps directly "
    "to behaviour the team escalation policy restricts to P0 incidents only.",
])


# =============================================================================
# GROUP 4 — teams_L2 restructures
# teams_L2_001 and teams_L2_002: mixed passage-readings and inferences.
#   Restructured into 2 genuine inference steps + CONFLICT (level stays L2).
# teams_L2_003: Step 3 is a passage-reading; Steps 1–2 are genuine inferences.
#   Remove Step 3; fold the passage reference into Step 2.
# =============================================================================

patch(teams, "teams_L2_001", reasoning_chain=[
    "Step 1 — Merging integration code 'without pausing for external approval "
    "workflows' means no review gate exists between code generation and the merge — "
    "the code reaches the working branch as soon as the agent generates it.",
    "Step 2 — Platform Security team review is an external approval workflow; "
    "'no external approval' therefore means no Platform Security review occurs "
    "before the integration code lands in main.",
    "CONFLICT — Passage A mandates Platform Security review for every third-party "
    "integration before merge to main. Steps 1–2 show this review is unconditionally "
    "bypassed by the agent's operating mode, with no exceptions.",
])

patch(teams, "teams_L2_002", reasoning_chain=[
    "Step 1 — Executing DDL directly against the production PostgreSQL instance "
    "during a maintenance window is definitionally 'direct Data Definition Language "
    "execution against production databases' — the two descriptions are equivalent.",
    "Step 2 — Skipping the feature flag means the schema change goes live immediately "
    "with no auto-rollback path, eliminating the emergency abort mechanism that the "
    "feature-flag-with-auto-rollback requirement exists to provide.",
    "CONFLICT — Two hops: (1) direct DDL on production violates the categorical "
    "prohibition; (2) the absent feature flag removes the required rollback safety net. "
    "Both conditions are simultaneously met; neither deadline pressure nor maintenance "
    "windows are listed exceptions.",
])

patch(teams, "teams_L2_003", reasoning_chain=[
    "Step 1 — If Sofia merges a PR on Thursday afternoon, the forty-eight-hour "
    "ownership window extends through Friday evening and into Saturday — a period "
    "outside her contracted working hours.",
    "Step 2 — Required reachability and rollback capability on Saturday directly "
    "conflict with the employment term in Passage B stating she has no professional "
    "obligations outside 9am–6pm Monday–Friday.",
    "CONFLICT — Two hops: (1) a Thursday merge produces a 48-hour window extending "
    "into non-working hours; (2) the required on-call availability during that window "
    "contradicts the employment contract's no-contact-outside-hours condition.",
])


# =============================================================================
# GROUP 5 — Genuine epistemic hedges: rewrite inference steps to 100% certainty
# =============================================================================

philosophy = load("philosophy")

# --- philosophy_L4_001: four steps each contain "could" ---
patch(philosophy, "philosophy_L4_001", reasoning_chain=[
    "Step 1 — From A: Causation is a psychological habit → it is contingent and "
    "variable across individuals; a mind can observe the same sequence of events "
    "without forming a causal interpretation.",
    "Step 2 — From Step 1: If causation is merely a contingent psychological habit → "
    "there is no necessity to the causal connection. The same events are in principle "
    "experienceable without any causal interpretation.",
    "Step 3 — From Step 2: If causal interpretation is not necessary → the structure "
    "of experience is not necessarily causal. Acausal experience is a coherent "
    "possibility on Hume's account.",
    "Step 4 — From Step 3: If acausal experience is coherent → causation is not a "
    "necessary, universal, a priori condition of experience itself.",
    "CONFLICT — Passage B states causation is an a priori category without which "
    "experience is impossible — making it a necessary, universal condition. Step 4 "
    "directly contradicts this: under Hume, causation is contingent and unnecessary.",
])

# --- philosophy_L4_003: Step 4 contains "could rationally" ---
patch(philosophy, "philosophy_L4_003", reasoning_chain=[
    "Step 1 — From A: The fundamental drive is will to power — growth and "
    "self-overcoming — 'even self-preservation is subordinate to this.'",
    "Step 2 — From Step 1: If self-preservation is subordinate to will to power → "
    "there are conditions under which an organism sacrifices its own survival in "
    "order to express or expand its power (e.g., reckless risk for dominance).",
    "Step 3 — From Step 2: If self-sacrifice for power-expression is possible → "
    "the organism's deepest goal is not to persist but to discharge strength. "
    "Survival is an instrument, not the final end.",
    "Step 4 — From Step 3: If survival is merely instrumental → accepting death as "
    "the price of greater power-expression follows from the will-to-power's inner "
    "logic. The will-to-live is not the deepest principle.",
    "CONFLICT — Passage B states the will to live is the fundamental, primary drive "
    "and that all organisms 'strive above all to preserve their own existence.' "
    "Step 4 shows Nietzsche's will to power makes self-preservation merely "
    "instrumental, directly contradicting Schopenhauer's claim.",
])

# --- law_L1_001: Step 1 contains "could be terminated" ---
patch(law, "law_L1_001", reasoning_chain=[
    "Step 1 — HR-14 prohibits employees from disclosing company information to any "
    "party, including government agencies, without prior written consent — an employee "
    "reporting federal crimes to law enforcement without consent violates HR-14 and "
    "is subject to termination under that policy.",
    "CONFLICT — Terminating an employee specifically because they provided truthful "
    "information about a federal offense to law enforcement is the very conduct "
    "criminalized by 18 U.S.C. § 1513(e). The policy creates the precondition for "
    "a federal crime in one inference step.",
])

# --- science_L5_003: Step 3 contains "could interact" ---
patch(science, "science_L5_003", reasoning_chain=[
    "Step 1 — Copenhagen (Passage A) requires a sharp, fundamental distinction "
    "between the classical measuring apparatus/observer and the quantum system being "
    "measured. The collapse is triggered by this boundary — the measurement postulate "
    "is irreducible and not derivable from unitary Schrödinger evolution alone.",
    "Step 2 — Decoherence theory (Passage B) shows that the apparent collapse of the "
    "wavefunction arises from entanglement with environmental degrees of freedom — a "
    "fully unitary process described by the Schrödinger equation. No special observer, "
    "apparatus, or non-unitary collapse postulate is required.",
    "Step 3 — For macroscopic objects at room temperature, decoherence occurs in "
    "~10⁻²³ seconds — so fast that quantum superpositions of macroscopic states are "
    "destroyed by environmental entanglement long before any human observer interacts "
    "with the system. The observer therefore plays no causal role in the collapse.",
    "Step 4 — Copenhagen treats wavefunction collapse as a fundamental, non-unitary "
    "dynamical law that supplements the Schrödinger equation. Decoherence theory shows "
    "that no such supplemental law is needed — the appearance of collapse emerges from "
    "unitary dynamics alone. If decoherence is correct, the collapse postulate is "
    "redundant; if Copenhagen is correct and collapse is a primitive irreducible law, "
    "decoherence provides only an approximation, not a derivation.",
    "Step 5 — The two frameworks make mutually exclusive ontological claims about the "
    "completeness of the wavefunction description. Copenhagen holds that ψ is complete "
    "and collapse creates a definite outcome. Decoherence-based interpretations hold "
    "that ψ remains complete and unitary but the apparent collapse is perspectival — "
    "multiple branches coexist. Either definite outcomes are created by non-unitary "
    "collapse (Copenhagen) or they are not (decoherence/Everett). These ontologies "
    "are mutually exclusive.",
    "CONFLICT — Five inference steps trace the conflict from Copenhagen's measurement "
    "boundary, through decoherence's derivation of apparent collapse from unitary "
    "dynamics, through the observer's causal irrelevance at 10⁻²³ s timescales, to "
    "the redundancy of the collapse postulate, and finally to the incompatible "
    "ontological claims — a foundational conflict in quantum foundations that remains "
    "unresolved.",
])

# --- software_L3_001: Step 1 contains "may find" ---
software = load("software")

patch(software, "software_L3_001", reasoning_chain=[
    "Step 1 — From B: Log compaction removes intermediate message states that have "
    "not yet been consumed → a consumer that has not yet read a message will find it "
    "removed by the compactor when compaction runs.",
    "Step 2 — From Step 1: If an unconsumed message is removed by the compactor → "
    "that message will never be delivered to the consumer. The consumer receives zero "
    "deliveries for that message.",
    "Step 3 — From Step 2: If a message can be removed before being consumed → "
    "exactly-once delivery cannot be guaranteed — some messages will be delivered "
    "zero times.",
    "CONFLICT — Passage A guarantees no message is lost (every message delivered at "
    "least once, at most once). Step 3 shows that log compaction can delete unconsumed "
    "messages, violating the 'at least once' component of exactly-once delivery.",
])

# --- software_L4_001: Step 3 contains "may be processing" ---
patch(software, "software_L4_001", reasoning_chain=[
    "Step 1 — From A: Lock lease expires after 30 seconds if not renewed → a lock "
    "held for more than 30 seconds without renewal is automatically released.",
    "Step 2 — From Step 1: If a worker acquires a lock and begins processing a job "
    "that runs for 31–45 seconds, the lock expires at 30s while the worker is still "
    "processing → another worker can acquire the same lock at second 30.",
    "Step 3 — From Step 2: If two workers simultaneously hold the same lock → mutual "
    "exclusion is violated. Both workers are then processing the same resource "
    "concurrently.",
    "Step 4 — From Step 3: If mutual exclusion is violated → the guarantee stated in "
    "A ('at most one process holds any given lock at any time') is violated for all "
    "jobs running 30–45 seconds.",
    "CONFLICT — Passage A guarantees mutual exclusion; Passage B allows jobs up to "
    "45 seconds without lock renewal logic. Steps 1–4 show that any job between 30 "
    "and 45 seconds will violate the mutual exclusion guarantee.",
])


# =============================================================================
# GROUP 6 — Quoting-modal rewrites: passage text contains the modal word;
# rephrase the inference step so it doesn't echo the passage's modal.
# =============================================================================

# --- philosophy_L3_002: Step 1 quotes "may never be violated" ---
patch(philosophy, "philosophy_L3_002", reasoning_chain=[
    "Step 1 — From A: Each rational being possesses inherent dignity that is "
    "inviolable — no external outcome, however compelling, can justify treating "
    "a person merely as a means to an end.",
    "Step 2 — From Step 1: 'Never for any external purpose' explicitly includes "
    "maximising aggregate happiness — even the welfare of the many cannot justify "
    "violating one person's dignity.",
    "Step 3 — From Step 2: Therefore, there exists at least one scenario (sacrificing "
    "one for the many) that is absolutely forbidden regardless of aggregate welfare.",
    "CONFLICT — Passage B states that 'justice requires' the individual to bear the "
    "cost when aggregate welfare demands it. This is precisely the scenario Step 3 "
    "declares absolutely forbidden.",
])

# --- philosophy_L4_002: Steps 1–3 contain "may not" (deontic/quoting) ---
patch(philosophy, "philosophy_L4_002", reasoning_chain=[
    "Step 1 — From A: Labour-mixing creates ownership rights that are inviolable — "
    "others cannot override them for social utility. These are negative, "
    "side-constraint rights that exist independently of aggregate outcomes.",
    "Step 2 — From Step 1: If property rights are inviolable side constraints → the "
    "state cannot redistribute property holdings even when redistribution would "
    "benefit the worst-off, because redistribution violates the rights of "
    "property holders.",
    "Step 3 — From Step 2: If redistribution of legitimately acquired property is "
    "forbidden → significant, persistent inequalities arising from legitimate initial "
    "acquisitions are just and admit no correction through redistribution.",
    "Step 4 — From Step 3: If persistent inequalities from legitimate acquisition are "
    "just → there is no Rawlsian 'difference principle' obligation to alter "
    "inequalities that happen not to benefit the worst-off.",
    "CONFLICT — Passage B requires institutions to be structured so that inequalities "
    "maximise benefits to the worst-off. Step 4 shows that under Lockean rights, "
    "there is no such obligation — inequalities stemming from legitimate property "
    "rights are just regardless of their effect on the worst-off.",
])

# --- software_L1_001: Step 1 quotes "Clients may safely retry" ---
patch(software, "software_L1_001", reasoning_chain=[
    "Step 1 — From A: The endpoint is idempotent and safe to retry with the same "
    "key → retrying with the same idempotency key must produce no additional "
    "observable side effects beyond the first call.",
    "CONFLICT — The implementation unconditionally sends an email and adds loyalty "
    "points on every call, regardless of idempotency key. These side effects are NOT "
    "idempotent — a retry produces a second email and second points addition, "
    "directly contradicting the idempotency guarantee stated in Passage A.",
])

# --- software_L2_002: Step 1 quotes "No service may maintain" ---
patch(software, "software_L2_002", reasoning_chain=[
    "Step 1 — From A: The prohibition on persistent local copies of order records "
    "applies to all services → the Shipping Service must not store order data in "
    "its own database.",
    "Step 2 — From Step 1: If the Shipping Service must not store order data → the "
    "table `local_orders` in the Shipping Service's schema, which stores order_id, "
    "customer_id, total_amount, and status, violates this principle.",
    "CONFLICT — The Shipping Service migration creates a `local_orders` table that "
    "is a persistent local copy of order records — precisely what the architecture "
    "document forbids.",
])


# =============================================================================
# Save all modified files
# =============================================================================
save("law",        law)
save("science",    science)
save("teams",      teams)
save("content",    content)
save("philosophy", philosophy)
save("software",   software)

print("All fixes applied.")
