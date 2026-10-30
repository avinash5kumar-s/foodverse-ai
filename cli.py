"""Command-line interface.

Usage:
    python cli.py "2 chapati, dal and a bowl of rice"
    python cli.py --image meal.jpg "is this high protein?"
    python cli.py --interactive
"""

import argparse
import sys

from foodverse import FoodVerseAgent


def main() -> int:
    p = argparse.ArgumentParser(description="Food Verse AI CLI")
    p.add_argument("text", nargs="?", default="", help="Meal description or question")
    p.add_argument("--image", help="Path to a meal photo")
    p.add_argument("--interactive", "-i", action="store_true", help="Chat mode")
    p.add_argument("--show-tools", action="store_true", help="Print tool calls")
    args = p.parse_args()

    try:
        agent = FoodVerseAgent()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1

    def run(text: str, image: str | None = None) -> None:
        res = agent.ask_file(image, text) if image else agent.ask(text)
        if args.show_tools:
            for t in res.tool_calls:
                print(f"[tool] {t['tool']} {t['input']}")
        print(res.text)

    if args.interactive:
        print("Food Verse AI — type 'quit' to exit. Prefix with 'img:<path> ' to attach a photo.")
        while True:
            try:
                line = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if line.lower() in {"quit", "exit"}:
                break
            if not line:
                continue
            image = None
            if line.startswith("img:"):
                path, _, line = line[4:].partition(" ")
                image = path
            run(line, image)
        return 0

    if not args.text and not args.image:
        p.print_help()
        return 1
    run(args.text, args.image)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
