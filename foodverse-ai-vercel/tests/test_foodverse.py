"""Tests for nutrition DB, tools, vision prep, and the agent loop (with a fake client)."""

import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from foodverse.agent import FoodVerseAgent
from foodverse.nutrition_db import lookup_food, scale
from foodverse.tools import analyze_meal, check_diet, run_tool, suggest_swaps
from foodverse.vision import prepare_image


# ---------- nutrition db ----------
def test_lookup_exact_and_fuzzy():
    assert lookup_food("chapati")[0] == "chapati"
    assert lookup_food("Paneer")[0] == "paneer"
    assert lookup_food("bananaa")[0] == "banana"
    assert lookup_food("zzzz-not-food") is None


def test_scale():
    _, per100 = lookup_food("paneer")
    assert scale(per100, 50).calories == pytest.approx(132.5)


# ---------- tools ----------
def test_analyze_meal_totals():
    r = analyze_meal([{"name": "chapati", "grams": 100}, {"name": "dal (cooked)", "grams": 200}])
    assert r["total"]["calories"] == pytest.approx(297 + 232)
    assert r["unmatched"] == []


def test_analyze_meal_unmatched():
    r = analyze_meal([{"name": "banana", "grams": 100}, {"name": "dragon stew", "grams": 100}])
    assert r["unmatched"] == ["dragon stew"]
    assert r["total"]["calories"] == pytest.approx(89)


def test_check_diet_vegetarian():
    ok = check_diet("vegetarian", [{"name": "paneer", "grams": 100}])
    bad = check_diet("vegetarian", [{"name": "chicken curry", "grams": 100}])
    assert ok["compatible"] and not bad["compatible"]


def test_check_diet_vegan_flags_dairy():
    r = check_diet("vegan", [{"name": "plain yogurt", "grams": 100}])
    assert not r["compatible"]


def test_check_diet_high_protein():
    assert check_diet("high_protein", [{"name": "chicken breast (cooked)", "grams": 150}])["compatible"]
    assert not check_diet("high_protein", [{"name": "white rice (cooked)", "grams": 150}])["compatible"]


def test_suggest_swaps():
    r = suggest_swaps("french fries", "lower_calorie")
    assert r["suggestions"] and all(
        s["per_100g"]["calories"] < 312 for s in r["suggestions"]
    )


def test_run_tool_errors_are_json():
    assert "error" in json.loads(run_tool("nope", {}))
    assert "error" in json.loads(run_tool("analyze_meal", {"items": [{"name": "x", "grams": -5}]}))


# ---------- vision ----------
def _png(size=(100, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="PNG")
    return buf.getvalue()


def test_prepare_image_block():
    block = prepare_image(_png())
    assert block["type"] == "image_url" and block["image_url"]["url"].startswith("data:image/png;base64,")


def test_prepare_image_downscales():
    block = prepare_image(_png((4000, 3000)))
    import base64

    encoded = block["image_url"]["url"].split(",", 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert max(img.size) <= 1568


# ---------- agent loop with fake client ----------
class FakeClient:
    """Returns a function-call turn, then a final text turn."""

    def __init__(self):
        self.calls = 0
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kw):
        self.calls += 1
        if self.calls == 1:
            call = SimpleNamespace(
                id="t1",
                function=SimpleNamespace(
                    name="analyze_meal",
                    arguments='{"items": [{"name": "banana", "grams": 120}]}',
                ),
            )
            msg = SimpleNamespace(content=None, tool_calls=[call])
        else:
            msg = SimpleNamespace(content="done", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_agent_tool_loop():
    agent = FoodVerseAgent(client=FakeClient(), model="test")
    res = agent.ask("a banana", _png())
    assert res.text == "done"
    assert res.tool_calls[0]["tool"] == "analyze_meal"
    # history: user, assistant(tool_use), user(tool_result), assistant(final)
    assert len(agent.history) == 4
    assert agent.history[2]["role"] == "tool"
    assert agent.history[2]["tool_call_id"] == "t1"
