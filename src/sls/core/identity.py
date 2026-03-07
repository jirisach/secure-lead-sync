from __future__ import annotations

import hashlib

def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def lead_fingerprint(external_id: str | None, email_norm: str | None, phone_norm: str | None) -> str:
    # stable-ish identifier for logs/audit WITHOUT PII
    base = f"ext={external_id or ''}|em={email_norm or ''}|ph={phone_norm or ''}"
    return sha256_hex(base)