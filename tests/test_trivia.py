"""Smoke tests for trivia.py — pure Python, no Streamlit or Snowflake needed."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trivia import MATCH_TRIVIA


def test_trivia_is_not_empty():
    assert len(MATCH_TRIVIA) > 0


def test_trivia_keys_are_strings():
    for key in MATCH_TRIVIA:
        assert isinstance(key, str), f"Key is not a string: {key!r}"


def test_trivia_values_are_strings():
    for key, value in MATCH_TRIVIA.items():
        assert isinstance(value, str), f"Value for {key!r} is not a string"
        assert len(value) > 0, f"Value for {key!r} is empty"


def test_trivia_keys_contain_vs():
    for key in MATCH_TRIVIA:
        assert " vs " in key, f"Key does not follow 'Team vs Team' format: {key!r}"
