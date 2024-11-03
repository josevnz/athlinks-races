# scrapy-athlinks: web scraper for race results hosted on Athlinks

[![License](https://img.shields.io/github/license/aaron-schroeder/athlinks-scraper-scrapy)](LICENSE)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-3910/)
[![PyPI](https://img.shields.io/pypi/v/scrapy-athlinks.svg)](https://pypi.python.org/pypi/scrapy-athlinks/)

## NOTE

This fork contains bug-fixes not present in the original repository. May, may not be merged ever.

For that reason I'm making it read-only.


## Introduction

<!--## Documentation

The official documentation is hosted on readthedocs.io: https://athlinks-scraper-scrapy.readthedocs.io/en/stable. -->


`scrapy-athlinks` provides the [`RaceSpider`](scrapy_athlinks/spiders/race.py) class.

This spider crawls through all results pages from a race hosted on athlinks.com,
building and following links to each athlete's individual results page, where it
collects their split data. It also collects some metadata about the race itself.

By default, the spider returns one race metadata object (`RaceItem`), and one
`AthleteItem` per participant. 
Each `AthleteItem` consists of some basic athlete info and a list of `RaceSplitItem`
containing data from each split they recorded.

## How to use this package

### Option 1: In python scripts

Scrapy can be operated entirely from python scripts.
[See the scrapy documentation for more info.](https://docs.scrapy.org/en/latest/topics/practices.html#run-scrapy-from-a-script)

#### Installation

The package is available on [PyPi](https://pypi.org/project/scrapy-athlinks) and can be installed with `pip`:

```sh
python -m venv `$HOME/virtualenv/scrapy-athlinks/`
. $HOME/virtualenv/scrapy-athlinks/bin/activate
pip install scrapy-athlinks
```

#### Example usage

[A demo script is included in this repo](scrapy_athlinks/demo.py).

```python
"""
Demonstrate the available classes.
You can run as python scrapy_athlinks/demo.py
"""
from scrapy.crawler import CrawlerProcess
from scrapy_athlinks import RaceSpider, AthleteItem, RaceItem


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
scrappy_athlinks_demo
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
python -m venv `$HOME/virtualenv/scrapy-athlinks/`
. $HOME/virtualenv/scrapy-athlinks/bin/activate
git clone https://github.com/aaron-schroeder/athlinks-scraper-scrapy
cd athlinks-scraper-scrapy
python install --editable .
```

#### Example usage

Run a `RaceSpider`, few races with different years:

```shell
cd scrapy_athlinks
scrapy crawl race -a url=https://www.athlinks.com/event/33913/results/Event/1018673 -O 1018673.json
scrapy crawl race -a url=https://www.athlinks.com/event/382111/results/Event/1093108 -O 1093108.json
scrapy crawl race -a url=https://www.athlinks.com/event/382111/results/Event/1062909 -O 1093108.json
```

## Dependencies

All that is required is [Scrapy](https://scrapy.org/) (and its dependencies).

## Testing

```
make test
```

## License

[![License](https://img.shields.io/github/license/aaron-schroeder/athlinks-scraper-scrapy)](LICENSE)

This project is licensed under the MIT License. See
[LICENSE](LICENSE) file for details.

## Contact

You can get in touch with me at the following places:

- Website: [trailzealot.com](https://trailzealot.com)
- LinkedIn: [linkedin.com/in/aarondschroeder](https://www.linkedin.com/in/aarondschroeder/)
- GitHub: [github.com/aaron-schroeder](https://github.com/aaron-schroeder)
