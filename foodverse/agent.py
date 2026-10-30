"""Food Verse agent powered by Groq vision and function calling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import MAX_TOKENS, MAX_TOOL_ROUNDS, get_api_key, get_model
from .tools import GROQ_TOOL_DEFINITIONS, run_tool
from .vision import prepare_image

SYSTEM_PROMPT = """You are Food Verse AI, a multimodal food intelligence assistant.

You can receive food photos, menu photos, or text descriptions. Your job:
1. Identify each food item. For photos, estimate portion sizes in grams using visual cues
   (plate size, utensils, typical serving sizes) and state your assumptions briefly.
2. Call `analyze_meal` with the identified items to get calories and macros. Never invent
   nutrition numbers yourself when the tool can compute them. If items come back as
   'unmatched', give a clearly-labelled rough estimate for them.
3. If the user mentions a diet or health goal, use `check_diet` and `suggest_swaps`.
4. Reply concisely: a short list of detected items with portions, the totals, then 1-3
   practical suggestions. Be upfront that portion estimates from images are approximate.

You are not a medical professional. For allergies, medical conditions, or eating-disorder
concerns, recommend consulting a qualified clinician. If an image does not contain food,
say so instead of guessing."""


@dataclass
class AgentResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)


class FoodVerseAgent:
    def __init__(self, client: Any | None = None, model: str | None = None):
        if client is None:
            key = get_api_key()
            if key is None:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Copy .env.example to .env and add your Groq key."
                )
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        self.client = client
        self.model = model or get_model()
        self.history: list[dict] = []

    def reset(self) -> None:
        self.history = []

    def ask(self, text: str = "", image_bytes: bytes | None = None) -> AgentResult:
        """Send one user turn and run Groq function calls until a final answer is ready."""
        content: list[dict] = []
        if image_bytes:
            content.append(prepare_image(image_bytes))
        content.append({"type": "text", "text": text or "What is in this meal, and what are its nutrition totals?"})
        self.history.append({"role": "user", "content": content if image_bytes else content[0]["text"]})

        tool_log: list[dict] = []
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self.history],
                tools=GROQ_TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=MAX_TOKENS,
            )
            message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:
                final = message.content or "I couldn't generate a response. Please try again."
                self.history.append({"role": "assistant", "content": final})
                return AgentResult(text=final, tool_calls=tool_log)

            assistant_tool_calls = []
            for call in calls:
                assistant_tool_calls.append({
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                })
            self.history.append({"role": "assistant", "content": message.content, "tool_calls": assistant_tool_calls})

            for call in calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                output = run_tool(call.function.name, args)
                tool_log.append({"tool": call.function.name, "input": args, "output": output})
                self.history.append({"role": "tool", "tool_call_id": call.id, "content": output})

        return AgentResult(
            text="I hit the tool-call limit before finishing. Try a simpler request.",
            tool_calls=tool_log,
        )

    def ask_file(self, path: str | Path, text: str = "") -> AgentResult:
        return self.ask(text, Path(path).read_bytes())
