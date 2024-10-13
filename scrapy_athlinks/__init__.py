"""
Use __all__ to let type checkers know what is part of the public API.
The public API is determined based on the documentation.
"""
from scrapy_athlinks.spiders.race import RaceSpider
from scrapy_athlinks.items import RaceItem, AthleteItem, AthleteSplitItem

import importlib.metadata

__version__ = importlib.metadata.version("scrapy_athlinks")

__all__ = [ 
  'AthleteItem',
  'AthleteSplitItem',
  'RaceItem',
  'RaceSpider',
  'items',
  'spiders'
]
