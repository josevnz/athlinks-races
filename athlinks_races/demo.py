"""
Demonstrate the available classes.
You can run as python athlinks_races/demo.py
"""
# pylint: disable=duplicate-code
from argparse import ArgumentParser
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from athlinks_races import RaceSpider, AthleteItem, RaceItem


def main():
    """
    CLI entry point
    Returns:

    """

    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--athletes",
        action="store",
        type=Path,
        default=Path.home() / "athletes.json",
        required=False,
        help="Override default location of the athletes race results"
    )
    parser.add_argument(
        "--metadata",
        action="store",
        type=Path,
        default=Path.home() / "metadata.json",
        required=False,
        help="Override default location of the race metadata results"
    )
    parser.add_argument(
        "race_url",
        action="store",
        default="https://www.athlinks.com/event/33913/results/Event/1018673/",
        help="Override default race to crawl (Default: Crawl results for the 2022 Leadville Trail 100 Run)",
        nargs="?"

    )
    options = parser.parse_args()

    # Make settings for two separate output files: one for athlete data,
    # one for race metadata.
    settings = {
      'FEEDS': {
        # Athlete data. Inside this file will be a list of dicts containing
        # data about each athlete's race and splits.
        options.athletes.as_posix(): {
          'format': 'json',
          'overwrite': True,
          'item_classes': [AthleteItem],
        },
        # Race metadata. Inside this file will be a list with a single dict
        # containing info about the race itself.
        options.metadata.as_posix(): {
          'format': 'json',
          'overwrite': True,
          'item_classes': [RaceItem],
        },
      }
    }
    process = CrawlerProcess(settings=settings)

    process.crawl(RaceSpider, options.race_url)
    process.start()


if __name__ == "__main__":
    main()
