"""GTM MCP server.

Deterministic, read-only GTM tooling exposed over the Model Context Protocol:
ICP scoring, contact ranking, email-readiness classification, snapshot
reconciliation, activation analysis, campaign previews, and guarded n8n
operations.

Every tool in this package is preview-only by default. The single tool capable
of a remote write (`n8n_retry_execution`) requires both an explicit workflow
allowlist and `confirm=true`.
"""

__version__ = "0.2.0"
