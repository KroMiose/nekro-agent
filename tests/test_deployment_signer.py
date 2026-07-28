import hashlib
import hmac

from nekro_agent.services.deployment.signer import build_signature_headers


def test_build_signature_headers_is_predictable_with_fixed_inputs() -> None:
    token = b"fixed-token"
    body = b'{"channel":"stable"}'
    timestamp = "1781020800000"
    nonce = "40d2c11d7f6f4e43a87486f2044613f1"
    plaintext = "\n".join(
        [
            "POST",
            "/v1/jobs/update",
            timestamp,
            nonce,
            hashlib.sha256(body).hexdigest(),
        ]
    )
    expected = "v1=" + hmac.new(token, plaintext.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = build_signature_headers(
        token=token,
        instance_id="sha256:test",
        method="post",
        path_with_query="/v1/jobs/update",
        body=body,
        timestamp=timestamp,
        nonce=nonce,
    )

    assert headers == {
        "X-NA-Instance": "sha256:test",
        "X-NA-Timestamp": timestamp,
        "X-NA-Nonce": nonce,
        "X-NA-Signature": expected,
    }


def test_build_signature_headers_hashes_empty_body() -> None:
    token = b"fixed-token"
    timestamp = "1781020800000"
    nonce = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    plaintext = "\n".join(
        [
            "GET",
            "/v1/capabilities",
            timestamp,
            nonce,
            hashlib.sha256(b"").hexdigest(),
        ]
    )
    expected = "v1=" + hmac.new(token, plaintext.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = build_signature_headers(
        token=token,
        instance_id="sha256:test",
        method="GET",
        path_with_query="/v1/capabilities",
        timestamp=timestamp,
        nonce=nonce,
    )

    assert headers["X-NA-Signature"] == expected


def test_build_signature_headers_includes_query_in_path() -> None:
    token = b"fixed-token"
    timestamp = "1781020800000"
    nonce = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    plaintext = "\n".join(
        [
            "GET",
            "/v1/jobs/upd_1/logs?after_seq=10&limit=20",
            timestamp,
            nonce,
            hashlib.sha256(b"").hexdigest(),
        ]
    )
    expected = "v1=" + hmac.new(token, plaintext.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = build_signature_headers(
        token=token,
        instance_id="sha256:test",
        method="GET",
        path_with_query="/v1/jobs/upd_1/logs?after_seq=10&limit=20",
        timestamp=timestamp,
        nonce=nonce,
    )

    assert headers["X-NA-Signature"] == expected

