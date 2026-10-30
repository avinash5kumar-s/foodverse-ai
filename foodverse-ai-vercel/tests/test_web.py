"""Tests for the framework-free web logic and the served page (no network, no API key)."""

import ast
from types import SimpleNamespace

import pytest

from foodverse.page import INDEX_HTML
from foodverse.web import RequestError, analyze


class FakeAgent:
    def ask(self, text, image_bytes=None):
        return SimpleNamespace(text=f"ok:{text}:{bool(image_bytes)}", tool_calls=[{"tool": "t"}])


class BoomAgent:
    def ask(self, text, image_bytes=None):
        raise ValueError("boom")


def test_analyze_text_only():
    out = analyze("2 chapati", None, agent=FakeAgent())
    assert out == {"answer": "ok:2 chapati:False", "tool_calls": [{"tool": "t"}]}


def test_analyze_with_image():
    assert analyze("", b"\x89PNG...", agent=FakeAgent())["answer"] == "ok::True"


def test_analyze_empty_rejected():
    with pytest.raises(RequestError) as e:
        analyze("   ", None, agent=FakeAgent())
    assert e.value.status == 400


def test_analyze_too_large():
    with pytest.raises(RequestError) as e:
        analyze("x", b"0" * 4_000_001, agent=FakeAgent())
    assert e.value.status == 413


def test_analyze_model_failure_is_502():
    with pytest.raises(RequestError) as e:
        analyze("x", None, agent=BoomAgent())
    assert e.value.status == 502


def test_missing_api_key_is_clear_500(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("foodverse.config.load_dotenv", lambda *a, **k: None, raising=False)
    with pytest.raises(RequestError) as e:
        analyze("banana", None)
    assert e.value.status == 500 and "GROQ_API_KEY" in e.value.message


def test_page_posts_to_api():
    assert "/api/analyze" in INDEX_HTML and "<textarea" in INDEX_HTML


def test_vercel_entrypoint_exports_app():
    """Vercel needs a top-level `app` in app.py; check statically (works without fastapi installed)."""
    tree = ast.parse(open("app.py").read())
    names = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    assert "app" in names
