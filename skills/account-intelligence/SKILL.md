---
name: account-intelligence
description: >
  This skill should be used when the user asks to "research an account", "get account 360",
  "source ICP companies", "rank accounts", "find the best contact", or evaluate a company for outreach.
---

# Account intelligence

1. Search the CRM by domain before enriching anything.
2. Call `crm_get_account_360` when available. Otherwise compose `search_records` and `get_record`, and label the result partial.
3. Use Clay only to fill missing facts. Require source URLs for coding-agent, open-source, AI-tooling, and developer-workflow evidence.
4. Pass candidate accounts to `gtm_score_icp_accounts`, then `gtm_rank_team_adoption` when product-usage fields exist.
5. Pass people to `gtm_rank_best_contact`.
6. Preserve every uncertainty. Do not convert absence of evidence into a negative claim.
7. Return a ranked account summary with evidence, missing fields, and recommended next research step.

Read `references/criteria.md` when scoring or explaining ICP fit.
