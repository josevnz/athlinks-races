"""
Pure parsing functions: no network, no browser.
"""
import json
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

import pycountry

from chronotrack.items import AthleteItem, AthleteSplitItem, RaceItem

PAGE_SIZE = 50
_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse_race_url(url: str) -> dict[str, Any]:
    """
    Extract event, race and division ids from a results URL.
    Returns a dict with event_id, race_id, division_id (ints, or None when missing) and origin.
    """
    parsed = urlparse(url)
    match = re.search(r"/event/(\d+)", parsed.path)
    query = parse_qs(parsed.query)

    def _int(key):
        values = query.get(key)
        return int(values[0]) if values else None

    return {
        "origin": f"{parsed.scheme}://{parsed.netloc}",
        "event_id": int(match.group(1)) if match else None,
        "race_id": _int("raceId"),
        "division_id": _int("divisionId"),
    }


def extract_next_data(html: str) -> dict[str, Any] | None:
    """Return the parsed __NEXT_DATA__ JSON from raw page HTML, or None."""
    match = _NEXT_DATA_RE.search(html)
    return json.loads(match.group(1)) if match else None


def _meters(distance: dict[str, Any] | None) -> int | None:
    if not distance:
        return None
    value = distance.get("meters")
    return None if value is None else int(round(value))


def find_race(next_data: dict[str, Any], race_id: int | None) -> dict[str, Any] | None:
    """Pick the race with race_id (or the only/first race when race_id is None)."""
    races = next_data["props"]["pageProps"]["eventMetadata"].get("races") or []
    for race in races:
        if race_id is None or race.get("id") == race_id:
            return race
    return None


def parse_metadata(next_data: dict[str, Any], race_id: int | None = None) -> RaceItem:
    """
    __NEXT_DATA__ -> race metadata.
    event_course_id is the ChronoTrack race id (the closest equivalent of an athlinks course).
    distance_m is the distance of the full course interval.
    """
    event = next_data["props"]["pageProps"]["eventMetadata"]
    race = find_race(next_data, race_id)
    intervals = sorted((race or {}).get("intervals") or [], key=lambda i: i.get("displayOrder", 0))
    full_id = (race or {}).get("fullCourseIntervalId")
    full = next((i for i in intervals if i.get("id") == full_id), None)
    return RaceItem(
        name=event.get("name"),
        event_id=event.get("id"),
        event_course_id=(race or {}).get("id"),
        date_utc_ms=event.get("startTimeMs"),
        distance_m=_meters(full["distance"]) if full else None,
        split_info=[{"name": i.get("name"), "distance_m": _meters(i.get("distance"))} for i in intervals],
    )


def parse_results_page(payload: dict[str, Any]) -> list[int]:
    """
    Results list JSON -> entry ids, in the order shown.
    Finishers are listed under the full course interval; athletes who did not finish appear
    under the last split they reached, so every interval is read (without duplicates).
    """
    ids: list[int] = []
    for interval in payload.get("intervals") or []:
        for result in interval.get("results") or []:
            if "id" in result and result["id"] not in ids:
                ids.append(result["id"])
    return ids


def results_from(url: str) -> int | None:
    """The `from` query value of a results API URL."""
    values = parse_qs(urlparse(url).query).get("from")
    return int(values[0]) if values else None


def parse_total(payload: dict[str, Any]) -> int | None:
    """Total athletes reported by the division, if present."""
    return (payload.get("division") or {}).get("totalAthletes")


def _gun_time(millis: int | None) -> dict[str, Any] | None:
    """Gun time in the same shape athlinks uses."""
    return None if millis is None else {"timeInMillis": millis, "timeUnit": "m"}


def state_name(country: str | None, region: str | None) -> str:
    """
    ChronoTrack region code (ISO 3166-2 subdivision, e.g. "13" for Tokyo) -> subdivision name, like athlinks.
    "-" when there is no region (athlinks convention); the raw code when it cannot be resolved.
    """
    if not region:
        return "-"
    code = region if "-" in region else f"{country}-{region}"
    try:
        subdivision = pycountry.subdivisions.get(code=code.upper())
    except (KeyError, LookupError):
        subdivision = None
    return subdivision.name if subdivision else region


def parse_athlete(payload: dict[str, Any], interval_order: list[int] | None = None) -> AthleteItem:
    """
    Entry result JSON -> athlete record.
    interval_order is the list of interval ids from the event metadata; it gives each split a stable
    `number` (1-based). Without it, splits are numbered in the order returned.
    time_with_penalties_ms is not provided by ChronoTrack and stays None.
    """
    location = payload.get("location") or {}
    raw = (payload.get("result") or {}).get("intervals") or []
    if interval_order:
        raw = sorted(raw, key=lambda i: interval_order.index(i["id"]) if i.get("id") in interval_order else len(interval_order))
    splits = []
    for idx, interval in enumerate(raw, start=1):
        number = idx
        if interval_order and interval.get("id") in interval_order:
            number = interval_order.index(interval["id"]) + 1
        splits.append(AthleteSplitItem(
            name=interval.get("name"),
            number=number,
            time_ms=interval.get("chipTimeInMillis"),
            gun_time_ms=_gun_time(interval.get("gunTimeInMillis")),
            time_with_penalties_ms=None,
            distance_m=_meters(interval.get("distance")),
            interval_full=interval.get("full"),
        ))
    finished = any(s.interval_full and s.time_ms is not None for s in splits)
    return AthleteItem(
        name=payload.get("displayName"),
        bib=payload.get("bib"),
        age=payload.get("age"),
        gender=payload.get("gender"),
        country=location.get("country"),
        locality=location.get("locality"),
        state=state_name(location.get("country"), location.get("region")),
        racer_has_finished=finished,
        split_data=splits,
    )
