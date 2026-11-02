"""
Crawl pipeline and output writers. Independent of how pages are fetched (see fetch.py).
"""
import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from chronotrack import parse
from chronotrack.fetch import CacheMiss, Fetcher, PageCapture
from chronotrack.items import AthleteItem, RaceItem

LOG = logging.getLogger("chronotrack.crawl")
MAX_PAGES = 200  # safety net


def results_url(ids: dict[str, Any], page: int) -> str:
    """Canonical results page URL for a page number (1-based)."""
    return (f"{ids['origin']}/event/{ids['event_id']}/results"
            f"?raceId={ids['race_id']}&divisionId={ids['division_id']}&page={page}")


def entry_url(ids: dict[str, Any], entry_id: int) -> str:
    """Athlete entry page URL."""
    return f"{ids['origin']}/event/{ids['event_id']}/results/entry/{entry_id}"


def _division_results(ids: dict[str, Any], page: int):
    """Predicate/finder for the list response that belongs to a page number."""
    wanted_from = (page - 1) * parse.PAGE_SIZE
    marker = f"/division/{ids['division_id']}/results"

    def match(capture: PageCapture):
        return capture.find(marker, lambda u: parse.results_from(u) == wanted_from)
    return match


async def collect_entry_ids(fetch: Fetcher, ids: dict[str, Any]) -> tuple[list[int], PageCapture, int | None]:
    """Load results pages 1..N until a page adds no new entries. Returns ids, first page capture, site total."""
    seen: list[int] = []
    known = set()
    first: PageCapture | None = None
    total = None
    for page in range(1, MAX_PAGES + 1):
        finder = _division_results(ids, page)
        capture = await fetch(results_url(ids, page), lambda c, f=finder: f(c) is not None and c.next_data is not None)
        payload = finder(capture)
        if page == 1:
            first = capture
            total = parse.parse_total(payload)
        new = [i for i in parse.parse_results_page(payload) if i not in known]
        LOG.info("Results page %d: %d new entries", page, len(new))
        if not new:
            break
        known.update(new)
        seen.extend(new)
    return seen, first, total


async def fetch_athlete(fetch: Fetcher, ids: dict[str, Any], entry_id: int, interval_order: list[int]) -> AthleteItem | None:
    """Load one entry page and parse it."""
    def has_result(capture: PageCapture):
        return capture.find(f"/entry/{entry_id}/result") is not None
    try:
        capture = await fetch(entry_url(ids, entry_id), has_result)
    except CacheMiss as miss:
        LOG.warning("%s", miss)
        return None
    return parse.parse_athlete(capture.find(f"/entry/{entry_id}/result"), interval_order)


async def crawl(fetch: Fetcher, race_url: str) -> tuple[list[AthleteItem], RaceItem, int | None]:
    """Crawl every athlete of the division in race_url."""
    ids = parse.parse_race_url(race_url)
    if None in (ids["event_id"], ids["race_id"], ids["division_id"]):
        raise ValueError("race_url needs /event/<id>/ and raceId and divisionId parameters")
    entry_ids, first, total = await collect_entry_ids(fetch, ids)
    metadata = parse.parse_metadata(first.next_data, ids["race_id"])
    race = parse.find_race(first.next_data, ids["race_id"]) or {}
    order = [i["id"] for i in sorted(race.get("intervals") or [], key=lambda i: i.get("displayOrder", 0))]
    athletes = await asyncio.gather(*(fetch_athlete(fetch, ids, eid, order) for eid in entry_ids))
    return [a for a in athletes if a is not None], metadata, total


def write_athletes(path: Path, athletes: list[AthleteItem], fmt: str) -> None:
    """Write athletes as json, jsonlines or xml."""
    records = [a.to_dict() for a in athletes]
    path = Path(path)
    if fmt == "jsonlines":
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    elif fmt == "json":
        path.write_text(json.dumps(records, indent=1), encoding="utf-8")
    elif fmt == "xml":
        root = ET.Element("items")
        for rec in records:
            _to_xml(ET.SubElement(root, "item"), rec)
        ET.indent(root)
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    else:
        raise ValueError(f"Unknown format {fmt}")


def _to_xml(parent: ET.Element, value: Any) -> None:
    if isinstance(value, dict):
        for key, val in value.items():
            _to_xml(ET.SubElement(parent, key), val)
    elif isinstance(value, list):
        for val in value:
            _to_xml(ET.SubElement(parent, "value"), val)
    elif value is not None:
        parent.text = str(value).lower() if isinstance(value, bool) else str(value)


def write_metadata(path: Path, metadata: RaceItem) -> None:
    """Metadata: JSON list with one dict."""
    Path(path).write_text(json.dumps([metadata.to_dict()], indent=1), encoding="utf-8")
