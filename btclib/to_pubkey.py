#!/usr/bin/env python3

# Copyright (C) 2017-2020 The btclib developers
#
# This file is part of btclib. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution.
#
# No part of btclib including this file, may be copied, modified, propagated,
# or distributed except according to the terms contained in the LICENSE file.

from typing import Union

from . import bip32
from .alias import Octets, Point, PubKey, XkeyDict
from .curve import Curve
from .curves import secp256k1
from .network import curve_from_bip32version
from .secpoint import bytes_from_point, point_from_octets
from .utils import bytes_from_octets


def _pubkey_tuple_from_dict(d: XkeyDict, ec: Curve) -> Point:
    if d['key'][0] in (2, 3):
        if ec != curve_from_bip32version(d['version']):
            m = f"ec / xpub version ({d['version']!r}) mismatch"
            raise ValueError(m)
        return point_from_octets(d['key'], ec)
    raise ValueError(f"Not a public key: {d['key'].hex()}")


def to_pubkey_tuple(P: PubKey, ec: Curve = secp256k1) -> Point:
    """Return a point tuple from any possible pubkey representation.

    It supports:

    - BIP32 extended keys (bytes, string, or XkeyDict)
    - SEC Octets (bytes or hex-string, with 02, 03, or 04 prefix)
    - native tuple
    """

    if isinstance(P, tuple):
        if ec.is_on_curve(P) and P[1] != 0:
            return P
        raise ValueError(f"Not a public key: {P}")
    elif isinstance(P, dict):
        return _pubkey_tuple_from_dict(P, ec)
    else:
        try:
            xkey = bip32.deserialize(P)
        except Exception:
            pass
        else:
            return _pubkey_tuple_from_dict(xkey, ec)

    return point_from_octets(P, ec)


def _to_pubkey_bytes_from_dict(d: XkeyDict, compressed: bool) -> bytes:
        if not compressed:
            m = "Uncompressed SEC / compressed BIP32 key mismatch"
            raise ValueError(m)
        if d['key'][0] in (2, 3):
            return d['key']
        raise ValueError(f"Not a public key: {d['key'].hex()}")


def to_pubkey_bytes(P: PubKey, compressed: bool = True, ec: Curve = secp256k1) -> bytes:
    """Return SEC bytes from any possible pubkey representation.

    It supports:

    - BIP32 extended keys (bytes, string, or XkeyDict)
    - SEC Octets (bytes or hex-string, with 02, 03, or 04 prefix)
    - native tuple
    """

    if isinstance(P, tuple):
        return bytes_from_point(P, compressed, ec)
    elif isinstance(P, dict):
        return _to_pubkey_bytes_from_dict(P, compressed)
    else:
        try:
            xkey = bip32.deserialize(P)
        except Exception:
            pass
        else:
            return _to_pubkey_bytes_from_dict(xkey, compressed)


        pubkey = bytes_from_octets(P)
        if not compressed and len(pubkey) != 2*ec.psize + 1:
            m = f"Wrong size ({len(pubkey)}-bytes) for uncompressed SEC key"
            raise ValueError(m)
        if compressed and len(pubkey) != ec.psize + 1:
            m = f"Wrong size ({len(pubkey)}-bytes) for compressed SEC key"
            raise ValueError(m)
        Q = point_from_octets(pubkey, ec)  # verify it is a valid point
        return bytes_from_point(Q, compressed, ec)
