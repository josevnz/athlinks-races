"""
Page fetching: a headless browser that loads pages like a user and records the JSON
the page itself requests (azp/ctlive paths), plus a disk cache so a crawl happens only once.
"""
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from playwright.async_api import async_playwright, Error as PlaywrightError

LOG = logging.getLogger("chronotrack.fetch")
API_MARKER = "azp/ctlive"
NAV_TIMEOUT_MS = 30_000
MAX_CONCURRENCY = 2
NAV_DELAY_S = 1.0
MAX_RETRIES = 2
DEFAULT_CACHE_DIR = Path(".cache") / "chronotrack"


@dataclass
class PageCapture:
    """What a page load produced: its __NEXT_DATA__ and the captured API JSON bodies."""
    url: str
    next_data: dict[str, Any] | None = None
    responses: list[dict[str, Any]] = field(default_factory=list)  # {"url": str, "body": parsed JSON}

    def find(self, marker: str, predicate: Callable[[str], bool] | None = None) -> Any | None:
        """First captured JSON body whose URL path ends with / contains marker and passes predicate."""
        for resp in self.responses:
            if marker in resp["url"].split("?")[0] and (predicate is None or predicate(resp["url"])):
                return resp["body"]
        return None


class CacheMiss(RuntimeError):
    """Raised in offline mode when a page is not in the cache."""


Fetcher = Callable[[str, Callable[[PageCapture], bool]], Awaitable[PageCapture]]


class DiskCache:
    """One JSON file per URL."""

    def __init__(self, directory: Path = DEFAULT_CACHE_DIR):
        self.directory = Path(directory)

    def _path(self, url: str) -> Path:
        return self.directory / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".json")

    def load(self, url: str) -> PageCapture | None:
        """Cached capture for url, or None."""
        path = self._path(url)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return PageCapture(url=data["url"], next_data=data.get("next_data"), responses=data.get("responses", []))

    def store(self, capture: PageCapture) -> None:
        """Save a capture."""
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"url": capture.url, "next_data": capture.next_data, "responses": capture.responses}
        self._path(capture.url).write_text(json.dumps(payload), encoding="utf-8")


class BrowserFetcher:  # pylint: disable=too-many-instance-attributes
    """
    Async context manager. Call it as `await fetcher(url, is_complete)`; cache first, browser second.
    `is_complete(capture)` says whether the capture has the data the caller needs (else it is retried).
    """

    def __init__(self, cache: DiskCache | None, refresh: bool = False, offline: bool = False):
        self.cache = cache
        self.refresh = refresh
        self.offline = offline
        self._playwright = None
        self._browser = None
        self._sem = asyncio.Semaphore(MAX_CONCURRENCY)
        self._nav_lock = asyncio.Lock()
        self._last_nav = 0.0
        self.browser_loads = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _ensure_browser(self):
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def _polite_delay(self):
        async with self._nav_lock:
            wait = NAV_DELAY_S - (time.monotonic() - self._last_nav)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_nav = time.monotonic()

    async def _load(self, url: str) -> PageCapture:
        browser = await self._ensure_browser()
        page = await browser.new_page()
        tasks: list[asyncio.Task] = []
        capture = PageCapture(url=url)

        async def on_response(resp):
            if API_MARKER not in resp.url or resp.request.resource_type not in ("fetch", "xhr"):
                return
            try:
                capture.responses.append({"url": resp.url, "body": json.loads(await resp.text())})
            except (PlaywrightError, ValueError, UnicodeDecodeError):
                LOG.debug("Skipping non-JSON response %s", resp.url)

        page.on("response", lambda r: tasks.append(asyncio.ensure_future(on_response(r))))
        try:
            await self._polite_delay()
            await page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="networkidle")
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=NAV_TIMEOUT_MS / 1000)
            raw = await page.evaluate("document.getElementById('__NEXT_DATA__')?.textContent")
            capture.next_data = json.loads(raw) if raw else None
        finally:
            await page.close()
        self.browser_loads += 1
        return capture

    async def __call__(self, url: str, is_complete: Callable[[PageCapture], bool]) -> PageCapture:
        if self.cache and not self.refresh:
            cached = self.cache.load(url)
            if cached is not None:
                return cached
        if self.offline:
            raise CacheMiss(f"Not cached (offline mode): {url}")
        async with self._sem:
            last_error: Exception | None = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    capture = await self._load(url)
                    if is_complete(capture):
                        if self.cache:
                            self.cache.store(capture)
                        return capture
                    last_error = RuntimeError(f"Expected data not captured from {url}")
                except (PlaywrightError, asyncio.TimeoutError) as err:
                    last_error = err
                LOG.warning("Attempt %d for %s failed: %s", attempt + 1, url, last_error)
            raise RuntimeError(f"Giving up on {url}: {last_error}")


def sample_fetcher(mapping: dict[str, PageCapture]) -> Fetcher:
    """A fetcher that answers from in-memory captures (used by offline tests)."""
    async def _fetch(url: str, is_complete: Callable[[PageCapture], bool]) -> PageCapture:
        if url not in mapping:
            raise CacheMiss(f"No sample for {url}")
        capture = mapping[url]
        if not is_complete(capture):
            raise RuntimeError(f"Sample for {url} is incomplete")
        return capture
    return _fetch
