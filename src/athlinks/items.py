"""Define here the models for your scraped items

See documentation in:
https://docs.scrapy.org/en/latest/topics/items.html
"""
from scrapy import Item, Field


class AthleteItem(Item):
    """
    Data about an athlete's entire race.

    NOTE:
    * See `sample_data/individual_response.json` for other available data
    that could be of future interest.
    """
    name = Field()  # str
    bib = Field()
    gender = Field()
    country = Field()
    locality = Field()
    state = Field()
    racer_has_finished = Field()
    age = Field()
    split_data = Field()  # list(AthleteSplitItem)


class AthleteSplitItem(Item):
    """
    Data about a split recorded by an athlete in a race.

    NOTE:
    * Split data collected in selenium package: 
        split, Overall, Gender, Division, Pace, Time
    * I really only care about the split time, everything else is of
      dubious value to me.
    * See `sample_data/individual_response.json` for other available data
      that could be of future interest.
    """
    name = Field()
    time_ms = Field()
    gun_time_ms = Field()
    number = Field()
    time_with_penalties_ms = Field()
    distance_m = Field()
    interval_full = Field()


class RaceItem(Item):
    """
    Metadata about a specific running of a race.

    Example, the 2022 Leadville Trail 100 Run.

    NOTE:
    * See `sample_data/race_meta_response.json` for other available data
      that could be of future interest.
    """
    name = Field()  # str
    # athletes = Field()  # list(AthleteItem)
    # divisions = Field() # list() -> consider
    event_id = Field()
    event_course_id = Field()
    date_utc_ms = Field()
    distance_m = Field()
    split_info = Field()  # list
