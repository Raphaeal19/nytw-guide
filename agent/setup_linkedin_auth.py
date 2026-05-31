"""Save browser sessions for LinkedIn and X (Twitter) — run once before first use."""
import asyncio
import sys
from pathlib import Path


async def save_session(site: str, login_url: str, out_path: Path, use_system_chrome: bool = False):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"Opening {site} login page...")
    print(f"Log in manually, then press Enter in this terminal.")
    print(f"Session will be saved to: {out_path}")

    async with async_playwright() as p:
        if use_system_chrome:
            # X blocks Playwright's bundled Chromium — use real Chrome instead
            try:
                browser = await p.chromium.launch(channel="chrome", headless=False)
            except Exception:
                print("System Chrome not found — falling back to bundled Chromium.")
                browser = await p.chromium.launch(headless=False)
        else:
            browser = await p.chromium.launch(headless=False)

        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url)

        input(f"\nPress Enter after you have logged in to {site}... ")

        await context.storage_state(path=str(out_path))
        await browser.close()

    print(f"Saved {site} session to {out_path}")


async def main():
    base = Path(__file__).parent

    print("This script saves browser sessions for LinkedIn and X (Twitter).")
    print("You will be prompted to log in to each in a browser window.\n")

    await save_session(
        site="LinkedIn",
        login_url="https://www.linkedin.com/login",
        out_path=base / "linkedin_auth.json",
    )

    await save_session(
        site="X / Twitter",
        login_url="https://x.com/i/flow/login",
        out_path=base / "twitter_auth.json",
        use_system_chrome=True,
    )

    print("\nDone. Both sessions saved.")


if __name__ == "__main__":
    asyncio.run(main())
