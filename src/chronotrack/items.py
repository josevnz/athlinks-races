"""
Output records. Field names match the ones written by the athlinks crawler.
Fields that ChronoTrack does not provide are None.
"""
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class AthleteSplitItem:
    """A split (timing interval) recorded by an athlete."""
    name: str | None = None
    number: int | None = None
    time_ms: int | None = None
    gun_time_ms: int | None = None
    time_with_penalties_ms: int | None = None
    distance_m: int | None = None
    interval_full: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Plain dict representation"""
        return asdict(self)


@dataclass
class AthleteItem:  # pylint: disable=too-many-instance-attributes
    """Data about an athlete's entire race."""
    name: str | None = None
    bib: str | None = None
    age: int | None = None
    gender: str | None = None
    country: str | None = None
    locality: str | None = None
    state: str | None = None
    racer_has_finished: bool | None = None
    split_data: list[AthleteSplitItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain dict representation"""
        return asdict(self)


@dataclass
class RaceItem:
    """Metadata about a specific running of a race."""
    name: str | None = None
    event_id: int | None = None
    event_course_id: int | None = None
    date_utc_ms: int | None = None
    distance_m: int | None = None
    split_info: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Plain dict representation"""
        return asdict(self)
