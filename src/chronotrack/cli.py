"""
Command line interface for the ChronoTrack results crawler
"""
import asyncio
import logging
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

from chronotrack.crawl import crawl, write_athletes, write_metadata
from chronotrack.fetch import BrowserFetcher, DiskCache, DEFAULT_CACHE_DIR

DEFAULT_URL = "https://sites.chronotrack.com/event/93943/results?raceId=249433&divisionId=2804693"


def build_parser() -> ArgumentParser:
    """Command line options"""
    parser = ArgumentParser(description=__doc__)
    athletes_location = Path.home() / "race-crawler-chronotrack.json"
    parser.add_argument("--athletes_rpt", type=Path, default=athletes_location,
                        help=f"Location of the athletes race results. Default={athletes_location}")
    meta_location = Path.home() / "race-crawler-chronotrack-metadata.json"
    parser.add_argument("--metadata_rpt", type=Path, default=meta_location,
                        help=f"Location of the race metadata results, JSON. Default={meta_location}")
    parser.add_argument("--format", default="jsonlines", choices=["json", "jsonlines", "xml"],
                        help="Format of the athletes report")
    parser.add_argument("--race_url", default=DEFAULT_URL, nargs="?",
                        help=f"Division results page to crawl. Default={DEFAULT_URL}")
    parser.add_argument("--cache_dir", type=Path, default=DEFAULT_CACHE_DIR,
                        help=f"Directory for the page cache. Default={DEFAULT_CACHE_DIR}")
    parser.add_argument("--no-cache", "--refresh", dest="refresh", action="store_true",
                        help="Ignore cached pages and load everything again with the browser")
    parser.add_argument("--offline", action="store_true",
                        help="Use only cached pages, never launch the browser; uncached athletes are skipped")
    parser.add_argument("--tui", action="store_true", help="If passed, enable rich TUI with a post run report.")
    return parser


async def run(options) -> None:
    """Crawl and write the reports"""
    start = time.monotonic()
    async with BrowserFetcher(DiskCache(options.cache_dir), refresh=options.refresh,
                              offline=options.offline) as fetcher:
        athletes, metadata, total = await crawl(fetcher, options.race_url)
        loads = fetcher.browser_loads
    write_athletes(options.athletes_rpt, athletes, options.format)
    write_metadata(options.metadata_rpt, metadata)
    logging.info("Crawled %d athletes (site total: %s), %d browser page loads, %.1fs",
                 len(athletes), total, loads, time.monotonic() - start)


def main():
    """
    CLI entry point
    """
    options = build_parser().parse_args()
    if not options.tui:
        logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
        asyncio.run(run(options))
        return

    from textual.logging import TextualHandler  # pylint: disable=import-outside-toplevel
    from athlinks.app import RaceCrawlerApp  # pylint: disable=import-outside-toplevel
    crawl_cmd = [
        sys.executable, "-m", "chronotrack.cli",
        "--athletes_rpt", options.athletes_rpt.as_posix(),
        "--metadata_rpt", options.metadata_rpt.as_posix(),
        "--format", options.format,
        "--race_url", options.race_url,
        "--cache_dir", options.cache_dir.as_posix(),
    ]
    if options.refresh:
        crawl_cmd.append("--refresh")
    if options.offline:
        crawl_cmd.append("--offline")
    logging.basicConfig(level="INFO", handlers=[TextualHandler()])
    app = RaceCrawlerApp(athletes_file=options.athletes_rpt, crawl_cmd=crawl_cmd)
    app.title = "race-crawler"
    app.run(inline_no_clear=True)


if __name__ == "__main__":
    main()
