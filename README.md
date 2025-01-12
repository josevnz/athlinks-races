# athlinks_races: web scraper for race results hosted on Athlinks

![Screenshot of athlinks_races_cli --tui](athlinks_capture_screenshot.png)

## NOTE

This is a fork of the original [scrapy-athlinks](https://github.com/josevnz/scrapy-athlinks). I decided to take over 
as I want to add features that were not originally available on the project.


## Introduction


`athlinks_races` provides the [`RaceSpider`](athlinks_races/spiders/race.py) class.

This spider crawls through all results pages from a race hosted on athlinks.com,
building and following links to each athlete's individual results page, where it
collects their split data. It also collects some metadata about the race itself.

By default, the spider returns one race metadata object (`RaceItem`), and one `AthleteItem` per participant.

Each `AthleteItem` consists of some basic athlete info and a list of `RaceSplitItem` containing data from each 
split they recorded.

## How to use this package

### Option 1: In python scripts

Scrapy can be operated entirely from python scripts.
[See the scrapy documentation for more info.](https://docs.scrapy.org/en/latest/topics/practices.html#run-scrapy-from-a-script)

#### Installation

The package is available on [PyPi](https://pypi.org/project/athlinks-races) and can be installed with `pip`:

```sh
python -m venv "$HOME/virtualenv/athlinks_races/"
. $HOME/virtualenv/athlinks_races/bin/activate
pip install athlinks_races
```

#### Example usage

[A demo script is included in this repo](athlinks_races/demo.py). It has plenty of features but is also monolithic on purpose.

```python
"""
Demonstrate the available classes.
You can run as python athlinks_races/demo.py
"""
from scrapy.crawler import CrawlerProcess
from athlinks_races import RaceSpider, AthleteItem, RaceItem


def main():
    # Make settings for two separate output files: one for athlete data,
    # one for race metadata.
    settings = {
        'FEEDS': {
            # Athlete data. Inside this file will be a list of dicts containing
            # data about each athlete's race and splits.
            'athletes.json': {
                'format': 'json',
                'overwrite': True,
                'item_classes': [AthleteItem],
            },
            # Race metadata. Inside this file will be a list with a single dict
            # containing info about the race itself.
            'metadata.json': {
                'format': 'json',
                'overwrite': True,
                'item_classes': [RaceItem],
            },
        }
    }
    process = CrawlerProcess(settings=settings)

    # Crawl results for the 2022 Leadville Trail 100 Run
    process.crawl(RaceSpider, 'https://www.athlinks.com/event/33913/results/Event/1018673/')
    process.start()


if __name__ == "__main__":
    main()
```

If you do a ```pip install --editable .[lint,dev]``` then you can run as

```shell
athlinks_cli
```

Then you can build the wheelhouse to install locally if needed:

```shell
python -m build .
```

### Option 2: Command line

Alternatively, you may clone this repo for use like a typical Scrapy project
that you might create on your own.

#### Installation

```sh
python -m venv `$HOME/virtualenv/athlink_races`
. $HOME/virtualenv/athlink_races/bin/activate
git clone https://github.com/josevnz/athlinks-races
cd athlink-races
python install --editable .[lint,dev]
```

#### Example usage

Run a `RaceSpider`, few races with different years:

```shell
cd athlinks_races
scrapy crawl race -a url=https://www.athlinks.com/event/33913/results/Event/1018673 -O $HOME/1018673.json
scrapy crawl race -a url=https://www.athlinks.com/event/382111/results/Event/1093108 -O $HOME/1093108.json
scrapy crawl race -a url=https://www.athlinks.com/event/382111/results/Event/1062909 -O $HOME/1093108.json
```

Or the newer thlinks_races_cli, with the `--tui` argument:

```shell
(athlinks-races) [josevnz@dmaf5 athlinks_races]$ athlinks_races_cli --tui
2025-01-12 14:56:31 [scrapy.middleware] INFO: Enabled item pipelines:
[]
2025-01-12 14:56:31 [scrapy.core.engine] INFO: Spider opened
2025-01-12 14:56:31 [scrapy.extensions.logstats] INFO: Crawled 0 pages (at 0 pages/min), scraped 0 items (at 0 items/min)
2025-01-12 14:56:31 [scrapy.extensions.telnet] INFO: Telnet console listening on 127.0.0.1:6023
2025-01-12 14:56:31 [asyncio] DEBUG: Using selector: EpollSelector

```

## Dependencies

All that is required is [Scrapy](https://scrapy.org/) and [Textual](https://github.com/Textualize/textual) (and its dependencies).

## Testing

```shell
. $HOME/virtualenv/athlink_races/bin/activate
pytest tests/*.py
```

Example session:

```shell
(athlinks_races) [josevnz@dmaf5 athlinks_races]$ pytest /home/josevnz/athlinks_races/tests/tests.py
============================================================= test session starts =============================================================
platform linux -- Python 3.11.6, pytest-8.3.3, pluggy-1.5.0
rootdir: /home/josevnz/athlinks_races
configfile: pyproject.toml
collected 6 items                                                                                                                             

tests/tests.py ......                                                                                                                   [100%]

============================================================== 6 passed in 0.33s ==============================================================

```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Contact

You can get in touch with me here:

- GitHub: [https://github.com/josevnz](https://github.com/josevnz)

### Original Author

If you want to take a look at the original project. He is not in charge of this forked version.

- GitHub: [github.com/aaron-schroeder](https://github.com/aaron-schroeder)
