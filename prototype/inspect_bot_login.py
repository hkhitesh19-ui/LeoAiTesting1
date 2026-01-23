# prototype/inspect_bot_login.py
"""
Inspect bot.shoonya_login source code so we can see why it returns False.
SAFE: does not print secrets, only prints function source.
"""

import sys
from pathlib import Path
import inspect

def main():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    import bot

    print("bot.py:", bot.__file__)
    print("\n========== shoonya_login SOURCE ==========\n")
    print(inspect.getsource(bot.shoonya_login))
    print("\n========== END ==========\n")

if __name__ == "__main__":
    main()
