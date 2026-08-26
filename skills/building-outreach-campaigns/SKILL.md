---
name: building-outreach-campaigns
description: >
  Use when the user asks to "build an outreach campaign", "prepare design partner
  outreach", "draft a campaign", "verify a contact", "find this person's email", or
  wants an Instantly-ready preview. Also use when a contact list is supplied and the
  stated intent is sending rather than research.
---

# Building outreach campaigns

1. Retrieve the existing CRM account and prior replies before generating new
   outreach. The CRM connector is user-supplied: if it is not configured, say so
   and continue without prior-contact history — but flag that the campaign cannot
   be checked against previous outreach, which is a real risk of duplicate sends.
2. Use `gtm_rank_best_contact` to rank candidates.
3. Use `gtm_resolve_contact_email` only when an address is missing. Keep paid verification and PDL disabled unless the user approves the cost-bearing tier.
4. Use `gtm_classify_email_readiness` for every selected address.
5. Treat only `verified` and `verified:commit` as send-ready. Quarantine inferred, catch-all, risky, personal, and unresolved addresses.
6. Use `gtm_build_enrichment_provenance` before recommending CRM write-back.
7. Use `gtm_preview_campaign_build` to produce a paused campaign plan.
8. Stop at preview. Require explicit approval before contact upload, CRM write-back, campaign creation, launch, or sending.

Read `references/approval-gates.md` before any requested write.
