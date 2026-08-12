from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError


def test_hash_password_and_verify_it() -> None:
    plain_password = "strong-test-password"

    hashed_password = hash_password(plain_password)

    assert hashed_password != plain_password
    assert verify_password(plain_password, hashed_password) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed_password = hash_password("correct-password")

    assert verify_password("wrong-password", hashed_password) is False


def test_same_password_produces_different_hashes() -> None:
    plain_password = "same-password"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != second_hash
    assert verify_password(plain_password, first_hash) is True
    assert verify_password(plain_password, second_hash) is True


def test_create_and_decode_access_token() -> None:
    user_id = uuid4()
    session_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        session_id=session_id,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_decode_access_token_rejects_invalid_signature() -> None:
    token = create_access_token(
        user_id=uuid4(),
        session_id=uuid4(),
    )

    header, payload, _signature = token.split(".")
    forged_token = f"{header}.{payload}.invalidsignature"

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged_token)


def test_decode_access_token_rejects_expired_token() -> None:
    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "type": "access",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ExpiredSignatureError):
        decode_access_token(token)


def test_generate_refresh_token_returns_unique_tokens() -> None:
    first_token = generate_refresh_token()
    second_token = generate_refresh_token()

    assert first_token != second_token
    assert len(first_token) >= 43
    assert len(second_token) >= 43


def test_hash_refresh_token_is_deterministic() -> None:
    token = generate_refresh_token()

    first_hash = hash_refresh_token(token)
    second_hash = hash_refresh_token(token)

    assert first_hash == second_hash
    assert first_hash != token
    assert len(first_hash) == 64
