from __future__ import annotations

from sls.core.errors import ApiServerError


class FakeApiClient:
    def __init__(self) -> None:
        self.calls = 0

    def send_contact(self) -> dict[str, str]:
        self.calls += 1

        if self.calls < 3:
            raise ApiServerError(f"Temporary upstream failure on call {self.calls}")

        return {
            "status": "ok",
            "message": f"Success on call {self.calls}",
        }