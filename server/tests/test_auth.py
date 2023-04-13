import base64
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from jwt import PyJWK

from app.api import auth
from app.api.auth import authenticate
from app.core.config import settings

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio

SIGNING_KEY = {
    "kty": "oct",
    "alg": "HS256",  # use HS256 for simplicity
    "k": base64.urlsafe_b64encode(b"secret"),
    "kid": "abc123",
}
KEY_SET = {"keys": [SIGNING_KEY]}
TOKEN_PAYLOAD = {
    "oid": "faf2ebc2-fe58-4ab8-bb70-ad82c9e2f44d",
    "iss": auth.ISSUERS["2.0"],
    "aud": settings.APP_CLIENT_ID,
    "exp": int(time.time()) + 600,
    "ver": "2.0",
}


async def generate_token(payload=None, kid=SIGNING_KEY["kid"]):
    if not payload:
        payload = TOKEN_PAYLOAD
    key = PyJWK.from_dict(SIGNING_KEY)
    return jwt.encode(payload, key.key, algorithm="HS256", headers={"kid": kid})


async def generate_request(token=None):
    if not token:
        token = await generate_token()

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return MagicMock(headers=headers)


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_success(mock_fetch_data):
    """Test a request that should auth successfully."""
    request = await generate_request()
    oid = await authenticate(request)
    assert oid == TOKEN_PAYLOAD["oid"]


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_no_request_headers(mock_fetch_data):
    """Test using a request with no auth header."""
    request = MagicMock(headers={})

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing or invalid auth token."


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_bad_issuer(mock_fetch_data):
    """Test using a token with a bad/unknown issuer."""
    token = await generate_token(TOKEN_PAYLOAD | {"iss": "bad_issuer"})
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Invalid issuer." in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_expired_token(mock_fetch_data):
    """Test using an expired token."""
    token = await generate_token(TOKEN_PAYLOAD | {"exp": 1581049078})
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Signature has expired." in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_token_missing_exp(mock_fetch_data):
    """Test using a token that's missing exp (expiration) claim."""
    payload = TOKEN_PAYLOAD.copy()
    payload.pop("exp")
    token = await generate_token(payload)
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert 'Token is missing the "exp" claim.' in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_bad_token(mock_fetch_data):
    """Test using a token that can't be decoded."""
    token = "abc123"
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Failed to parse auth token" in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_invalid_key_id(mock_fetch_data):
    """Test using a token signed with an invalid key."""
    token = await generate_token(kid="def234")
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Unable to find a signing key that matches" in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_missing_oid(mock_fetch_data):
    """Test using a token without an oid."""
    payload = TOKEN_PAYLOAD.copy()
    payload.pop("oid")
    token = await generate_token(payload)
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Missing or invalid oid" in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_v1_token_version(mock_fetch_data):
    """Test using a v1 token."""
    payload = TOKEN_PAYLOAD.copy()
    payload["ver"] = "1.0"
    payload["iss"] = auth.ISSUERS["1.0"]
    payload["aud"] = f"api://{settings.APP_CLIENT_ID}"
    token = await generate_token(payload)
    request = await generate_request(token)

    oid = await authenticate(request)
    assert oid == TOKEN_PAYLOAD["oid"]


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_missing_token_version(mock_fetch_data):
    """Test using a token without a ver."""
    payload = TOKEN_PAYLOAD.copy()
    payload.pop("ver")
    token = await generate_token(payload)
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert 'Token is missing the "ver" claim' in exc.value.detail


@patch("app.api.auth.ALGORITHMS", ["HS256"])
@patch("jwt.PyJWKClient.fetch_data", return_value=KEY_SET)
async def test_authenticate_invalid_token_version(mock_fetch_data):
    """Test using a token with an invalid ver."""
    payload = TOKEN_PAYLOAD.copy()
    payload["ver"] = "3"
    token = await generate_token(payload)
    request = await generate_request(token)

    with pytest.raises(HTTPException) as exc:
        await authenticate(request)
    assert exc.value.status_code == 401
    assert "Invalid/missing token version" in exc.value.detail
