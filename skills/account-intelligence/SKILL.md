---
name: account-intelligence
description: >
  Use when the user asks to "research an account", "get account 360", "source ICP
  companies", "rank accounts", "find the best contact at", "who should I talk to at",
  or asks whether a company is worth pursuing. Also use when a domain or company name
  is supplied with no further instruction and the intent is evaluation rather than
  outreach.
---

# Account intelligence

1. Search the CRM by domain before enriching anything. The CRM connector is
   user-supplied and may not be configured — if it is absent, say so, skip to
   step 3, and label every result partial for the rest of the run.
2. With a CRM: call `crm_get_account_360` when available, otherwise compose
   `search_records` and `get_record` and label the result partial. Never fill a
   missing CRM field from Clay and present it as a CRM record.
3. Use Clay only to fill missing facts. Require source URLs for coding-agent, open-source, AI-tooling, and developer-workflow evidence.
4. Pass candidate accounts to `gtm_score_icp_accounts`, then `gtm_rank_team_adoption` when product-usage fields exist.
5. Pass people to `gtm_rank_best_contact`.
6. Preserve every uncertainty. Do not convert absence of evidence into a negative claim.
7. Return a ranked account summary with evidence, missing fields, and recommended next research step.

Read `references/criteria.md` when scoring or explaining ICP fit.
