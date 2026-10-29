"""Visitor pass codes: an unforgeable reference to one visit, rendered as a QR code.

Format: ``VP1-`` + Base32(visit_id (16 bytes) || HMAC-SHA256(pass_key, visit_id)[:16]).

- Contains no personal data: a screenshot of the QR code reveals only an opaque identifier.
- Cannot be forged or enumerated without the server key (128-bit MAC).
- Deterministic: the same visit always yields the same pass, so it can be displayed again
  later without storing it. Whether it admits the visitor is decided by the normal
  check-in rules (status and date), so cancelling a visit also invalidates its pass.
- Upper-case Base32 plus ``-`` fits the QR alphanumeric mode and is case-insensitive,
  which suits keyboard-emulating handheld scanners.
"""

import base64
import binascii
import hashlib
import hmac
import uuid

PASS_PREFIX = "VP1-"  # noqa: S105 - format/version marker, not a secret
_MAC_BYTES = 16
_ENCODED_LENGTH = 52  # Base32 of 32 bytes, without padding.
MAX_PASS_CODE_LENGTH = 100  # Upper bound accepted from clients before any parsing.

# Domain separation: the pass key is derived from the application secret, so a MAC computed
# for a pass can never be confused with an access-token signature made with the same secret.
_KEY_CONTEXT = b"vmp/visitor-pass/v1"


class VisitorPassCodec:
    def __init__(self, secret: str) -> None:
        self._key = hmac.new(secret.encode(), _KEY_CONTEXT, hashlib.sha256).digest()

    def encode(self, visit_id: uuid.UUID) -> str:
        raw = visit_id.bytes + self._mac(visit_id.bytes)
        return PASS_PREFIX + base64.b32encode(raw).decode("ascii").rstrip("=")

    def decode(self, code: str) -> uuid.UUID | None:
        """Returns the visit id of a genuine pass, or None for anything else."""
        candidate = code.strip().upper()
        if not candidate.startswith(PASS_PREFIX):
            return None
        body = candidate.removeprefix(PASS_PREFIX)
        if len(body) != _ENCODED_LENGTH:
            return None
        try:
            raw = base64.b32decode(body + "====")
        except (binascii.Error, ValueError):
            return None
        visit_id = uuid.UUID(bytes=raw[:16])
        # Re-encoding rejects non-canonical spellings; compare_digest avoids a timing oracle.
        if not hmac.compare_digest(self.encode(visit_id), candidate):
            return None
        return visit_id

    def _mac(self, message: bytes) -> bytes:
        return hmac.new(self._key, message, hashlib.sha256).digest()[:_MAC_BYTES]
