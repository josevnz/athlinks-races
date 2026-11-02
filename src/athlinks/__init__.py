"""
Use __all__ to let type checkers know what is part of the public API.
The public API is determined based on the documentation.
"""
import importlib.metadata
from athlinks.spiders.race import RaceSpider
from athlinks.items import RaceItem, AthleteItem, AthleteSplitItem

__version__ = importlib.metadata.version("race-crawler")

__all__ = [
  'AthleteItem',
  'AthleteSplitItem',
  'RaceItem',
  'RaceSpider',
  'items',
  'spiders'
]
