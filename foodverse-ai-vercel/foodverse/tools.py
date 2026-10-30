"""Tools exposed to the Groq agent: schemas + Python implementations."""

from __future__ import annotations

import json
from typing import Any

from .nutrition_db import NUTRITION_DB, lookup_food, scale
from .schemas import FoodItem, Macros, MealAnalysis

# Rough daily reference values used for goal comparison (adult, 2000 kcal).
DAILY_REFERENCE = Macros(calories=2000, protein_g=50, carbs_g=275, fat_g=70, fiber_g=28)

DIET_RULES: dict[str, dict[str, Any]] = {
    "vegetarian": {"exclude": ["chicken", "salmon", "beef", "egg"]},
    "vegan": {"exclude": ["chicken", "salmon", "beef", "egg", "paneer", "yogurt",
                          "milk", "ghee", "butter", "ice cream", "gulab jamun", "naan"]},
    "high_protein": {"min_protein_ratio": 0.25},   # >=25% of kcal from protein
    "low_carb": {"max_carb_ratio": 0.25},          # <=25% of kcal from carbs
    "low_fat": {"max_fat_ratio": 0.25},            # <=25% of kcal from fat
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "analyze_meal",
        "description": (
            "Compute total calories and macros for a meal from a list of food items "
            "with estimated gram weights. Use this after identifying foods from an "
            "image or description. Foods not in the database are returned as 'unmatched' "
            "so you can estimate them yourself and say so."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Food name, e.g. 'chapati'"},
                            "grams": {"type": "number", "description": "Estimated weight in grams"},
                        },
                        "required": ["name", "grams"],
                    },
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "lookup_food",
        "description": "Look up nutrition per 100 g for a single food in the built-in database.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "check_diet",
        "description": (
            "Check whether a meal fits a dietary pattern: vegetarian, vegan, "
            "high_protein, low_carb, or low_fat. Pass the same items used for analyze_meal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "diet": {"type": "string", "enum": list(DIET_RULES.keys())},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "grams": {"type": "number"}},
                        "required": ["name", "grams"],
                    },
                },
            },
            "required": ["diet", "items"],
        },
    },
    {
        "name": "suggest_swaps",
        "description": (
            "Suggest lighter or higher-protein swaps from the database for a given food. "
            "goal is one of: lower_calorie, higher_protein, higher_fiber."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "goal": {"type": "string", "enum": ["lower_calorie", "higher_protein", "higher_fiber"]},
            },
            "required": ["name", "goal"],
        },
    },
]


# Groq uses the OpenAI-compatible function-tool schema.
GROQ_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }
    for tool in TOOL_DEFINITIONS
]


def analyze_meal(items: list[dict]) -> dict:
    parsed = [FoodItem(**i) for i in items]
    total = Macros()
    unmatched: list[str] = []
    breakdown = []
    for it in parsed:
        hit = lookup_food(it.name)
        if hit is None:
            unmatched.append(it.name)
            continue
        canonical, per100 = hit
        m = scale(per100, it.grams)
        total = total + m
        breakdown.append({"food": canonical, "grams": it.grams, **m.rounded().model_dump()})
    result = MealAnalysis(items=parsed, total=total.rounded(), unmatched=unmatched)
    pct = {
        k: round(v / getattr(DAILY_REFERENCE, k) * 100)
        for k, v in result.total.model_dump().items()
    }
    return {
        "breakdown": breakdown,
        "total": result.total.model_dump(),
        "percent_of_daily_reference": pct,
        "unmatched": unmatched,
    }


def _lookup(name: str) -> dict:
    hit = lookup_food(name)
    if hit is None:
        return {"found": False, "query": name}
    canonical, m = hit
    return {"found": True, "food": canonical, "per_100g": m.model_dump()}


def check_diet(diet: str, items: list[dict]) -> dict:
    if diet not in DIET_RULES:
        return {"error": f"Unknown diet '{diet}'", "supported": list(DIET_RULES)}
    rule = DIET_RULES[diet]
    names = [i["name"].lower() for i in items]
    if "exclude" in rule:
        violations = [n for n in names for bad in rule["exclude"] if bad in n]
        return {"diet": diet, "compatible": not violations, "violations": sorted(set(violations))}
    total = analyze_meal(items)["total"]
    kcal = total["calories"] or 1
    ratios = {
        "protein": total["protein_g"] * 4 / kcal,
        "carbs": total["carbs_g"] * 4 / kcal,
        "fat": total["fat_g"] * 9 / kcal,
    }
    ok = True
    if "min_protein_ratio" in rule:
        ok = ratios["protein"] >= rule["min_protein_ratio"]
    if "max_carb_ratio" in rule:
        ok = ratios["carbs"] <= rule["max_carb_ratio"]
    if "max_fat_ratio" in rule:
        ok = ratios["fat"] <= rule["max_fat_ratio"]
    return {"diet": diet, "compatible": ok, "energy_ratios": {k: round(v, 2) for k, v in ratios.items()}}


def suggest_swaps(name: str, goal: str) -> dict:
    hit = lookup_food(name)
    if hit is None:
        return {"found": False, "query": name}
    canonical, base = hit
    key = {"lower_calorie": "calories", "higher_protein": "protein_g", "higher_fiber": "fiber_g"}[goal]
    base_v = getattr(base, key)
    cands = []
    for n, m in NUTRITION_DB.items():
        if n == canonical:
            continue
        v = getattr(m, key)
        better = v < base_v if goal == "lower_calorie" else v > base_v
        # keep swaps plausible: similar calorie ballpark unless the goal is calories
        if better and (goal == "lower_calorie" or m.calories <= base.calories * 1.5 + 50):
            cands.append((abs(v - base_v), n, m))
    cands.sort(reverse=True)
    return {
        "food": canonical,
        "goal": goal,
        "suggestions": [{"food": n, "per_100g": m.rounded().model_dump()} for _, n, m in cands[:4]],
    }


_DISPATCH = {
    "analyze_meal": lambda a: analyze_meal(a["items"]),
    "lookup_food": lambda a: _lookup(a["name"]),
    "check_diet": lambda a: check_diet(a["diet"], a["items"]),
    "suggest_swaps": lambda a: suggest_swaps(a["name"], a["goal"]),
}


def run_tool(name: str, args: dict) -> str:
    """Execute a tool and return a JSON string (errors are returned, not raised)."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool '{name}'"})
    try:
        return json.dumps(fn(args))
    except Exception as e:  # noqa: BLE001 - surface to the model so it can recover
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
