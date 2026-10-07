from __future__ import annotations

from src.infrastructure.security.tokens import generate_token, hash_token


def test_generate_token_is_high_entropy_and_unique():
    tokens = {generate_token() for _ in range(100)}
    assert len(tokens) == 100


def test_hash_token_is_deterministic():
    token = generate_token()
    assert hash_token(token) == hash_token(token)


def test_hash_token_differs_for_different_tokens():
    assert hash_token(generate_token()) != hash_token(generate_token())


def test_hash_token_never_equals_the_raw_token():
    token = generate_token()
    assert hash_token(token) != token
