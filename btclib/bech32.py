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


"""Bech32 encoding and decoding functions.

BIP173: https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki

This implementation of Bech32 is originally from
https://github.com/sipa/bech32/tree/master/ref/python,
with the following modifications:

* splitted the original segwit_addr.py file in bech32.py and segwitaddr.py
* type annotated python3
* avoided returning (None, None), throwing ValueError instead
* removed the 90-chars limit for Bech32 string, enforced by segwitaddr instead
* detailed error messages
* interface mimics the native python3 base64 interface, i.e.
  it supports encoding bytes-like objects to ASCII bytes,
  and decoding bytes-like objects or ASCII strings to bytes
"""


from typing import Tuple, Iterable, List, Union

__ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values: Iterable[int]) -> int:
    """Internal function that computes the Bech32 checksum."""
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _hrp_expand(hrp: str) -> List[int]:
    """Expand the HRP into values for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _create_checksum(hrp: str, data: List[int]) -> List[int]:
    """Compute the checksum values given HRP and data."""
    values = _hrp_expand(hrp) + data
    polymod = _polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return checksum


def encode(hrp: str, data: List[int]) -> bytes:
    """Compute a Bech32 string given HRP and data values."""
    combined = data + _create_checksum(hrp, data)
    # FIXME: work with bytes
    s = hrp + '1' + ''.join([__ALPHABET[d] for d in combined])
    return s.encode()


def _verify_checksum(hrp: str, data: List[int]) -> bool:
    """Verify a checksum given HRP and converted data characters."""
    return _polymod(_hrp_expand(hrp) + data) == 1


def decode(bech: Union[str, bytes]) -> Tuple[str, List[int]]:
    """Validate a Bech32 string, and determine HRP and data."""

    if isinstance(bech, bytes):
        bech = bech.decode("ascii")

    if (any(ord(x) < 33 or ord(x) > 126 for x in bech)):
        msg = "Bech32 string contains "
        msg += "ASCII characters outside printable set [33-126]"
        raise ValueError(msg)
    if bech.lower() != bech and bech.upper() != bech:
        raise ValueError("Mixed case Bech32 string")
    bech = bech.lower()

    # if len(bech) > 90:
    #     raise ValueError(f"Bech32 string length ({len(bech)}) > 90")

    pos = bech.rfind('1')  # find the separator between hrp and data
    if pos < 1:
        raise ValueError("Missing HRP in Bech32 string")
    if pos + 7 > len(bech):
        raise ValueError("Bech32 checksum length < 6")

    hrp = bech[:pos]

    if not all(x in __ALPHABET for x in bech[pos+1:]):
        msg = "Bech32 string data part contains invalid characters"
        raise ValueError(msg)
    data = [__ALPHABET.find(x) for x in bech[pos+1:]]

    if _verify_checksum(hrp, data):
        return hrp, data[:-6]
    raise ValueError("Invalid Bech32 string checksum")