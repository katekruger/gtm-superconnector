---
name: reconciling-clay-snapshots
description: >
  Use when the user asks to "reconcile Clay", "diff the user snapshot", "sync users",
  "check schema drift", or asks what changed between two exports. Also use when
  deduplication and upsert behavior are being confused, or when a row count is being
  read as an update count.
---

# Reconciling Clay snapshots

1. Obtain the latest complete product user snapshot and current Clay rows without changing either system.
2. Use `user_id` as the default reconciliation key.
3. Call `gtm_reconcile_clay_snapshot` with both complete datasets.
4. Report inserts, field-level updates, unchanged rows, missing incoming records, missing IDs, and schema drift separately.
5. Treat deduplication as duplicate suppression only; do not claim existing rows were updated without evidence.
6. Stop at the dry run. Require explicit approval before publication, upload, or write-back.
