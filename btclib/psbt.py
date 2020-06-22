#!/usr/bin/env python3

# Copyright (C) 2020 The btclib developers
#
# This file is part of btclib. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution.
#
# No part of btclib including this file, may be copied, modified, propagated,
# or distributed except according to the terms contained in the LICENSE file.

from dataclasses import dataclass
from typing import List, Dict, Tuple, Type, TypeVar, Optional
from base64 import b64decode, b64encode

from .tx import Tx
from .tx_out import TxOut
from .alias import Script
from . import varint, script


_PsbtInput = TypeVar("_PsbtInput", bound="PsbtInput")


@dataclass
class PsbtInput:
    non_witness_utxo: Optional[Tx] = None
    witness_utxo: Optional[TxOut] = None
    partial_sigs: Optional[Dict[str, str]] = None
    sighash: Optional[int] = 0
    redeem_script: Optional[Script] = None
    witness_script: Optional[Script] = None
    hd_keypaths: Optional[Dict[str, str]] = None
    final_script_sig: Optional[Script] = None
    final_script_witness: Optional[Script] = None
    por_commitment: Optional[str] = None
    unknown: Optional[Dict[str, str]] = None

    @classmethod
    def decode(cls: Type[_PsbtInput], input_map: Dict[bytes, bytes]) -> _PsbtInput:
        out_map = {}
        out_map["partial_sigs"] = {}
        out_map["hd_keypaths"] = []
        for key, value in input_map.items():
            if key == b"\x00":
                out_map["non_witness_utxo"] = Tx.deserialize(value)
            elif key == b"\x01":
                out_map["witness_utxo"] = TxOut.deserialize(value)
            elif key[0] == 0x02:
                assert len(key) == 33 + 1
                out_map["partial_sigs"][key[1:].hex()] = value.hex()
            elif key == b"\x03":
                assert len(value) == 4
                out_map["sighash"] = int.from_bytes(value, "little")
            elif key == b"\x04":
                out_map["redeem_script"] = script.decode(value)
            elif key == b"\x05":
                out_map["witness_script"] = script.decode(value)
            elif key[0] == 0x06:
                assert len(key) == 33 + 1
                assert len(value) % 4 == 0
                out_map["hd_keypaths"].append(
                    {
                        "xpub": key[1:].hex(),
                        "fingerprint": value[:4].hex(),
                        "derivation_path": value[4:].hex(),
                    }
                )
            elif key == b"\x07":
                out_map["final_script_sig"] = script.decode(value)
            elif key == b"\x08":
                out_map["final_script_witness"] = script.decode(value)
            elif key == b"\x09":
                out_map["por_commitment"] = value.hex()  # TODO: bip127
            elif key[0] == 0xFC:
                pass  # proprietary use
            else:
                raise KeyError("Invalid key type")

        out = cls(**out_map)

        out.assert_valid()

        return out

    def serialize(self) -> bytes:
        out = b""
        if self.non_witness_utxo:
            out += b"\x01\x00"
            utxo = self.non_witness_utxo.serialize()
            out += varint.encode(len(utxo)) + utxo
        if self.witness_utxo:
            out += b"\x01\x01"
            utxo = self.witness_utxo.serialize()
            out += varint.encode(len(utxo)) + utxo
        if self.partial_sigs:
            for key, value in self.partial_sigs.items():
                out += b"\x22\x02" + bytes.fromhex(key)
                out += varint.encode(len(value)) + bytes.fromhex(value)
        if self.sighash:
            out += b"\x01\x03\x04"
            out += self.sighash.to_bytes(4, "little")
        if self.redeem_script:
            out += b"\x01\x04"
            out += script.serialize(self.redeem_script)
        if self.witness_script:
            out += b"\x01\x05"
            out += script.serialize(self.witness_script)
        if self.hd_keypaths:
            for hd_keypath in self.hd_keypaths:
                out += b"\x22\x06" + bytes.fromhex(hd_keypath["xpub"])
                keypath = bytes.fromhex(hd_keypath["fingerprint"])
                keypath += bytes.fromhex(hd_keypath["derivation_path"])
                out += varint.encode(len(keypath)) + keypath
        if self.final_script_sig:
            out += b"\x01\x07"
            out += script.serialize(self.final_script_sig)
        if self.final_script_witness:
            pass
            # out += b"\x01\x08"
            # out += script.deserialize(self.final_script_witness)
        if self.por_commitment:
            out += b"\x01\x09"
            c = bytes.fromhex(self.por_commitment)
            out += varint.encode(len(c)) + c
        return out

    def assert_valid(self) -> None:
        pass


_PsbtOutput = TypeVar("_PsbtOutput", bound="PsbtOutput")


@dataclass
class PsbtOutput:
    redeem_script: Optional[Script] = None
    witness_script: Optional[Script] = None
    hd_keypaths: Optional[Dict[str, str]] = None
    unknown: Optional[Dict[str, str]] = None

    @classmethod
    def decode(cls: Type[_PsbtOutput], output_map: Dict[bytes, bytes]) -> _PsbtOutput:
        out_map = {}
        out_map["hd_keypaths"] = []
        for key, value in output_map.items():
            if key == b"\x00":
                out_map["redeem_script"] = script.decode(value)
            elif key == b"\x01":
                out_map["witness_script"] = script.decode(value)
            elif key[0] == 0x02:
                assert len(key) == 33 + 1
                assert len(value) % 4 == 0
                out_map["hd_keypaths"].append(
                    {
                        "xpub": key[1:].hex(),
                        "fingerprint": value[:4].hex(),
                        "derivation_path": value[4:].hex(),
                    }
                )
            elif key[0] == 0xFC:
                pass  # proprietary use
            else:
                raise KeyError("Invalid key type")

        out = cls(**out_map)

        out.assert_valid()

        return out

    def serialize(self) -> bytes:
        out = b""
        if self.redeem_script:
            out += b"\x01\x00"
            out += script.serialize(self.redeem_script)
        if self.witness_script:
            out += b"\x01\x01"
            out += script.serialize(self.witness_script)
        if self.hd_keypaths:
            for hd_keypath in self.hd_keypaths:
                out += b"\x22\x02" + bytes.fromhex(hd_keypath["xpub"])
                keypath = bytes.fromhex(hd_keypath["fingerprint"])
                keypath += bytes.fromhex(hd_keypath["derivation_path"])
                out += varint.encode(len(keypath)) + keypath
        return out

    def assert_valid(self) -> None:
        pass


_PSbt = TypeVar("_PSbt", bound="Psbt")


@dataclass
class Psbt:
    tx: Tx
    inputs: List[PsbtInput]
    outputs: List[PsbtOutput]
    version: Optional[int] = 0
    hd_keypaths: Optional[List[Dict[str, str]]] = None
    unknown: Optional[Dict[str, str]] = None

    @classmethod
    def deserialize(cls: Type[_PSbt], string: str) -> _PSbt:
        data = b64decode(string)

        magic_bytes = data[:5]
        assert magic_bytes == b"psbt\xff", "Malformed psbt: missing magic bytes"

        data = data[5:]

        global_map, data = deserialize_map(data)
        version = 0
        xpub = None
        hd_keypaths = []
        unknown = {}
        for key, value in global_map.items():
            if key == b"\x00":
                tx = Tx.deserialize(value)
            elif key[0] == 0x01:  # TODO
                assert len(key) == 78 + 1
                assert len(value) % 4 == 0
                hd_keypaths.append(
                    {
                        "xpub": key[1:].hex(),
                        "fingerprint": value[:4].hex(),
                        "derivation_path": value[4:].hex(),
                    }
                )
            elif key[0] == 0xFB:
                assert len(value) == 32
                version = int.from_bytes(value, "little")
            elif key[0] == 0xFC:
                pass  # proprietary use
            else:
                raise KeyError("Invalid key type")

        input_len = len(tx.vin)
        output_len = len(tx.vout)

        inputs = []
        for i in range(input_len):
            input_map, data = deserialize_map(data)
            input_map = PsbtInput.decode(input_map)
            inputs.append(input_map)

        outputs = []
        for i in range(output_len):
            output_map, data = deserialize_map(data)
            output_map = PsbtOutput.decode(output_map)
            outputs.append(output_map)

        psbt = cls(
            tx=tx,
            inputs=inputs,
            outputs=outputs,
            version=version,
            hd_keypaths=hd_keypaths,
            unknown=unknown,
        )

        psbt.assert_valid()

        return psbt

    def serialize(self) -> str:
        out = bytes.fromhex("70736274ff")
        out += b"\x01\x00"
        tx = self.tx.serialize()
        out += varint.encode(len(tx)) + tx
        if self.hd_keypaths:
            for hd_keypath in self.hd_keypaths:
                out += b"\x4f\x01" + bytes.fromhex(hd_keypath["xpub"])
                keypath = bytes.fromhex(hd_keypath["fingerprint"])
                keypath += bytes.fromhex(hd_keypath["derivation_path"])
                out += varint.encode(len(keypath)) + keypath
        if self.version:
            pass
        out += b"\x00"
        for input_map in self.inputs:
            out += input_map.serialize() + b"\x00"
        for output_map in self.outputs:
            out += output_map.serialize() + b"\x00"
        return b64encode(out).decode()

    def assert_valid(self) -> None:
        for vin in self.tx.vin:
            assert vin.scriptSig == []
        for input_map in self.inputs:
            input_map.assert_valid()
        for output_map in self.outputs:
            output_map.assert_valid()


def deserialize_map(data: bytes) -> Tuple[Dict[bytes, bytes], bytes]:
    assert len(data) != 0, "Malformed psbt: at least a map is missing"
    partial_map: Dict[bytes, bytes] = {}
    while True:
        if len(data) == 0:
            return partial_map, data
        if data[0] == 0:
            data = data[1:]
            return partial_map, data
        key_len = varint.decode(data)
        data = data[len(varint.encode(key_len)) :]
        key = data[:key_len]
        data = data[key_len:]
        value_len = varint.decode(data)
        data = data[len(varint.encode(value_len)) :]
        value = data[:value_len]
        data = data[value_len:]
        assert key not in partial_map.keys(), "Malformed psbt: duplicate keys"
        partial_map[key] = value
