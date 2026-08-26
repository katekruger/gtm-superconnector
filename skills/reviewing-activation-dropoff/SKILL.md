---
name: reviewing-activation-dropoff
description: >
  Use when the user asks to "find activation drop-off", "analyze inactive users",
  "find users without repositories", "who installed but never used it", or asks which
  users are missing a proof moment. Also use when an activation or retention number
  needs explaining rather than reporting.
---

# Reviewing activation drop-off

1. Obtain the latest complete user dataset rather than a partial contact export.
2. Call `gtm_detect_activation_dropoff` with the requested inactivity window.
3. Separate installed-without-repository, history-then-inactive, and no-meaningful-proof-moment cohorts.
4. Rank cohorts by recency, account concentration, and potential sponsor value when those fields exist.
5. Return cohort counts, representative records, missing instrumentation, and recommended follow-up.
6. Do not send messages or change lifecycle stages without explicit approval.
