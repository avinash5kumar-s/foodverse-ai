"""A small built-in nutrition database (values per 100 g, approximate).

Deliberately compact and focused on commonly eaten foods, including many
Indian staples. Extend NUTRITION_DB or swap in a real data source (USDA
FoodData Central, IFCT) behind `lookup_food`.
"""

from difflib import get_close_matches

from .schemas import Macros

# name: (calories, protein_g, carbs_g, fat_g, fiber_g) per 100 g
_RAW: dict[str, tuple[float, float, float, float, float]] = {
    "white rice (cooked)": (130, 2.7, 28.0, 0.3, 0.4),
    "brown rice (cooked)": (112, 2.3, 23.5, 0.8, 1.8),
    "chapati": (297, 9.0, 46.0, 7.5, 4.0),
    "roti": (297, 9.0, 46.0, 7.5, 4.0),
    "paratha": (326, 7.0, 44.0, 13.0, 3.5),
    "naan": (290, 9.0, 50.0, 5.0, 2.0),
    "dal (cooked)": (116, 7.0, 20.0, 0.4, 5.0),
    "chana masala": (164, 8.0, 22.0, 5.0, 7.0),
    "rajma (cooked)": (127, 8.7, 22.8, 0.5, 6.4),
    "paneer": (265, 18.3, 1.2, 20.8, 0.0),
    "palak paneer": (160, 8.0, 5.0, 12.0, 2.0),
    "chicken curry": (150, 14.0, 4.0, 8.5, 1.0),
    "chicken breast (cooked)": (165, 31.0, 0.0, 3.6, 0.0),
    "egg (boiled)": (155, 12.6, 1.1, 10.6, 0.0),
    "egg (fried)": (196, 13.6, 0.8, 15.3, 0.0),
    "idli": (130, 4.0, 26.0, 0.4, 1.0),
    "dosa": (168, 3.9, 29.0, 3.7, 1.2),
    "sambar": (55, 2.5, 8.0, 1.5, 2.0),
    "upma": (120, 3.0, 19.0, 3.5, 1.5),
    "poha": (130, 2.5, 25.0, 2.5, 1.2),
    "samosa": (308, 5.0, 32.0, 17.0, 2.5),
    "biryani (chicken)": (180, 8.5, 22.0, 6.5, 1.0),
    "plain yogurt": (61, 3.5, 4.7, 3.3, 0.0),
    "milk (whole)": (61, 3.2, 4.8, 3.3, 0.0),
    "banana": (89, 1.1, 22.8, 0.3, 2.6),
    "apple": (52, 0.3, 13.8, 0.2, 2.4),
    "mango": (60, 0.8, 15.0, 0.4, 1.6),
    "orange": (47, 0.9, 11.8, 0.1, 2.4),
    "potato (boiled)": (87, 1.9, 20.1, 0.1, 1.8),
    "french fries": (312, 3.4, 41.0, 15.0, 3.8),
    "broccoli": (35, 2.4, 7.2, 0.4, 3.3),
    "spinach": (23, 2.9, 3.6, 0.4, 2.2),
    "mixed salad": (20, 1.2, 3.5, 0.2, 1.5),
    "bread (white)": (265, 9.0, 49.0, 3.2, 2.7),
    "bread (whole wheat)": (247, 13.0, 41.0, 3.4, 7.0),
    "pizza (cheese)": (266, 11.0, 33.0, 10.0, 2.3),
    "burger (beef)": (254, 13.0, 24.0, 11.0, 1.3),
    "pasta (cooked)": (158, 5.8, 31.0, 0.9, 1.8),
    "oats (cooked)": (71, 2.5, 12.0, 1.5, 1.7),
    "almonds": (579, 21.2, 21.6, 49.9, 12.5),
    "peanuts": (567, 25.8, 16.1, 49.2, 8.5),
    "ghee": (900, 0.0, 0.0, 100.0, 0.0),
    "butter": (717, 0.9, 0.1, 81.0, 0.0),
    "olive oil": (884, 0.0, 0.0, 100.0, 0.0),
    "sugar": (387, 0.0, 100.0, 0.0, 0.0),
    "gulab jamun": (300, 4.0, 45.0, 12.0, 0.5),
    "chocolate (dark)": (546, 4.9, 61.0, 31.0, 7.0),
    "ice cream (vanilla)": (207, 3.5, 24.0, 11.0, 0.7),
    "salmon (cooked)": (206, 22.0, 0.0, 12.0, 0.0),
    "tofu": (76, 8.0, 1.9, 4.8, 0.3),
    "lentil soup": (80, 5.0, 12.0, 1.5, 3.5),
    "cola": (42, 0.0, 10.6, 0.0, 0.0),
    "orange juice": (45, 0.7, 10.4, 0.2, 0.2),
}

NUTRITION_DB: dict[str, Macros] = {
    name: Macros(calories=v[0], protein_g=v[1], carbs_g=v[2], fat_g=v[3], fiber_g=v[4])
    for name, v in _RAW.items()
}


def lookup_food(name: str) -> tuple[str, Macros] | None:
    """Return (canonical_name, macros_per_100g) for the closest match, or None."""
    key = name.strip().lower()
    if key in NUTRITION_DB:
        return key, NUTRITION_DB[key]
    # substring match first (e.g. "boiled egg" -> "egg (boiled)" handled by fuzzy below)
    for canonical in NUTRITION_DB:
        base = canonical.split(" (")[0]
        if key == base or key in canonical or base in key:
            return canonical, NUTRITION_DB[canonical]
    close = get_close_matches(key, NUTRITION_DB.keys(), n=1, cutoff=0.7)
    if close:
        return close[0], NUTRITION_DB[close[0]]
    return None


def scale(macros_per_100g: Macros, grams: float) -> Macros:
    f = grams / 100.0
    return Macros(
        calories=macros_per_100g.calories * f,
        protein_g=macros_per_100g.protein_g * f,
        carbs_g=macros_per_100g.carbs_g * f,
        fat_g=macros_per_100g.fat_g * f,
        fiber_g=macros_per_100g.fiber_g * f,
    )
