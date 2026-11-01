"""
TUI application
"""
import asyncio
import contextlib
import logging
import sys
import tempfile
from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding
from textual.logging import TextualHandler
from textual.widgets import Header, Footer, Log


class RaceCrawlerApp(App):
    """
    Run the crawler as a child process and present a nice summary once it is done.
    """

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding("ctrl+z", "suspend_process")
    ]

    def __init__(self, athletes_file: Path, crawl_cmd: list[str]):
        super().__init__()
        self.athletes_file = athletes_file
        self.crawl_cmd = crawl_cmd
        self._proc: asyncio.subprocess.Process | None = None

    def compose(self):
        """
        Compose UI controls on the screen
        """
        yield Header(show_clock=True)
        yield Log()
        yield Footer()

    def _kill_child(self):
        """
        Make sure the crawler child does not outlive the UI.
        """
        proc = self._proc
        if proc is not None and proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()

    def on_unmount(self):
        """
        Kill the child on exit.
        """
        self._kill_child()

    @work(exclusive=True)
    async def on_mount(self):
        """
        Run the crawl child process and render its output on the screen
        """
        log = self.query_one(Log)
        log.write_line("Starting crawler...")
        self._proc = await asyncio.create_subprocess_exec(
            *self.crawl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            assert self._proc.stdout is not None
            async for raw in self._proc.stdout:
                log.write_line(raw.decode("utf-8", errors="replace").rstrip("\n"))
            returncode = await self._proc.wait()
        except asyncio.CancelledError:
            self._kill_child()
            raise
        if returncode != 0:
            self.notify(
                severity="error",
                message=f"Crawler failed with exit code {returncode}",
                title="athlinks-races update",
                timeout=60,
            )
            return
        self.notify(
            severity="information",
            message="Done parsing",
            title="athlinks-races update",
        )
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
    url = "https://www.athlinks.com/event/33913/results/Event/1018673/"
    athletes = Path(tempfile.mktemp())
    crawl_cmd = [
        sys.executable, "-m", "athlinks.cli",
        "--athletes_rpt", athletes.as_posix(),
        "--metadata_rpt", Path(tempfile.mktemp()).as_posix(),
        "--race_url", url,
    ]
    app = RaceCrawlerApp(athletes, crawl_cmd)
    app.run()


if __name__ == "__main__":
    main()
