---
name: debugging-n8n-workflows
description: >
  Use when the user asks to "debug n8n", "inspect a workflow failure", "why did this
  workflow fail", "dry run a workflow", "retry an execution", or wants the
  last-known-good output for a workflow. Also use when an automation has silently
  stopped producing results.
---

# Debugging n8n workflows

1. Call `n8n_health` first.
2. Use only workflows returned by `n8n_list_approved_workflows`.
3. Validate workflow structure and preview the input before execution.
4. Inspect the failed execution and compare it with `n8n_last_known_good`.
5. Explain the likely cause with exact execution evidence.
6. Call `n8n_retry_execution` with `confirm=false` to show the retry preview.
7. Retry only after explicit approval naming the execution ID, workflow ID, and whether to load the latest saved workflow.
