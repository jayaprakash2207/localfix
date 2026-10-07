from __future__ import annotations

from src.infrastructure.security.hashing import hash_password, verify_password


def test_hash_is_never_the_plaintext():
    hashed = hash_password("Str0ngP@ssw0rd!")
    assert hashed != "Str0ngP@ssw0rd!"


def test_verify_accepts_correct_password():
    hashed = hash_password("Str0ngP@ssw0rd!")
    assert verify_password("Str0ngP@ssw0rd!", hashed) is True


def test_verify_rejects_incorrect_password():
    hashed = hash_password("Str0ngP@ssw0rd!")
    assert verify_password("wrong-password", hashed) is False


def test_same_password_hashes_differently_each_time():
    """Argon2id salts each hash, so two hashes of the same password must differ."""
    assert hash_password("same-input") != hash_password("same-input")


def test_verify_returns_false_for_a_malformed_hash():
    """Security review F11: a non-Argon2/corrupted hash must not raise, just fail closed."""
    assert verify_password("anything", "not-a-real-argon2-hash") is False
    assert verify_password("anything", "") is False
