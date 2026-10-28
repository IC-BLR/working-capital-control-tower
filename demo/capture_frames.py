#!/usr/bin/env python3
"""Capture full 1920x1080 screens — wait until real data is visible (no empty/skeleton frames)."""
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:3000"
OUT = Path(__file__).resolve().parent / "frames"
OUT.mkdir(exist_ok=True)
W, H = 1920, 1080


def shot(page, name: str, settle_ms: int = 500):
    page.wait_for_timeout(settle_ms)
    page.screenshot(path=str(OUT / name), full_page=False)
    print(f"saved {name}")


def wait_text(page, pattern: str, timeout: int = 25000):
    page.wait_for_function(
        """(pat) => new RegExp(pat, 'i').test(document.body.innerText)""",
        arg=pattern,
        timeout=timeout,
    )


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
        ).new_page()
        page.set_default_timeout(30000)

        # 01 Login
        page.goto(f"{BASE}/login", wait_until="domcontentloaded")
        page.wait_for_selector("form")
        expect(page.get_by_role("heading", name="Working Capital Control Tower")).to_be_visible()
        shot(page, "01_login.png")

        page.fill("#email", "ap.analyst@demo.com")
        page.fill("#password", "Demo@123")
        page.click("button[type=submit]")
        page.wait_for_selector("text=Cash Calendar")

        # 02 Cash Calendar
        page.get_by_role("button", name="30 days").click()
        page.locator("#wc-scenario").select_option("baseline")
        wait_text(page, r"EXPECTED INFLOWS[\s\S]{0,80}₹\s*[1-9]")
        wait_text(page, r"NET WC SIGNAL")
        wait_text(page, r"INV-PART")
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "02_calendar.png", 700)

        # 03 AR portfolio
        page.goto(f"{BASE}/ar/dashboard", wait_until="domcontentloaded")
        wait_text(page, r"CFO Executive Dashboard")
        wait_text(page, r"Total Outstanding[\s\S]{0,80}₹\s*[1-9]")
        wait_text(page, r"Total Overdue[\s\S]{0,80}₹\s*[1-9]")
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "03_ar_portfolio.png", 900)

        # 04 AR partners ranking
        page.goto(f"{BASE}/ar/partners", wait_until="domcontentloaded")
        wait_text(page, r"PART000")
        wait_text(page, r"Outstanding")
        wait_text(page, r"Showing 1 to \d+ of [1-9]")
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "04_ar_partners.png", 600)

        # 05 Invoice level — invoices list with rows
        page.goto(f"{BASE}/ar/invoices", wait_until="domcontentloaded")
        wait_text(page, r"Invoice-level|Invoices")
        # Retry refresh if still skeleton/zero
        for attempt in range(4):
            body = page.inner_text("body")
            if "INV-" in body and "Total Invoices" in body and "Total Invoices\n0" not in body.replace(" ", ""):
                # also reject pure zero summary
                if "Showing 1" in body and "of 0" not in body:
                    break
            if "INV-" in body and "of 0" not in body:
                break
            page.wait_for_timeout(1500)
            if attempt == 1:
                page.reload(wait_until="domcontentloaded")
            if attempt == 2:
                # navigate away and back
                page.goto(f"{BASE}/ar/partners", wait_until="domcontentloaded")
                page.wait_for_timeout(800)
                page.goto(f"{BASE}/ar/invoices", wait_until="domcontentloaded")
        wait_text(page, r"INV-", timeout=35000)
        # Ensure not stuck on zeros
        page.wait_for_function(
            """() => {
              const t = document.body.innerText.replace(/\\s+/g, ' ');
              return /INV-/.test(t) && !/Total Invoices 0 Overdue 0/.test(t) && !/of 0/.test(t);
            }""",
            timeout=35000,
        )
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "05_ar_invoice.png", 700)

        # 06 AP portfolio — wait past refreshing empty state
        page.goto(f"{BASE}/ap/", wait_until="domcontentloaded")
        wait_text(page, r"Control Tower")
        if page.get_by_role("button", name="Refresh").count():
            page.get_by_role("button", name="Refresh").click()
        page.wait_for_function(
            """() => {
              const t = document.body.innerText.replace(/\\s+/g, ' ');
              if (/Refreshing/.test(t)) return false;
              const hasKpi = /Invoices\\s*[1-9]/.test(t) || /Exceptions\\s*[1-9]/.test(t);
              const hasMoney = /Exposure\\s*\\$[1-9]|770,?800|Financial|₹/.test(t);
              const hasContent = /ApexCloud|INV-PO|Active regulations|PO-backed|Exception/.test(t);
              return hasKpi && hasContent;
            }""",
            timeout=40000,
        )
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "06_ap_portfolio.png", 800)

        # 07 AP blocked invoice
        page.get_by_role("button", name="Invoice Approval").click()
        wait_text(page, r"INV-")
        if page.locator("text=INV-PO-1002").count():
            page.locator("text=INV-PO-1002").first.click()
        page.wait_for_timeout(1000)
        wait_text(page, r"Blocked|Exception|Payment Ready")
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "07_ap_invoice.png", 600)

        # 08 AI Assistant with live answer
        page.goto(f"{BASE}/ar/chatbot", wait_until="domcontentloaded")
        wait_text(page, r"AI Assistant")
        chip = page.get_by_text("What is the total outstanding amount?")
        if chip.count():
            chip.first.click()
        else:
            page.locator("textarea").first.fill("What is the total outstanding amount?")
            page.locator("textarea").first.press("Enter")
        page.wait_for_function(
            """() => {
              const t = document.body.innerText;
              return /Total Outstanding Summary|Total Outstanding Amount/i.test(t)
                  && /[0-9]{1,3}(,[0-9]{2,3})+/.test(t);
            }""",
            timeout=50000,
        )
        page.wait_for_timeout(1200)
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "08_assistant.png", 500)

        # 09 Close
        page.goto(f"{BASE}/", wait_until="domcontentloaded")
        wait_text(page, r"EXPECTED INFLOWS[\s\S]{0,80}₹\s*[1-9]")
        page.evaluate("window.scrollTo(0, 0)")
        shot(page, "09_close.png", 600)

        browser.close()
        print("done")


if __name__ == "__main__":
    main()
