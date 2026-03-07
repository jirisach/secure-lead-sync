from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    close_api_key: str | None
    close_base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            close_api_key=os.getenv("CLOSE_API_KEY"),
            close_base_url=os.getenv("CLOSE_BASE_URL", "https://api.close.com/api/v1"),
        )