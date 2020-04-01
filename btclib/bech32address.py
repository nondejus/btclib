# Copyright (c) 2017 Pieter Wuille
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Copyright (C) 2019-2020 The btclib developers
#
# This file is part of btclib. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution.
#
# No part of btclib including this file, may be copied, modified, propagated,
# or distributed except according to the terms contained in the LICENSE file.


"""SegWit address functions.

Some of these functions were originally from
https://github.com/sipa/bech32/tree/master/ref/python,
with the following modifications:

* moved bech32 stuff into bech32.py
* type annotated python3
* avoided returning None or (None, None), throwing ValueError instead
* detailed error messages and exteded safety checks
* check that bech32 addresses are not longer than 90 characters
  (as this is not enforced by bech32.b32decode anymore)
"""


from typing import Iterable, List, Tuple, Union

from .alias import Octets, String, XkeyDict
from .base58wif import _pubkeytuple_from_wif
from .bech32 import b32decode, b32encode
from .bip32 import deserialize
from .network import _NETWORKS, _P2W_PREFIXES
from .utils import bytes_from_hexstring, h160_from_pubkey, hash160, sha256


def has_segwit_prefix(addr: String) -> bool:

    if isinstance(addr, str):
        str_addr = addr.strip()
        str_addr = str_addr.lower()
    else:
        str_addr = addr.decode()

    for prefix in _P2W_PREFIXES:
        if str_addr.startswith(prefix + '1'):
            return True

    return False


def _convertbits(data: Iterable[int], frombits: int,
                 tobits: int, pad: bool = True) -> List[int]:
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError(f"invalid value {value}")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)

    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("failure")

    return ret


def _check_witness(witvers: int, witprog: bytes):
    l = len(witprog)
    if witvers == 0:
        if l not in (20, 32):
            raise ValueError(f"witness program length ({l}) is not 20 or 32")
    elif witvers > 16 or witvers < 0:
        msg = f"witness version ({witvers}) not in [0, 16]"
        raise ValueError(msg)
    else:
        if l < 2 or l > 40:
            raise ValueError(f"witness program length ({l}) not in [2, 40]")


# bech32 native SegWit addresses


def b32address_from_witness(wv: int, wp: Octets, network: str = 'mainnet') -> bytes:
    """Encode a bech32 native SegWit address."""

    wp = bytes_from_hexstring(wp)
    _check_witness(wv, wp)
    hrp = _P2W_PREFIXES[_NETWORKS.index(network)]
    ret = b32encode(hrp, [wv] + _convertbits(wp, 8, 5))
    return ret


def witness_from_b32address(b32addr: String) -> Tuple[int, bytes, str, bool]:
    """Decode a bech32 native SegWit address."""

    if isinstance(b32addr, str):
        b32addr = b32addr.strip()

    # the following check was originally in b32decode
    # but it does not pertain there
    if len(b32addr) > 90:
        raise ValueError(f"Bech32 address length ({len(b32addr)}) > 90")

    hrp, data = b32decode(b32addr)

    # check that it is a SegWit address
    i = _P2W_PREFIXES.index(hrp)

    if len(data) == 0:
        raise ValueError(f"Bech32 address with empty data")

    witvers = data[0]
    witprog = _convertbits(data[1:], 5, 8, False)
    _check_witness(witvers, bytes(witprog))

    if len(witprog) == 20:
        is_script_hash = False
    else:
        is_script_hash = True

    return witvers, bytes(witprog), _NETWORKS[i], is_script_hash


def p2wpkh(pubkey: Octets, network: str = 'mainnet') -> bytes:
    """Return the p2wpkh (bech32 native) SegWit address."""
    h160 = h160_from_pubkey(pubkey)
    return b32address_from_witness(0, h160, network)


def p2wpkh_from_wif(wif: String) -> bytes:
    """Return the p2wpkh (bech32 native) SegWit address."""
    o, network = _pubkeytuple_from_wif(wif)
    return p2wpkh(o, network)


def p2wpkh_from_xpub(d: Union[XkeyDict, String]) -> bytes:
    """Return the p2wpkh (native SegWit) address."""
    if not isinstance(d, dict):
        d = deserialize(d)

    if d['key'][0] not in (2, 3):
        # if pubkey would be derived from prvkey,
        # then this safety check might be removed
        raise ValueError("xkey is not a public one")
    return p2wpkh(d['key'], d['network'])


def p2wsh_address(wscript: Octets, network: str = 'mainnet') -> bytes:
    """Return the p2wsh (bech32 native) SegWit address."""
    h256 = sha256(wscript)
    return b32address_from_witness(0, h256, network)
