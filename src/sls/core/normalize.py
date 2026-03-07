from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    e = email.strip().lower()
    return e if EMAIL_RE.match(e) else None

def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    p = phone.strip()
    # keep digits and leading +
    p = re.sub(r"[^\d+]", "", p)
    # convert 00 prefix to +
    if p.startswith("00"):
        p = "+" + p[2:]
    # if starts with +, keep, else just digits (simple)
    if p.startswith("+"):
        return p
    return re.sub(r"\D", "", p) or None

def normalize_text(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None