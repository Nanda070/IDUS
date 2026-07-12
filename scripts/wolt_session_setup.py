"""One-time setup: log into Wolt in a real Chrome window (using a dedicated
profile, not your daily-use one, so this doesn't conflict with Chrome you
already have open). The profile persists on disk, so tools/food_ordering.py
can reuse it headlessly afterwards without logging in again.
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).resolve().parent.parent / "config" / "wolt_chrome_profile"


def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://wolt.com")
        print("A Chrome window opened (separate profile, not your main one). Log into Wolt there.")
        input("Once you're logged in and see your account, press Enter here to finish...")
        context.close()
    print(f"Profile saved to {PROFILE_DIR}")


if __name__ == "__main__":
    main()
