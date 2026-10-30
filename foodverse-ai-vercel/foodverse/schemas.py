"""Pydantic schemas shared across the agent and tools."""

from pydantic import BaseModel, Field


class Macros(BaseModel):
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0

    def __add__(self, other: "Macros") -> "Macros":
        return Macros(
            calories=self.calories + other.calories,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
        )

    def rounded(self) -> "Macros":
        return Macros(**{k: round(v, 1) for k, v in self.model_dump().items()})


class FoodItem(BaseModel):
    name: str
    grams: float = Field(gt=0, description="Estimated portion weight in grams")


class MealAnalysis(BaseModel):
    items: list[FoodItem]
    total: Macros
    unmatched: list[str] = Field(default_factory=list)
