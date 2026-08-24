from __future__ import annotations

import os
from typing import Any

import httpx


class N8nOps:
    def __init__(self) -> None:
        self.base = os.getenv("N8N_BASE_URL", "http://127.0.0.1:5678").rstrip("/")
        self.key = os.getenv("N8N_API_KEY", "")
        self.approved = {x.strip() for x in os.getenv("N8N_APPROVED_WORKFLOW_IDS", "").split(",") if x.strip()}

    def _headers(self) -> dict[str, str]:
        if not self.key:
            raise ValueError("N8N_API_KEY is not configured.")
        return {"X-N8N-API-KEY": self.key}

    def _check(self, workflow_id: str, *, write: bool = False) -> None:
        if self.approved and workflow_id not in self.approved:
            raise ValueError(f"Workflow {workflow_id} is not in N8N_APPROVED_WORKFLOW_IDS.")
        if write and not self.approved:
            raise ValueError("Retries are disabled until N8N_APPROVED_WORKFLOW_IDS is configured.")

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, f"{self.base}{path}", headers=self._headers(), **kwargs)
            response.raise_for_status()
            return response.json()

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base}/healthz")
            return {"reachable": response.is_success, "status_code": response.status_code, "body": response.json() if response.is_success else None, "api_key_configured": bool(self.key), "approved_workflow_count": len(self.approved)}
