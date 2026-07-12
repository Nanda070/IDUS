"""Food ordering tool - Playwright automation for Wolt.

Builds a cart and stops there. NEVER clicks checkout/payment - that boundary
is structural (there's simply no code path to it here), not a runtime check,
so no prompt-injection or model mistake can make this place a real order.
Requires a one-time login via scripts/wolt_session_setup.py.
"""

import os
import re
from pathlib import Path

# Keep the browser binary lookup consistent with scripts/wolt_session_setup.py
# (installed inside .venv, not the per-user global cache - see that file for why).
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).resolve().parent.parent / "config" / "wolt_chrome_profile"
BASE_URL = "https://wolt.com"


def order_food(restaurant: str, items: list[str]) -> str:
    """
    Search for a restaurant on Wolt and add the requested menu items to the
    cart. Does NOT place the order or pay - the user must open Wolt
    themselves to review the cart and complete checkout.

    Args:
        restaurant: Restaurant name to search for, e.g. "Pizza Mizza".
        items: Menu item names to add to the cart, e.g. ["Margherita", "Cola"].

    Returns:
        str: What was added and the cart total, or an error message if the
            restaurant/items weren't found or the Wolt session isn't set up.
    """
    if not PROFILE_DIR.exists():
        return "Сессия Wolt не настроена - сначала нужно один раз войти через scripts/wolt_session_setup.py."

    added: list[str] = []
    not_found: list[str] = []
    cart_summary = ""

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=True,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(BASE_URL, wait_until="domcontentloaded")

            search_box = page.get_by_placeholder("Search in Wolt...")
            search_box.click()
            search_box.fill(restaurant)
            page.wait_for_timeout(1500)

            restaurant_link = page.locator('a[href*="/restaurant/"]').first
            if restaurant_link.count() == 0:
                context.close()
                return f"Не нашёл ресторан «{restaurant}» на Wolt."
            restaurant_link.click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(1500)

            for item_name in items:
                card = page.locator('[data-test-id="horizontal-item-card"]').filter(
                    has=page.locator('[data-test-id="horizontal-item-card-header"]', has_text=re.compile(item_name, re.IGNORECASE))
                ).first
                if card.count() == 0:
                    not_found.append(item_name)
                    continue

                card.locator('[data-test-id="horizontal-item-card-button"]').click()
                page.wait_for_timeout(700)

                modal = page.locator('[data-test-id="product-modal-container"]')
                if modal.count() > 0:
                    confirm_button = modal.get_by_role("button", name=re.compile("Add to order", re.IGNORECASE))
                    if confirm_button.count() > 0:
                        confirm_button.first.click()
                        page.wait_for_timeout(500)
                added.append(item_name)

            cart_button = page.locator('[data-test-id="cart-view-button"]')
            if cart_button.count() > 0:
                cart_summary = cart_button.inner_text().replace("\n", " ")

            context.close()
    except Exception as exc:
        return f"Не получилось собрать корзину в Wolt: {exc}"

    parts = []
    if added:
        parts.append(f"Добавил в корзину: {', '.join(added)}.")
    if not_found:
        parts.append(f"Не нашёл в меню: {', '.join(not_found)}.")
    if cart_summary:
        parts.append(f"Корзина: {cart_summary}. Открой Wolt, чтобы проверить и оформить заказ - оплату делаешь сам.")
    return " ".join(parts) if parts else "Не получилось ничего добавить в корзину."


__all__ = ["order_food"]
