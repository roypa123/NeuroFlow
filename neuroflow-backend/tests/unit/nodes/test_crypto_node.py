from __future__ import annotations

import hashlib
import hmac

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.crypto_node import CryptoNode


async def test_hash_action_produces_expected_sha256() -> None:
    node = CryptoNode()
    items = [Item(json={"secret": "hello"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "action": "hash",
            "algorithm": "sha256",
            "inputField": "secret",
            "destinationField": "hashed",
        },
    )

    result = await node.execute(ctx)

    expected = hashlib.sha256(b"hello").hexdigest()
    assert result["main"][0][0].json_["hashed"] == expected


async def test_hmac_action_produces_expected_signature() -> None:
    node = CryptoNode()
    items = [Item(json={"body": "payload"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "action": "hmac",
            "algorithm": "sha256",
            "inputField": "body",
            "secretField": "shh",
            "destinationField": "sig",
        },
    )

    result = await node.execute(ctx)

    expected = hmac.new(b"shh", b"payload", digestmod="sha256").hexdigest()
    assert result["main"][0][0].json_["sig"] == expected


async def test_base64_round_trip() -> None:
    node = CryptoNode()
    items = [Item(json={"text": "hello world"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "action": "base64Encode",
            "inputField": "text",
            "destinationField": "encoded",
        },
    )
    encoded = (await node.execute(ctx))["main"][0][0].json_["encoded"]

    decode_items = [Item(json={"text": encoded})]
    decode_ctx = NodeExecutionContext(
        input_items=decode_items,
        params={
            "action": "base64Decode",
            "inputField": "text",
            "destinationField": "decoded",
        },
    )
    result = await node.execute(decode_ctx)

    assert result["main"][0][0].json_["decoded"] == "hello world"


async def test_random_string_respects_length_and_uniqueness() -> None:
    node = CryptoNode()
    ctx = NodeExecutionContext(
        input_items=[],
        params={"action": "randomString", "length": 16, "destinationField": "token"},
    )

    result1 = (await node.execute(ctx))["main"][0][0].json_["token"]
    result2 = (await node.execute(ctx))["main"][0][0].json_["token"]

    assert len(result1) == 16
    assert result1 != result2
