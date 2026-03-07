from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from sls.config.settings import Settings
from sls.core.errors import (
    ApiBadRequestError,
    ApiServerError,
    ApiTimeoutError,
    ApiUnauthorizedError,
    NonRetryableError,
    RateLimitError,
)
from sls.core.normalize import normalize_email, normalize_phone, normalize_text


@dataclass
class CloseConnector:
    api_key: str
    base_url: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "CloseConnector":
        if not settings.close_api_key:
            raise ApiUnauthorizedError("Missing CLOSE_API_KEY in environment")
        return cls(
            api_key=settings.close_api_key,
            base_url=settings.close_base_url,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def ping(self) -> dict[str, str]:
        if not self.api_key.strip():
            raise ApiUnauthorizedError("Empty CLOSE_API_KEY")

        if not self.base_url.startswith("https://"):
            raise NonRetryableError("CLOSE_BASE_URL must start with https://")

        return {
            "status": "ok",
            "message": "Close connector configuration looks valid",
            "base_url": self.base_url,
        }

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                timeout=15,
            )
        except requests.Timeout as e:
            raise ApiTimeoutError("Close API request timed out") from e
        except requests.RequestException as e:
            raise ApiServerError(f"Close API request failed: {type(e).__name__}") from e

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_value = float(retry_after) if retry_after else None
            raise RateLimitError("Close API rate limited", retry_after=retry_after_value)

        if response.status_code in (401, 403):
            raise ApiUnauthorizedError(f"Close API auth failed with status {response.status_code}")

        if 400 <= response.status_code < 500:
            raise ApiBadRequestError(f"Close API client error {response.status_code}")

        if 500 <= response.status_code < 600:
            raise ApiServerError(f"Close API server error {response.status_code}")

        return response.json()

    def search_contact(
        self,
        *,
        external_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> dict[str, Any]:
        """
        First real read-only Close API skeleton.
        Uses whichever identifier is available first.
        """

        ext = normalize_text(external_id)
        em = normalize_email(email)
        ph = normalize_phone(phone)

        query_value = ext or em or ph
        query_type = "external_id" if ext else "email" if em else "phone" if ph else None

        if not query_value or not query_type:
            return {
                "query_type": None,
                "query_value_present": False,
                "found": False,
                "count": 0,
                "data_preview": [],
                "note": "No usable identifier provided for Close search.",
            }

        # Safe starter approach: plain GET against lead endpoint with a simple query param.
        # This is still a skeleton and may need adjustment when we wire the exact Close search behavior.
        payload = self._request(
            "GET",
            "/lead/",
            params={"query": query_value},
        )

        data = payload.get("data", []) if isinstance(payload, dict) else []

        return {
            "query_type": query_type,
            "query_value_present": True,
            "found": len(data) > 0,
            "count": len(data),
            "data_preview": [
                {
                    "id": item.get("id"),
                    "display_name": item.get("display_name"),
                }
                for item in data[:5]
                if isinstance(item, dict)
            ],
        }

    def plan_contact(
        self,
        contact: dict,
        *,
        seen_external_ids: set[str] | None = None,
        seen_emails: set[str] | None = None,
        seen_phones: set[str] | None = None,
    ) -> dict:
        external_id = normalize_text(contact.get("external_id"))
        email = normalize_email(contact.get("email"))
        phone = normalize_phone(contact.get("phone"))

        seen_external_ids = seen_external_ids or set()
        seen_emails = seen_emails or set()
        seen_phones = seen_phones or set()

        if external_id and external_id in seen_external_ids:
            return {
                "external_id": external_id,
                "action": "would_update_by_external_id",
                "reason": "match_external_id_in_planner",
            }

        if email and email in seen_emails:
            return {
                "external_id": external_id,
                "action": "would_match_by_email",
                "reason": "match_email_in_planner",
            }

        if phone and phone in seen_phones:
            return {
                "external_id": external_id,
                "action": "would_match_by_phone",
                "reason": "match_phone_in_planner",
            }

        return {
            "external_id": external_id,
            "action": "would_create",
            "reason": "no_match_in_planner",
        }