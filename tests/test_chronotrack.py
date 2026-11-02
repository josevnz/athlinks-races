"""
Unit tests for the ChronoTrack crawler. No browser, no network: everything is read from sample_data/chronotrack.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from chronotrack import parse
from chronotrack.crawl import crawl, entry_url, results_url, write_athletes, write_metadata
from chronotrack.fetch import PageCapture, sample_fetcher

DATA_DIR = Path(__file__).parent.parent / 'sample_data' / 'chronotrack'
RACE_URL = "https://sites.chronotrack.com/event/93943/results?raceId=249433&divisionId=2804693"
INTERVAL_ORDER = [660830, 660831, 660832]


def load_capture(name: str) -> PageCapture:
    """Load a sample page capture"""
    data = json.loads((DATA_DIR / f"{name}.json").read_text(encoding='utf-8'))
    return PageCapture(url=data["url"], next_data=data["next_data"], responses=data["responses"])


def body(capture: PageCapture) -> dict:
    """The single API response kept in a sample"""
    return capture.responses[0]["body"]


class TestParse(unittest.TestCase):
    """
    Parsing functions
    """

    def test_parse_race_url(self):
        """
        Ids and origin come from the results URL
        """
        self.assertEqual(
            {"origin": "https://sites.chronotrack.com", "event_id": 93943, "race_id": 249433, "division_id": 2804693},
            parse.parse_race_url(RACE_URL)
        )
        self.assertIsNone(parse.parse_race_url("https://sites.chronotrack.com/event/93943/results")["race_id"])

    def test_parse_metadata(self):
        """
        Race metadata from __NEXT_DATA__
        """
        metadata = parse.parse_metadata(load_capture("results_page_1").next_data, 249433)
        self.assertEqual("Empire State Building Observation Deck Run-Up", metadata.name)
        self.assertEqual(93943, metadata.event_id)
        self.assertEqual(249433, metadata.event_course_id)
        self.assertEqual(1791331200000, metadata.date_utc_ms)
        self.assertEqual(320, metadata.distance_m)
        self.assertEqual(
            [{"name": "Full Course", "distance_m": 320}, {"name": "20th Floor", "distance_m": 61},
             {"name": "65th Floor", "distance_m": 229}],
            metadata.split_info
        )

    def test_parse_results_page(self):
        """
        Entry ids from the results list, including athletes who did not finish
        """
        page_1 = body(load_capture("results_page_1"))
        ids = parse.parse_results_page(page_1)
        self.assertEqual(50, len(ids))
        self.assertEqual(80710407, ids[0])
        self.assertEqual(356, parse.parse_total(page_1))

        last = parse.parse_results_page(body(load_capture("results_page_8")))
        self.assertEqual(6, len(last))
        self.assertIn(80718131, last)  # only reached the 20th floor

        self.assertEqual([], parse.parse_results_page(body(load_capture("results_page_9_empty"))))

    def test_results_from(self):
        """
        Pagination offset of an API URL
        """
        capture = load_capture("results_page_8")
        self.assertEqual(350, parse.results_from(capture.responses[0]["url"]))
        self.assertIsNone(parse.results_from("https://example.com/results"))

    def test_parse_athlete(self):
        """
        Athlete record with splits in metadata order
        """
        athlete = parse.parse_athlete(body(load_capture("entry_80710407")), INTERVAL_ORDER)
        self.assertEqual("Ryoji Watanabe", athlete.name)
        self.assertEqual("16", athlete.bib)
        self.assertEqual(42, athlete.age)
        self.assertEqual("M", athlete.gender)
        self.assertEqual("JP", athlete.country)
        self.assertEqual("Tokyo", athlete.locality)
        self.assertEqual("Tokyo", athlete.state)
        self.assertTrue(athlete.racer_has_finished)
        self.assertEqual(["Full Course", "20th Floor", "65th Floor"], [s.name for s in athlete.split_data])
        self.assertEqual([1, 2, 3], [s.number for s in athlete.split_data])
        full = athlete.split_data[0]
        self.assertEqual(677650, full.time_ms)
        self.assertEqual({"timeInMillis": 678360, "timeUnit": "m"}, full.gun_time_ms)
        self.assertEqual(320, full.distance_m)
        self.assertTrue(full.interval_full)
        self.assertIsNone(full.time_with_penalties_ms)
        self.assertEqual(119160, athlete.split_data[1].time_ms)
        self.assertEqual(61, athlete.split_data[1].distance_m)

    def test_parse_athlete_did_not_finish(self):
        """
        Real athlete who stopped at the 20th floor: no full course time
        """
        athlete = parse.parse_athlete(body(load_capture("entry_80718131")), INTERVAL_ORDER)
        self.assertEqual("Bradley Borr", athlete.name)
        self.assertEqual("62", athlete.bib)
        self.assertEqual("New Jersey", athlete.state)
        self.assertFalse(athlete.racer_has_finished)
        self.assertEqual([1, 2, 3], [s.number for s in athlete.split_data])
        self.assertEqual([None, 314690, None], [s.time_ms for s in athlete.split_data])
        self.assertEqual({"timeInMillis": 763890, "timeUnit": "m"}, athlete.split_data[1].gun_time_ms)
        self.assertIsNone(athlete.split_data[0].gun_time_ms)

    def test_parse_athlete_missing_fields(self):
        """
        Missing data becomes None, never invented
        """
        athlete = parse.parse_athlete({"displayName": "Someone"})
        self.assertEqual("Someone", athlete.name)
        self.assertIsNone(athlete.bib)
        self.assertIsNone(athlete.country)
        self.assertFalse(athlete.racer_has_finished)
        self.assertEqual([], athlete.split_data)


class TestStateName(unittest.TestCase):
    """
    Region code -> subdivision name, following the athlinks convention.
    """

    def test_tokyo(self):
        """Japanese prefecture code."""
        self.assertEqual("Tokyo", parse.state_name("JP", "13"))

    def test_us_state(self):
        """US state code, with or without the country prefix."""
        self.assertEqual("New York", parse.state_name("US", "NY"))
        self.assertEqual("New York", parse.state_name("US", "US-NY"))

    def test_unresolvable(self):
        """Unknown codes are kept as they are; no region becomes '-'."""
        self.assertEqual("99", parse.state_name("XX", "99"))
        self.assertEqual("-", parse.state_name("US", None))


class TestOfflineCrawl(unittest.TestCase):
    """
    Whole pipeline against the samples: results page 1, results page 8 (has the athlete who
    did not finish), the empty page 9 and four athletes.
    Athletes without a sample are skipped, like an offline run with an incomplete cache.
    """

    def setUp(self):
        ids = parse.parse_race_url(RACE_URL)
        def as_page(sample: str, page: int, sample_from: int) -> PageCapture:
            """Serve a sampled results page as if it were page number `page`"""
            capture = load_capture(sample)
            return PageCapture(
                url=results_url(ids, page),
                next_data={},
                responses=[{"url": r["url"].replace(f"from={sample_from}", f"from={(page - 1) * 50}"),
                            "body": r["body"]} for r in capture.responses]
            )

        # Only pages 1, 8 and 9 are sampled: page 8 (with the athlete who did not finish) stands in for page 2
        mapping = {
            results_url(ids, 1): load_capture("results_page_1"),
            results_url(ids, 2): as_page("results_page_8", 2, 350),
            results_url(ids, 3): as_page("results_page_9_empty", 3, 400),
        }
        for entry_id in (80710407, 80710127, 80710614, 80718131):
            mapping[entry_url(ids, entry_id)] = load_capture(f"entry_{entry_id}")
        self.fetcher = sample_fetcher(mapping)

    def test_crawl(self):
        """
        Crawl, then write every output format
        """
        athletes, metadata, total = asyncio.run(crawl(self.fetcher, RACE_URL))
        self.assertEqual(356, total)
        self.assertEqual(["Ryoji Watanabe", "Blanca Romero", "Rachel Sternberg", "Bradley Borr"],
                         [a.name for a in athletes])
        self.assertEqual([True, True, True, False], [a.racer_has_finished for a in athletes])
        self.assertEqual(93943, metadata.event_id)

        with tempfile.TemporaryDirectory() as tmp:
            jsonlines = Path(tmp) / "athletes.jsonl"
            write_athletes(jsonlines, athletes, "jsonlines")
            records = [json.loads(line) for line in jsonlines.read_text(encoding='utf-8').splitlines()]
            self.assertEqual(4, len(records))
            self.assertEqual(677650, records[0]["split_data"][0]["time_ms"])

            as_json = Path(tmp) / "athletes.json"
            write_athletes(as_json, athletes, "json")
            self.assertEqual(records, json.loads(as_json.read_text(encoding='utf-8')))

            as_xml = Path(tmp) / "athletes.xml"
            write_athletes(as_xml, athletes, "xml")
            self.assertIn("<name>Ryoji Watanabe</name>", as_xml.read_text(encoding='utf-8'))

            meta = Path(tmp) / "metadata.json"
            write_metadata(meta, metadata)
            self.assertEqual("Empire State Building Observation Deck Run-Up",
                             json.loads(meta.read_text(encoding='utf-8'))[0]["name"])


if __name__ == '__main__':
    unittest.main()
