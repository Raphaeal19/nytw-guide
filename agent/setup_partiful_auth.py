"""
Save your Partiful browser session — run once before using scrape-partiful.

Creates a dedicated Chrome profile at agent/partiful_profile/.
That profile persists between runs so IndexedDB (Firebase auth), cookies,
and localStorage are all preserved automatically.
"""
import asyncio
import sys
from pathlib import Path

PROFILE_DIR = Path(__file__).parent / "partiful_profile"


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        print("Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    PROFILE_DIR.mkdir(exist_ok=True)
    first_time = not any(PROFILE_DIR.iterdir())

    print("=" * 55)
    print("Partiful auth setup")
    print("=" * 55)
    print(f"\nProfile directory: {PROFILE_DIR}")
    print("\nA Chrome window will open at partiful.com.")
    if first_time:
        print("Log in with your account (phone number + OTP).")
    else:
        print("If already logged in, you should see your feed immediately.")
    print("Once you can see your Partiful events feed, press Enter here.\n")

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                channel="chrome",
                headless=False,
            )
        except Exception:
            print("System Chrome not found — using bundled Chromium.")
            context = await p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
            )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://partiful.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        url = page.url
        if any(s in url for s in ("/login", "/sign-in", "/welcome", "/verify")):
            print("Detected: NOT logged in — please log in in the browser window.")
        else:
            print("Detected: already logged in ✓")

        input("\nPress Enter once you can see your Partiful events feed... ")
        await context.close()

    print(f"\n✓ Profile saved to {PROFILE_DIR}/")
    print("  (IndexedDB, cookies, localStorage all preserved)")
    print("\nYou can now run:")
    print('  python3 agent/run.py scrape-partiful "https://partiful.com/e/..." --dry-run')


if __name__ == "__main__":
    asyncio.run(main())
