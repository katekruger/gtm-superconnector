# Skills

A skill is a procedure Claude follows — an ordered sequence of tool calls with explicit stopping points. They live in [`skills/`](../skills/), one directory each, with a `SKILL.md` and optional `references/`.

Every skill in this plugin shares four properties:

1. **Read before write.** Check the CRM before enriching; get the complete dataset before analyzing.
2. **Degrade, never substitute.** The CRM connector is user-supplied and may be absent. When it
   is, the skill says so and labels its output partial. It never fills a missing CRM field from
   Clay and presents it as a CRM record — that would convert "unknown" into "known", which is
   the exact failure this plugin exists to prevent.
3. **Preserve uncertainty.** Missing fields are reported as missing. Partial results are labelled partial.
4. **Stop at a gate.** No skill sends, uploads, launches, or writes back without separate explicit approval.

---

## account-intelligence

**Triggers on:** research an account, get account 360, source ICP companies, rank accounts, find the best contact.

Searches the CRM by domain first (skipping that step, and labelling the run partial, when no CRM is configured), uses Clay only to fill genuine gaps, then scores through `gtm_score_icp_accounts`, `gtm_rank_team_adoption`, and `gtm_rank_best_contact`.

Two rules do the heavy lifting:

- Coding-agent, open-source, AI-tooling, and developer-workflow claims **require source URLs**. Truthiness-checked evidence fields mean an unsourced `true` would score identically to a real citation — the skill closes that gap procedurally.
- *"Do not convert absence of evidence into a negative claim."* A missing signal is missing, not false.

Scoring criteria: [`skills/account-intelligence/references/criteria.md`](../skills/account-intelligence/references/criteria.md).

**Ends at:** a ranked summary with evidence, missing fields, and a recommended next research step.

---

## outreach-builder

**Triggers on:** build an outreach campaign, prepare design-partner outreach, verify a contact, draft a campaign.

The longest chain in the plugin, and the one with the most gates. It retrieves prior CRM context and replies *before* generating anything new, ranks contacts, resolves addresses only when missing, classifies every selected address, bundles provenance, and produces a paused campaign plan.

Paid verification and PDL stay **disabled** unless the user approves the cost. Only `verified` and `verified:commit` are treated as send-ready; everything else is quarantined.

**Ends at:** a preview. Contact upload, CRM write-back, campaign creation, launch, and sending each require separate approval — see [`references/approval-gates.md`](../skills/outreach-builder/references/approval-gates.md).

The final gate rule is worth quoting: **never construct email addresses by hand.** A hand-built address bypasses the entire status vocabulary.

---

## clay-reconciliation

**Triggers on:** reconcile Clay, diff the user snapshot, sync users, check schema drift.

Obtains complete snapshots from both sides without modifying either, diffs on `user_id`, and reports inserts, field-level updates, unchanged rows, missing records, missing IDs, and schema drift **as separate categories**.

The subtle rule: *treat deduplication as duplicate suppression only.* A deduplication pass that reports "1,200 rows processed" has not updated 1,200 rows, and the skill refuses to claim otherwise without evidence.

**Ends at:** a dry run. Publication, upload, and write-back require approval.

---

## activation-review

**Triggers on:** find activation drop-off, analyze inactive users, find users without repositories.

Requires the complete user dataset rather than a partial contact export — a drop-off analysis on a filtered export measures the filter. Separates the three cohorts from `gtm_detect_activation_dropoff` and ranks them by recency, account concentration, and sponsor value where those fields exist.

Reports **missing instrumentation** alongside results, so a gap in tracking is not read as a gap in usage.

**Ends at:** cohort counts, representative records, and recommended follow-up. No messages sent, no lifecycle stages changed.

---

## n8n-operations

**Triggers on:** debug n8n, inspect a workflow failure, dry run a workflow, retry an execution.

A diagnostic loop that ends at a guarded write. Calls `n8n_health` first, works only from `n8n_list_approved_workflows`, validates structure and previews input before anything executes, then compares the failed execution against `n8n_last_known_good` to isolate what changed.

Explains the cause **with exact execution evidence** rather than a plausible narrative.

**Ends at:** a retry preview via `confirm=false`. The actual retry requires approval naming the execution ID, the workflow ID, and whether to load the latest saved workflow.

---

## Writing a new skill

```
skills/your-skill/
├── SKILL.md              # required
└── references/           # optional, loaded on demand
```

`SKILL.md` needs YAML frontmatter with `name` and `description`. The description is what Claude matches against a user's request, so write it as concrete phrases people actually say:

```yaml
---
name: your-skill
description: >
  This skill should be used when the user asks to "do the thing",
  "do the other thing", or needs X.
---
```

Then write the body as numbered steps. Keep reference material in `references/` and link to it from the body — it loads only when needed, which keeps the skill itself cheap to match against.

If your skill can cause a write, state the gate explicitly as its own numbered step. Every skill here does.
