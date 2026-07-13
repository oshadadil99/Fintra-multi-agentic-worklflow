"""Terminal chat with the Morgan Treasuries assistant.

Usage:
    python scripts/chat_cli.py                     # default session
    python scripts/chat_cli.py --session alice     # named session (own memory)
"""

import argparse
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

warnings.filterwarnings("ignore")  # keep the demo output clean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default="cli-local", help="conversation/session id")
    args = parser.parse_args()

    from fintra.service import answer_query

    print("Morgan Treasuries assistant - type 'exit' to quit.\n")
    while True:
        try:
            query = input("you  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            break
        result = answer_query(args.session, query)
        print(f"\n[route: {result['route']}]")
        print(f"bank > {result['answer']}\n")


if __name__ == "__main__":
    main()
