"""
Command line interface parser
"""
import logging
from argparse import ArgumentParser
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from textual.logging import TextualHandler

from athlinks_races import RaceSpider, AthleteItem, RaceItem
from athlinks_races.app import RaceCrawler


def main():
    """
    CLI entry point
    Returns:
    """

    parser = ArgumentParser(description=__doc__)
    athletes_location = Path.home() / "athlinks-races.json"
    parser.add_argument(
        "--athletes_rpt",
        action="store",
        type=Path,
        default=athletes_location,
        help=f"Location of the athletes race results. Default={athletes_location}"
    )
    meta_location = Path.home() / "metadata.json"
    parser.add_argument(
        "--metadata_rpt",
        action="store",
        type=Path,
        default=meta_location,
        required=False,
        help=f"Location of the race metadata results. Saved in JSON format. Default={meta_location.as_posix()}"
    )
    parser.add_argument(
        "--format",
        action="store",
        default="jsonlines",
        required=False,
        choices=["json", "jsonlines", "xml"],
        help="Override default location of the race metadata results"
    )
    default_url = "https://www.athlinks.com/event/33913/results/Event/1018673/"
    parser.add_argument(
        "--race_url",
        action="store",
        default=default_url,
        help=f"Race to crawl (Default: Crawl results for the 2022 Leadville Trail 100 Run, {default_url})",
        nargs="?"
    )
    parser.add_argument(
        '--tui',
        action="store_true",
        help="If passed, enable rich TUI with a post run report."
    )
    options = parser.parse_args()

    # Make settings for two separate output files: one for athlete data,
    # one for race metadata.
    settings = {
        'FEEDS': {
            # Athlete data. Inside this file will be a list of dicts containing
            # data about each athlete's race and splits.
            options.athletes_rpt.as_posix(): {
                'format': options.format,
                'overwrite': True,
                'item_classes': [AthleteItem],
            },
            # Race metadata. Inside this file will be a list with a single dict
            # containing info about the race itself.
            options.metadata_rpt.as_posix(): {
                'format': 'json',
                'overwrite': True,
                'item_classes': [RaceItem],
            },
        }
    }
    crawler_process = CrawlerProcess(settings=settings)
    crawler_process.crawl(RaceSpider, options.race_url)
    if not options.tui:
        crawler_process.start()
    else:
        logging.basicConfig(
            level="INFO",
            handlers=[
                TextualHandler()
            ],
        )
        app = RaceCrawler(athletes_file=options.athletes_rpt)
        app.title = "athlinks-races"
        app.crawler_process = crawler_process
        app.run(inline_no_clear=True)


if __name__ == "__main__":
    """
    Entry point
    """
    main()
