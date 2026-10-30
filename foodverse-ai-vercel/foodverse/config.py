"""Configuration for Food Verse AI (Groq)."""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "qwen/qwen3.8-27b"


def get_model() -> str:
    return os.getenv("FOODVERSE_MODEL", DEFAULT_MODEL)


def get_api_key() -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key or key == "your-key-here":
        return None
    return key


MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 2048
MAX_IMAGE_DIM = 1568
