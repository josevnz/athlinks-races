"""
Use __all__ to let type checkers know what is part of the public API.
The public API is determined based on the documentation.
"""
import importlib.metadata
from athlinks_races.spiders.race import RaceSpider
from athlinks_races.items import RaceItem, AthleteItem, AthleteSplitItem

__version__ = importlib.metadata.version("athlinks_races")

__all__ = [
  'AthleteItem',
  'AthleteSplitItem',
  'RaceItem',
  'RaceSpider',
  'items',
  'spiders'
]
