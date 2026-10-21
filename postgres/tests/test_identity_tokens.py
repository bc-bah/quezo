import asyncio
import time

import httpx2 as httpx
import jwt
import pytest
from pydantic import ValidationError

from identity_helpers import SETTINGS, SUBJECT, SigningPeer
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.tokens import IdentitySettings, TokenVerifier, VerifiedIdentity

pytestmark = pytest.mark.anyio


@pytest.fixture
def peer() -> SigningPeer:
    return SigningPeer()


@pytest.mark.parametrize(("name", "value"), [
    ("iss", "http://attacker.invalid/realms/quezo-local"),
    ("aud", "quezo-web"), ("aud", []), ("aud", None),
    ("sub", ""), ("sub", " "), ("sub", "\x00"), ("sub", 23), ("sub", "x" * 256),
    ("exp", 0), ("exp", "9999999999"), ("exp", True), ("exp", []),
    ("iat", 0), ("iat", "12"), ("iat", True), ("iat", []),
    ("nbf", 9999999999), ("nbf", "0"), ("nbf", []),
    ("typ", "ID"), ("typ", None),
])
async def test_invalid_claims_denied(peer: SigningPeer, name: str, value: object) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(peer.serve)) as client:
        verifier = TokenVerifier(SETTINGS, client)
        with pytest.raises(ApiError) as error:
            await verifier.verify(peer.token({**peer.claims(), name: value}))
        assert error.value.code == ErrorCode.UNAUTHENTICATED


@pytest.mark.parametrize("name", ["iss", "aud", "sub", "exp", "iat", "typ"])
async def test_required_claims(peer: SigningPeer, name: str) -> None:
    claims = peer.claims()
    del claims[name]
    async with httpx.AsyncClient(transport=httpx.MockTransport(peer.serve)) as client:
        with pytest.raises(ApiError) as error:
            await TokenVerifier(SETTINGS, client).verify(peer.token(claims))
        assert error.value.code == ErrorCode.UNAUTHENTICATED


@pytest.mark.parametrize("variant", [
    "signature", "none", "hs256", "rs512", "jku", "x5u", "jwk", "crit",
    "missing-kid", "malformed", "oversize", "unicode",
])
async def test_signature_algorithm_and_header_policy(peer: SigningPeer, variant: str) -> None:
    token = peer.token()
    if variant == "signature":
        token = SigningPeer().token()
    elif variant == "none":
        token = jwt.encode(peer.claims(), "", algorithm="none", headers={"kid": peer.kid})
    elif variant == "hs256":
        token = jwt.encode(peer.claims(), "synthetic-key" * 8, algorithm="HS256", headers={"kid": peer.kid})
    elif variant == "rs512":
        token = jwt.encode(peer.claims(), peer.private, algorithm="RS512", headers={"kid": peer.kid})
    elif variant in {"jku", "x5u", "jwk", "crit"}:
        token = peer.token(None, **{variant: "http://attacker.invalid/key"})
    elif variant == "missing-kid":
        token = jwt.encode(peer.claims(), peer.private, algorithm="RS256")
    elif variant == "malformed":
        token = "not.a.jwt"
    elif variant == "oversize":
        token = "x" * 32769
    elif variant == "unicode":
        token = "\u00e9"
    async with httpx.AsyncClient(transport=httpx.MockTransport(peer.serve)) as client:
        with pytest.raises(ApiError) as error:
            await TokenVerifier(SETTINGS, client).verify(token)
        assert error.value.code == ErrorCode.UNAUTHENTICATED
    assert peer.requests == (1 if variant == "signature" else 0)


async def test_expiry_and_lifetime_boundaries(peer: SigningPeer) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(peer.serve)) as client:
        verifier = TokenVerifier(SETTINGS, client)
        assert await verifier.verify(peer.token()) == VerifiedIdentity(SETTINGS.issuer, SUBJECT)
        now = int(time.time())
        for iat, exp in [(now, now + 301), (now + 10, now + 20), (now, now), (now - 20, now - 1)]:
            with pytest.raises(ApiError) as error:
                await verifier.verify(peer.token({**peer.claims(), "iat": iat, "exp": exp}))
            assert error.value.code == ErrorCode.UNAUTHENTICATED


async def test_rotation_cache_unknown_keys_and_single_flight(peer: SigningPeer) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(peer.serve)) as client:
        verifier = TokenVerifier(SETTINGS, client)
        token = peer.token()
        await asyncio.gather(*(verifier.verify(token) for _ in range(20)))
        assert peer.requests == 1
        for number in range(20):
            with pytest.raises(ApiError) as error:
                await verifier.verify(peer.token(kid=f"unknown-{number}"))
            assert error.value.code == ErrorCode.UNAUTHENTICATED
        assert peer.requests == 1
        old_token = token
        peer.private = SigningPeer().private
        peer.kid = "rotated"
        verifier._refresh_after = 0
        await verifier.verify(peer.token())
        assert peer.requests == 2
        with pytest.raises(ApiError) as error:
            await verifier.verify(old_token)
        assert error.value.code == ErrorCode.UNAUTHENTICATED
        peer.status = 503
        # Valid cached keys remain usable, but never beyond the configured TTL.
        await verifier.verify(peer.token())
        verifier._expires_at = verifier._refresh_after = 0
        for _ in range(3):
            with pytest.raises(ApiError) as error:
                await verifier.verify(peer.token())
            assert error.value.code == ErrorCode.DEPENDENCY_UNAVAILABLE
        assert peer.requests == 3
        peer.status = 200
        verifier._refresh_after = 0
        await verifier.verify(peer.token())


@pytest.mark.parametrize("variant", [
    "status", "redirect", "network", "timeout", "json", "oversize", "no-keys",
    "too-many", "duplicate", "invalid-key", "weak-key", "private-key",
])
async def test_dependency_failures_are_bounded_and_explicit(peer: SigningPeer, variant: str) -> None:
    async def serve(request: httpx.Request) -> httpx.Response:
        if variant == "network":
            raise httpx.ConnectError("synthetic-secret", request=request)
        if variant == "timeout":
            await asyncio.sleep(1)
        if variant == "status":
            return httpx.Response(503)
        if variant == "redirect":
            return httpx.Response(302, headers={"Location": "http://attacker.invalid/"})
        if variant == "json":
            return httpx.Response(200, content="not-json")
        if variant == "oversize":
            return httpx.Response(200, content=b" " * 65537)
        keys: list[object] = [peer.jwk()]
        if variant == "no-keys":
            keys = []
        if variant == "too-many":
            keys *= 33
        if variant == "duplicate":
            keys *= 2
        if variant == "invalid-key":
            keys = [{**peer.jwk(), "n": "!"}]
        if variant == "weak-key":
            keys = [{**peer.jwk(), "n": "AQAB"}]
        if variant == "private-key":
            keys = [{**peer.jwk(), "d": "private"}]
        return httpx.Response(200, json={"keys": keys})

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        verifier = TokenVerifier(SETTINGS.model_copy(update={"timeout": 0.02}), client)
        with pytest.raises(ApiError) as error:
            await verifier.verify(peer.token())
        assert error.value.code == ErrorCode.DEPENDENCY_UNAVAILABLE
        assert "synthetic-secret" not in str(error.value)


async def test_cancellation_releases_refresh_lock(peer: SigningPeer) -> None:
    started = asyncio.Event()

    async def serve(request: httpx.Request) -> httpx.Response:
        started.set()
        await asyncio.sleep(10)
        return peer.serve(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        verifier = TokenVerifier(SETTINGS, client)
        task = asyncio.create_task(verifier.verify(peer.token()))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not verifier._lock.locked()


@pytest.mark.parametrize("values", [
    {"issuer": "http://external.invalid/realms/test"},
    {"issuer": "http://user:pass@localhost/realms/test"},
    {"issuer": "http://localhost/realms/test?url=evil"},
    {"issuer": "http://localhost/realms/test/"},
    {"audience": ""}, {"timeout": 0}, {"timeout": float("nan")},
    {"cache_seconds": 601}, {"refresh_seconds": 0}, {"max_lifetime": 901},
])
async def test_configuration_rejects_unsafe_values(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        IdentitySettings.model_validate({**SETTINGS.model_dump(), **values})
