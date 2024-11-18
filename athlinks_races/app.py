"""
TUI application
"""
import logging
import tempfile
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from textual import work
from textual.app import App
from textual.binding import Binding
from textual.logging import TextualHandler
from textual.reactive import Reactive
from textual.widgets import Header, Footer, Log

from athlinks_races import RaceSpider


class RaceCrawler(App):
    """
    Call the crawler and present a nice summary once run is done.
    """
    crawler_process = Reactive(CrawlerProcess())

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding("ctrl+z", "suspend_process")
    ]

    def __init__(self, athletes_file: Path):
        super().__init__()
        self.athletes_file = athletes_file

    def compose(self):
        """
        Compose UI controls on the screen
        """
        yield Header(show_clock=True)
        yield Log()
        yield Footer()

    @work(exclusive=True)
    async def on_mount(self):
        """
        Render contents on the screen
        """
        self.log.logging.info("Starting crawler...")
        self.crawler_process.start()
        self.notify(
            severity="information",
            message="Done parsing",
            title="athlinks-races update",
        )
        log = self.query_one(Log)
        cnt = 0
        with open(self.athletes_file, 'r', encoding='utf-8') as f:
            for line in f:
                log.write(line)
                cnt += 1
        self.notify(
            severity="information",
            message=f"Number of racers retrieved: {cnt}",
            title="athlinks-races ",
            timeout=60
        )


def main():
    """
    Test entry point.
    """
    logging.basicConfig(
        level="INFO",
        handlers=[
            TextualHandler()
        ],
    )
    crawler_process = CrawlerProcess()
    url = "https://www.athlinks.com/event/33913/results/Event/1018673/"
    crawler_process.crawl(RaceSpider, url)
    app = RaceCrawler(Path(tempfile.mktemp()))
    app.crawler_process = crawler_process
    app.run()


if __name__ == "__main__":
    main()
