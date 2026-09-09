"""Crypto -- hashing, HMAC, base64, and random tokens via the stdlib only
(`hashlib`/`hmac`/`base64`/`secrets`). See docs/13-node-catalog-and-sdk.md
#13.5. Named `crypto_node.py` (not `crypto.py`) so it can't be confused
with `app/core/crypto.py` (envelope encryption for credentials/variables,
an unrelated module this node never touches). `secretField` is a plain
string parameter, not a credential -- matching this app's own documented
answer for a generic hashing utility (n8n's own Crypto node takes a plain
secret parameter the same way); anything that genuinely needs secret
storage/redaction belongs on a Credential or a secret Variable instead."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as secrets_module

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    DisplayOptions,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)

_ALGORITHMS = ("md5", "sha1", "sha256", "sha512")


class CryptoNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.crypto",
        version=1,
        name="Crypto",
        group="data",
        category="Core",
        description="Hashes, signs, encodes, or generates random values.",
        icon="lock-keyhole",
        color="cat-data",
        aliases=["hash", "hmac", "base64"],
        subtitle="={{ $parameter.action }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="action",
                display_name="Action",
                type="options",
                default="hash",
                description="What to do with the input field's value.",
                options=[
                    PropertyOption(label="Hash", value="hash"),
                    PropertyOption(label="HMAC", value="hmac"),
                    PropertyOption(label="Base64 Encode", value="base64Encode"),
                    PropertyOption(label="Base64 Decode", value="base64Decode"),
                    PropertyOption(label="Random String", value="randomString"),
                ],
            ),
            NodeProperty(
                name="algorithm",
                display_name="Algorithm",
                type="options",
                default="sha256",
                description="Hash algorithm used for Hash/HMAC.",
                options=[PropertyOption(label=a.upper(), value=a) for a in _ALGORITHMS],
                display_options=DisplayOptions(show={"action": ["hash", "hmac"]}),
            ),
            NodeProperty(
                name="secretField",
                display_name="Secret",
                type="string",
                description="Plain-text HMAC key. Not a credential -- use a "
                "Credential or secret Variable if this value itself is sensitive.",
                display_options=DisplayOptions(show={"action": ["hmac"]}),
            ),
            NodeProperty(
                name="inputField",
                display_name="Input Field",
                type="string",
                required=True,
                description="Field on each input item to read the value from.",
                display_options=DisplayOptions(
                    show={"action": ["hash", "hmac", "base64Encode", "base64Decode"]}
                ),
            ),
            NodeProperty(
                name="length",
                display_name="Length",
                type="number",
                default=32,
                description="Number of hex characters to generate.",
                display_options=DisplayOptions(show={"action": ["randomString"]}),
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="result",
                required=True,
                description="Field on the output item to write the result to.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        action = params.get("action", "hash")
        destination = params.get("destinationField", "result")
        algorithm = params.get("algorithm", "sha256")

        if action == "randomString":
            length = max(1, int(params.get("length", 32)))
            random_value = secrets_module.token_hex(length)[:length]
            return {"main": [[Item(json={destination: random_value})]]}

        input_field = params.get("inputField", "")
        results: list[Item] = []
        for item in ctx.input_items:
            raw = str(item.json_.get(input_field, ""))
            value: str
            if action == "hash":
                value = hashlib.new(algorithm, raw.encode()).hexdigest()
            elif action == "hmac":
                secret = str(params.get("secretField", ""))
                value = hmac.new(
                    secret.encode(), raw.encode(), digestmod=algorithm
                ).hexdigest()
            elif action == "base64Encode":
                value = base64.b64encode(raw.encode()).decode()
            else:  # base64Decode
                value = base64.b64decode(raw.encode()).decode()
            results.append(Item(json={**item.json_, destination: value}))
        return {"main": [results]}
