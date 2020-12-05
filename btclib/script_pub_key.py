#!/usr/bin/env python3

# Copyright (C) 2017-2020 The btclib developers
#
# This file is part of btclib. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution.
#
# No part of btclib including this file, may be copied, modified, propagated,
# or distributed except according to the terms contained in the LICENSE file.

"""ScriptPubKey functions.

"""

from typing import List, Optional, Tuple

from . import var_bytes
from .alias import Octets, Script, String
from .exceptions import BTClibValueError
from .hashes import hash160_from_key, hash160_from_script, hash256_from_script
from .script import serialize
from .to_pub_key import Key, pub_keyinfo_from_key
from .utils import bytes_from_octets, bytesio_from_binarydata

# 1. Hash/WitnessProgram from pub_key/script_pub_key

# hash160_from_key, hash160_from_script, and hash256_from_script
# are imported from hashes.py


# 2. script_pub_key from Hash/WitnessProgram and vice versa


def script_pub_key_from_payload(script_type: str, payload: Octets) -> bytes:
    "Return the script_pub_key for the provided script_type and payload."

    script_type = script_type.lower()

    if script_type == "p2ms":
        script_pub_key = bytes_from_octets(payload) + b"\xae"
        if not is_p2ms(script_pub_key):
            raise BTClibValueError("invalid p2ms payload")
        return script_pub_key

    if script_type == "nulldata":
        payload = bytes_from_octets(payload)
        if len(payload) > 80:
            err_msg = f"invalid nulldata script length: {len(payload)} bytes "
            raise BTClibValueError(err_msg)
        return serialize(["OP_RETURN", payload])

    if script_type == "p2pk":
        payload = bytes_from_octets(payload, (33, 65))
        # TODO: check it is a valid pub_key
        return serialize([payload, "OP_CHECKSIG"])

    if script_type == "p2wsh":
        payload = bytes_from_octets(payload, 32)
        return serialize([0, payload])

    if script_type == "p2pkh":
        payload = bytes_from_octets(payload, 20)
        return serialize(
            [
                "OP_DUP",
                "OP_HASH160",
                payload,
                "OP_EQUALVERIFY",
                "OP_CHECKSIG",
            ]
        )

    if script_type == "p2sh":
        payload = bytes_from_octets(payload, 20)
        return serialize(["OP_HASH160", payload, "OP_EQUAL"])

    if script_type == "p2wpkh":
        payload = bytes_from_octets(payload, 20)
        return serialize([0, payload])

    raise BTClibValueError(f"unknown script_pub_key type: {script_type}")


def is_p2pk(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # p2pk [pub_key, OP_CHECKSIG]
    # 0x41{65-byte pub_key}AC or 0x21{33-byte pub_key}AC
    length = len(script_pub_key)
    return (
        length > 34
        and length == script_pub_key[0] + 2
        and script_pub_key[0] in (0x41, 0x21)
        and script_pub_key[-1] == 0xAC
    )


def is_p2pkh(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # p2pkh [OP_DUP, OP_HASH160, pub_key_hash, OP_EQUALVERIFY, OP_CHECKSIG]
    # 0x76A914{20-byte pub_key_hash}88AC
    return (
        len(script_pub_key) == 25
        and script_pub_key[:3] == b"\x76\xa9\x14"
        and script_pub_key[-2:] == b"\x88\xac"
    )


def is_p2sh(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # p2sh [OP_HASH160, script_hash, OP_EQUAL]
    # 0xA914{20-byte script_hash}87
    return (
        len(script_pub_key) == 23
        and script_pub_key[:2] == b"\xa9\x14"
        and script_pub_key[-1] == 0x87
    )


def is_p2ms(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # p2ms [m, pub_keys, n, OP_CHECKMULTISIG]
    length = len(script_pub_key)
    if length < 37 or script_pub_key[-1] != 0xAE:
        return False
    m = script_pub_key[0] - 80
    n = script_pub_key[-2] - 80
    if not 0 < m < 17 or not m <= n < 17:
        return False
    stream = bytesio_from_binarydata(script_pub_key[1:-2])
    pub_keys = [var_bytes.deserialize(stream) for _ in range(n)]
    if any(len(pub_key) not in (33, 65) for pub_key in pub_keys):
        return False
    # TODO: check all pub_keys are valid
    return not stream.read(1)


def is_nulldata(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # nulldata [OP_RETURN, data]
    length = len(script_pub_key)
    if length < 78:
        # OP_RETURN, data length, data up to 75 bytes max
        # 0x6A{1 byte data-length}{data (0-75 bytes)}
        return (
            length > 1 and script_pub_key[0] == 0x6A and script_pub_key[1] == length - 2
        )
    return (
        # OP_RETURN, OP_PUSHDATA1, data length, data min 76 bytes up to 80
        # 0x6A4C{1-byte data-length}{data (76-80 bytes)}
        78 < length < 84
        and script_pub_key[0] == 0x6A
        and script_pub_key[1] == 0x4C
        and script_pub_key[2] == length - 3
    )


def is_p2wpkh(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    # p2wpkh [0, pub_key_hash]
    # 0x0014{20-byte pub_key_hash}
    length = len(script_pub_key)
    return length == 22 and script_pub_key[:2] == b"\x00\x14"


def is_p2wsh(script_pub_key: Octets) -> bool:
    script_pub_key = bytes_from_octets(script_pub_key)
    length = len(script_pub_key)
    return length == 34 and script_pub_key[:2] == b"\x00\x20"


def payload_from_script_pub_key(script_pub_key: Script) -> Tuple[str, bytes]:
    "Return (script_pub_key type, payload) from the input script_pub_key."

    script_pub_key = (
        serialize(script_pub_key)
        if isinstance(script_pub_key, list)
        else bytes_from_octets(script_pub_key)
    )

    if is_p2wpkh(script_pub_key):
        # p2wpkh [0, pub_key_hash]
        # 0x0014{20-byte pub_key_hash}
        return "p2wpkh", script_pub_key[2:]

    if is_p2wsh(script_pub_key):
        # p2wsh [0, script_hash]
        # 0x0020{32-byte script_hash}
        return "p2wsh", script_pub_key[2:]

    if is_p2pk(script_pub_key):
        # p2pk [pub_key, OP_CHECKSIG]
        # 0x41{65-byte pub_key}AC or 0x21{33-byte pub_key}AC
        return "p2pk", script_pub_key[1:-1]

    if is_p2ms(script_pub_key):
        # p2ms [m, pub_keys, n, OP_CHECKMULTISIG]
        return "p2ms", script_pub_key[:-1]

    if is_nulldata(script_pub_key):
        # nulldata [OP_RETURN, data]
        if len(script_pub_key) < 78:
            # OP_RETURN, data length, data up to 75 bytes max
            # 0x6A{1 byte data-length}{data (0-75 bytes)}
            return "nulldata", script_pub_key[2:]

        # OP_RETURN, OP_PUSHDATA1, data length, data min 76 bytes up to 80
        # 0x6A4C{1-byte data-length}{data (76-80 bytes)}
        return "nulldata", script_pub_key[3:]

    if is_p2pkh(script_pub_key):
        # p2pkh [OP_DUP, OP_HASH160, pub_key_hash, OP_EQUALVERIFY, OP_CHECKSIG]
        # 0x76A914{20-byte pub_key_hash}88AC
        length = len(script_pub_key)
        return "p2pkh", script_pub_key[3 : length - 2]

    if is_p2sh(script_pub_key):
        # p2sh [OP_HASH160, script_hash, OP_EQUAL]
        # 0xA914{20-byte script_hash}87
        length = len(script_pub_key)
        return "p2sh", script_pub_key[2 : length - 1]

    return "unknown", script_pub_key


# 1.+2. = 3. script_pub_key from key(s)/script


def p2pk(key: Key) -> bytes:
    "Return the p2pk script_pub_key of the provided key."

    payload, _ = pub_keyinfo_from_key(key)
    return script_pub_key_from_payload("p2pk", payload)


def p2ms(
    m: int, keys: List[Key], lexi_sort: bool = True, compressed: Optional[bool] = None
) -> bytes:
    """Return the m-of-n multi-sig script_pub_key of the provided keys.

    BIP67 endorses lexicographica key sorting
    according to compressed key representation.

    Note that sorting uncompressed keys (leading 0x04 byte) results
    in a different order than sorting the same keys in compressed
    (leading 0x02 or 0x03 bytes) representation.

    https://github.com/bitcoin/bips/blob/master/bip-0067.mediawiki
    """
    m += 80
    payload = m.to_bytes(1, byteorder="big")
    pub_keys = [pub_keyinfo_from_key(k, compressed=compressed)[0] for k in keys]
    if lexi_sort:
        pub_keys = sorted(pub_keys)
    payload += b"".join([var_bytes.serialize(k) for k in pub_keys])
    n = len(keys) + 80
    payload += n.to_bytes(1, byteorder="big")
    return script_pub_key_from_payload("p2ms", payload)


def nulldata(data: String) -> bytes:
    "Return the nulldata script_pub_key of the provided data."

    if isinstance(data, str):
        data = data.encode()
    return script_pub_key_from_payload("nulldata", data)


def p2pkh(key: Key, compressed: Optional[bool] = None) -> bytes:
    "Return the p2pkh script_pub_key of the provided key."

    pub_key_h160, _ = hash160_from_key(key, compressed=compressed)
    return script_pub_key_from_payload("p2pkh", pub_key_h160)


def p2sh(redeem_script: Script) -> bytes:
    "Return the p2sh script_pub_key of the provided redeem script."

    script_h160 = hash160_from_script(redeem_script)
    return script_pub_key_from_payload("p2sh", script_h160)


def p2wpkh(key: Key) -> bytes:
    """Return the p2wpkh script_pub_key of the provided key.

    If the provided key is a public one, it must be compressed.
    """

    pub_key_h160, _ = hash160_from_key(key, compressed=True)
    return script_pub_key_from_payload("p2wpkh", pub_key_h160)


def p2wsh(redeem_script: Script) -> bytes:
    "Return the p2wsh script_pub_key of the provided redeem script."

    script_h256 = hash256_from_script(redeem_script)
    return script_pub_key_from_payload("p2wsh", script_h256)