"""Unit tests for Phase 1: Database, Models, JSON Repair, Settings, and Health."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import get_settings, encrypt_value, decrypt_value
from app.database import init_db
from app.main import app
from llm.router import _repair_json, _extract_json_block, LLMRouter


class SampleSchema(BaseModel):
    name: str
    score: int
    tags: list[str]


# ─── JSON Repair Tests ───────────────────────────────────────


def test_extract_json_from_markdown():
    markdown = '```json\n{"name": "Alice", "score": 95, "tags": ["python"]}\n```'
    extracted = _extract_json_block(markdown)
    assert extracted == '{"name": "Alice", "score": 95, "tags": ["python"]}'


def test_repair_json_trailing_commas():
    malformed = '{"name": "Bob", "score": 80, "tags": ["fastapi",],}'
    repaired = _repair_json(malformed)
    assert ',"tags"' in repaired or 'tags' in repaired
    assert not repaired.endswith(",}")


def test_repair_json_unclosed_braces():
    incomplete = '{"name": "Charlie", "score": 75, "tags": ["sql"]'
    repaired = _repair_json(incomplete)
    assert repaired.endswith("}")


def test_parse_and_validate_with_repair():
    raw_response = """```json
    {
        'name': 'Dev',
        'score': 90,
        'tags': ['ai', 'python',]
    }
    ```"""
    parsed = LLMRouter._parse_and_validate(raw_response, SampleSchema)
    assert parsed.name == "Dev"
    assert parsed.score == 90
    assert parsed.tags == ["ai", "python"]


# ─── Encryption Tests ────────────────────────────────────────


def test_fernet_encryption_and_decryption():
    plaintext = "super-secret-workday-password-123"
    ciphertext = encrypt_value(plaintext)
    assert ciphertext != plaintext
    decrypted = decrypt_value(ciphertext)
    assert decrypted == plaintext


# ─── Health & Settings API Tests ─────────────────────────────


def test_health_check_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert data["components"]["database"]["status"] == "up"
    assert "llm_providers" in data["components"]


def test_llm_settings_api():
    init_db()
    client = TestClient(app)
    
    # 1. Get LLM settings
    res = client.get("/api/settings/llm")
    assert res.status_code == 200
    data = res.json()
    assert "mistral" in data
    assert "nvidia" in data
    assert "default_provider" in data

    # 2. Update models via POST /api/settings/llm
    res = client.post("/api/settings/llm", json={
        "default_provider": "mistral",
        "mistral_strong_model": "mistral-large-latest",
        "mistral_cheap_model": "mistral-small-latest",
        "nvidia_strong_model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "nvidia_cheap_model": "nvidia/llama-3.1-nemotron-51b-instruct",
    })
    assert res.status_code == 200
    updated = res.json()
    assert updated["default_provider"] == "mistral"
    assert updated["nvidia"]["strong_model"] == "nvidia/llama-3.1-nemotron-70b-instruct"
    assert updated["nvidia"]["cheap_model"] == "nvidia/llama-3.1-nemotron-51b-instruct"

