import re
from collections.abc import Mapping, Sequence

SENSITIVE_KEYS = ("password", "secret", "token", "authorization", "api_key", "account")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{8,19}(?!\d)")
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if any(marker in str(key).lower() for marker in SENSITIVE_KEYS)
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        cleaned = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
        cleaned = LONG_NUMBER_PATTERN.sub("[REDACTED_NUMBER]", cleaned)
        cleaned = BEARER_PATTERN.sub("Bearer [REDACTED]", cleaned)
        return cleaned[:2_000]
    return value
