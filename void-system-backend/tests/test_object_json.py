"""Canonical SQLite object JSON contract tests."""
import json
import math
import unittest

from adapters.sqlite.object_json import (
    ObjectJSONContractError,
    decode_object,
    encode_legacy_object,
    encode_object,
)


class ObjectJSONTests(unittest.TestCase):
    def test_runtime_decoder_accepts_only_canonical_json_objects(self) -> None:
        self.assertEqual(decode_object('{"ready": true}'), {"ready": True})
        double_encoded = json.dumps('{"ready": true}')
        with self.assertRaises(ObjectJSONContractError):
            decode_object(double_encoded)
        with self.assertRaises(ObjectJSONContractError):
            decode_object('[]')
        with self.assertRaises(ObjectJSONContractError):
            decode_object('not-json')

    def test_legacy_decoder_is_available_only_for_one_way_migration(self) -> None:
        double_encoded = json.dumps('{"ready": true}')
        self.assertEqual(
            encode_legacy_object(double_encoded),
            '{"ready": true}',
        )
        self.assertEqual(
            encode_legacy_object('finish the draft', legacy_text_key="criteria"),
            '{"criteria": "finish the draft"}',
        )
        with self.assertRaises(ObjectJSONContractError):
            encode_legacy_object('unknown-corruption')

    def test_runtime_encoder_rejects_non_object_and_non_finite_values(self) -> None:
        with self.assertRaises(TypeError):
            encode_object([])
        with self.assertRaises(ObjectJSONContractError):
            encode_object({"score": math.nan})


if __name__ == "__main__":
    unittest.main()
