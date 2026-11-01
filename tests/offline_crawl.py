"""
Run a full crawl offline, answering every request from the snapshots in sample_data.
Usage: python tests/offline_crawl.py OUTPUT_FILE [--tui]
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from scrapy.crawler import CrawlerProcess
from scrapy.http import TextResponse

from athlinks import RaceSpider, AthleteItem
from athlinks.app import RaceCrawlerApp

DATA_DIR = Path(__file__).parent.parent / 'sample_data'
RACE_URL = "https://www.athlinks.com/event/33913/results/Event/1018673/"


class SnapshotMiddleware:
    """
    Downloader middleware that never touches the network.
    """

    @staticmethod
    def process_request(request, *_args):
        """
        Map each Athlinks endpoint to its snapshot; any page past the first is empty.
        """
        url = urlparse(request.url)
        if url.path.startswith('/metadata/event/'):
            body = (DATA_DIR / 'race_meta_response.json').read_bytes()
        elif url.path.startswith('/individual'):
            body = (DATA_DIR / 'individual_response.json').read_bytes()
        elif parse_qs(url.query).get('from', ['0'])[0] == '0':
            body = (DATA_DIR / 'race_response.json').read_bytes()
        else:
            body = b'[]'
        return TextResponse(url=request.url, body=body, encoding='utf-8', request=request)


def main():
    """
    Crawl the snapshots, optionally inside the TUI (headless), and exit when done.
    """
    out = Path(sys.argv[1])
    tui = '--tui' in sys.argv
    settings = {
        'LOG_LEVEL': 'WARNING',
        'DOWNLOADER_MIDDLEWARES': {SnapshotMiddleware: 1},
        'FEEDS': {out.as_posix(): {'format': 'jsonlines', 'overwrite': True, 'item_classes': [AthleteItem]}},
    }
    if not tui:
        crawler_process = CrawlerProcess(settings=settings)
        crawler_process.crawl(RaceSpider, RACE_URL)
        crawler_process.start()
        return

    app = RaceCrawlerApp(athletes_file=out, crawl_cmd=[sys.executable, __file__, out.as_posix()])
    failures = []

    async def quit_when_done(pilot):
        # Finished workers are dropped from app.workers, so remember each one seen.
        seen = set()
        while not seen or not all(w.is_finished for w in seen):
            await asyncio.sleep(0.1)
            seen.update(app.workers)
        failures.extend(w.error for w in seen if w.error)
        await pilot.press("q")

    app.run(headless=True, auto_pilot=quit_when_done)
    if failures:
        raise SystemExit(f"TUI worker failed: {failures}")


if __name__ == "__main__":
    main()
