import asyncio
import os
from server.config import settings


async def _send_linkedin_dm_async(profile_url: str, message: str) -> bool:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=settings.linkedin_auth_state_path)
        page = await context.new_page()
        await page.goto(profile_url, wait_until="networkidle")
        await page.click('[aria-label="Message"]')
        await page.wait_for_selector(".msg-form__contenteditable")
        await page.fill(".msg-form__contenteditable", message)
        await page.click(".msg-form__send-button")
        await page.wait_for_timeout(1500)
        await browser.close()
    return True


def send_linkedin_dm(profile_url: str, message: str) -> bool:
    return asyncio.run(_send_linkedin_dm_async(profile_url, message))
