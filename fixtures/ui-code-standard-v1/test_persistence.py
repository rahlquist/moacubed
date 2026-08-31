"""
Regression tests for the standard UI/code baseline fixture.

Verifies:
  1. Counter value survives a page refresh (persistence).
  2. The count element has a visually distinct treatment.
"""

import pathlib
import pytest
from playwright.sync_api import sync_playwright, Page, expect

FIXTURE_DIR = pathlib.Path(__file__).parent
INDEX_PATH = FIXTURE_DIR / "index.html"


@pytest.fixture()
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        pg = ctx.new_page()
        yield pg
        browser.close()


def _load(page: Page):
    page.goto(INDEX_PATH.as_uri())


def _increment(page: Page, times: int = 1):
    for _ in range(times):
        page.click("#increment")


def _count_value(page: Page) -> int:
    return int(page.inner_text("#count"))


def test_persistence_across_refresh(page):
    _load(page)
    _increment(page, 3)
    assert _count_value(page) == 3

    page.reload()
    assert _count_value(page) == 3, "counter did not persist across refresh"


def test_count_is_visually_distinct(page):
    _load(page)
    bg = page.evaluate(
        "el => getComputedStyle(el).backgroundColor",
        page.query_selector("#count"),
    )
    assert bg not in ("transparent", "rgba(0, 0, 0, 0)"), (
        "count element lacks a distinct visual treatment"
    )
