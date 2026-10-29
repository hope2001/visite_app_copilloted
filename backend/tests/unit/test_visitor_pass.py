import base64
import uuid
from collections.abc import Callable

import pytest

from app.core.visitor_pass import PASS_PREFIX, VisitorPassCodec

SECRET = "unit-test-secret-0123456789-abcdefghij"
VISIT_ID = uuid.UUID("0b5a3f0e-6a4c-4e7b-9d1f-2c8e5a7b9d10")
QR_ALPHANUMERIC = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:")
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


@pytest.fixture
def codec() -> VisitorPassCodec:
    return VisitorPassCodec(SECRET)


def test_round_trip(codec: VisitorPassCodec) -> None:
    assert codec.decode(codec.encode(VISIT_ID)) == VISIT_ID


def test_code_is_compact_qr_alphanumeric_and_stable(codec: VisitorPassCodec) -> None:
    code = codec.encode(VISIT_ID)

    assert code.startswith(PASS_PREFIX)
    assert len(code) == len(PASS_PREFIX) + 52
    assert set(code) <= QR_ALPHANUMERIC
    assert code == VisitorPassCodec(SECRET).encode(VISIT_ID)


def test_each_visit_gets_a_unique_code(codec: VisitorPassCodec) -> None:
    codes = {codec.encode(uuid.uuid4()) for _ in range(500)}
    assert len(codes) == 500


def test_scanner_noise_is_tolerated(codec: VisitorPassCodec) -> None:
    code = codec.encode(VISIT_ID)
    assert codec.decode(f"  {code.lower()}\n") == VISIT_ID


def _flip_last_mac_bit(code: str) -> str:
    raw = bytearray(base64.b32decode(code.removeprefix(PASS_PREFIX) + "===="))
    raw[-1] ^= 0x01
    return PASS_PREFIX + base64.b32encode(bytes(raw)).decode().rstrip("=")


def _with_visit_id(code: str, visit_id: uuid.UUID) -> str:
    raw = base64.b32decode(code.removeprefix(PASS_PREFIX) + "====")
    return PASS_PREFIX + base64.b32encode(visit_id.bytes + raw[16:]).decode().rstrip("=")


def _flip_unused_bit(code: str) -> str:
    last = BASE32_ALPHABET.index(code[-1])
    return code[:-1] + BASE32_ALPHABET[last ^ 1]


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(_flip_last_mac_bit, id="altered-mac"),
        pytest.param(lambda code: _with_visit_id(code, uuid.uuid4()), id="swapped-visit-id"),
        pytest.param(lambda code: "VP2-" + code.removeprefix(PASS_PREFIX), id="wrong-prefix"),
        pytest.param(lambda code: code[:-1], id="truncated"),
        pytest.param(lambda code: code + "A", id="extended"),
        pytest.param(lambda code: code[:-1] + "1", id="not-base32"),
        # The last Base32 character carries 4 unused bits; other spellings are not accepted.
        pytest.param(_flip_unused_bit, id="non-canonical"),
        pytest.param(lambda code: code.removeprefix(PASS_PREFIX), id="no-prefix"),
        pytest.param(lambda code: "", id="empty"),
    ],
)
def test_tampered_or_malformed_codes_are_rejected(
    codec: VisitorPassCodec, tamper: Callable[[str], str]
) -> None:
    assert codec.decode(tamper(codec.encode(VISIT_ID))) is None


def test_pass_from_another_deployment_is_rejected(codec: VisitorPassCodec) -> None:
    foreign = VisitorPassCodec("another-secret-9876543210-zyxwvutsrq").encode(VISIT_ID)
    assert codec.decode(foreign) is None


def test_code_reveals_only_the_visit_id(codec: VisitorPassCodec) -> None:
    raw = base64.b32decode(codec.encode(VISIT_ID).removeprefix(PASS_PREFIX) + "====")
    assert raw[:16] == VISIT_ID.bytes
    assert len(raw) == 32
