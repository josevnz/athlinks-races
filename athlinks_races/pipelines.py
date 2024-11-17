"""
Define item pipelines here

Don't forget to add your pipeline to the ITEM_PIPELINES setting
See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

'After an item has been scraped by a spider, it is sent to the Item Pipeline
which processes it through several components that are executed sequentially.'

Idea: cleaning and/or validation:
https://doc.scrapy.org/en/latest/topics/item-pipeline.html#item-pipeline-example
"""
import json

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

from athlinks_races import items

DEFAULT_DATA_FNAME = 'race.json'


class SingleJsonWriterPipeline:
    """
    Write all the race data as a single json object.

    The main functional difference from typical pipelines is that the
    items are stored in memory, then written to file all at once in
    the last step.

    Not great for memory usage generally, but let's see if it can handle
    some relatively small race result data.

    Ref:
    https://stackoverflow.com/questions/49635722/json-export-formating-in-scrapy

    NOTE: This could probably all be avoided by yielding a single RaceItem
    from the spider, then slightly modifying the JsonItemExporter, passing
    straight through `start_exporting` and just having `stop_exporting`
    call `self._beautify_newline()`.
    https://stackoverflow.com/questions/33290876/how-to-create-custom-scrapy-item-exporter
    https://docs.scrapy.org/en/latest/_modules/scrapy/exporters.html#JsonItemExporter
    """
    file = None

    def __init__(self, path_out: str = DEFAULT_DATA_FNAME):
        self.items = None
        self.path_out = path_out

    @classmethod
    def from_crawler(cls, crawler):
        """
        Return a class definition from the crawler object.
        Args:
            crawler:

        Returns:

        """
        return cls(
            path_out=crawler.settings.get('PATH_OUT', DEFAULT_DATA_FNAME)
        )

    def open_spider(self, spider):
        """
        Initialize spider pipeline
        Args:
            spider:

        Returns:

        """
        if not spider:
            raise ValueError("Missing spider argument")
        self.items = {'athletes': []}

    def close_spider(self, spider):
        """
        Flush spider contents before exiting
        Args:
            spider:

        Returns:

        """
        if not spider:
            raise ValueError("Missing spider argument")
        with open(self.path_out, 'w', encoding='utf-8') as json_file:
            json.dump(self.items, json_file, indent=2)
            json_file.flush()

    def process_item(self, item, spider):
        """
        Process an  item
        Args:
            item:
            spider:

        Returns:

        """
        if not spider:
            raise ValueError("Missing spider argument")
        if isinstance(item, items.AthleteItem):
            self.items['athletes'].append(ItemAdapter(item).asdict())
        elif isinstance(item, items.RaceItem):
            self.items.update(ItemAdapter(item).asdict())
        return item
