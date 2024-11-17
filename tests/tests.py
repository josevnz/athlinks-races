"""
Unit tests for the scraper
"""
import json
import re
import types
import unittest
from pathlib import Path
from typing import Callable, List, Any
from unittest import mock
from urllib.parse import urlparse, parse_qs

import scrapy

from athlinks_races import items
from athlinks_races.spiders import race

RACE_ID = 4984
EVENT_ID = 1017004
COURSE_ID = 2242309
EVENT_COURSE_ID = 2248652

DATA_DIR = Path(__file__).parent.parent / 'sample_data'


def load_json_file(fname):
    """

    Args:
        fname:

    Returns:

    """
    file_name = DATA_DIR / fname
    with open(file_name, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_mock_response(fname):
    """

    Args:
        fname:

    Returns:

    """
    jsonresponse = load_json_file(fname)
    return mock.Mock(
        text=json.dumps(jsonresponse)
    )


def get_dict_like(test_case, dict_like, expected_type_tups):
    """

    Args:
        test_case:
        dict_like:
        expected_type_tups:

    Returns:

    """
    for key, expected_type in expected_type_tups:
        test_case.assertIn(key, dict_like)
        test_case.assertIsInstance(dict_like[key], expected_type)


def select_by_criteria(my_list: List[Any], criteria_func: Callable):
    """

    Args:
        my_list:
        criteria_func:

    Returns:

    """
    return [o for o in my_list if criteria_func(o)]


class TestRaceSpider(unittest.TestCase):
    """
    Unit tests for the Race spider
    """

    def _test_request_and_return_parsed_url(self, request, callback):
        """Helper func that validates a request and returns a parsed url"""
        self.assertIsInstance(request, scrapy.Request)
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.callback, callback)
        parse_result = urlparse(request.url)
        self.assertIn(parse_result.netloc, race.RaceSpider.allowed_domains)
        return parse_result

    def assert_param_equals(self, query, key, val):
        """

        Args:
            query:
            key:
            val:

        Returns:

        """
        self.assertEqual(query[key][0], str(val))

    def assert_from_is_zero(self, query):
        """

        Args:
            query:

        Returns:

        """
        if 'from' in query:  # acceptable if not specified
            self.assert_param_equals(query, 'from', 0)

    def test_extract_ids(self):
        """
        Test id extraction
        Returns:

        """
        for url in [
            f'https://www.athlinks.com/event/{RACE_ID}/results/Event/{EVENT_ID}/Course/{COURSE_ID}',
            f'https://www.athlinks.com/event/{RACE_ID}/results/Event/{EVENT_ID}/Course/{COURSE_ID}/Results',
            f'https://www.athlinks.com/event/{RACE_ID}/results/Event/{EVENT_ID}/Course/{COURSE_ID}/Bib/99',
        ]:
            ids = race.extract_ids(url)
            self.assertEqual(ids[0], RACE_ID)
            self.assertEqual(ids[1], EVENT_ID)
            self.assertEqual(ids[2], COURSE_ID)

        for url in [
            f'https://www.athlinks.com/event/{RACE_ID}/results/Event/{EVENT_ID}',
            f'https://www.athlinks.com/event/{RACE_ID}/results/Event/{EVENT_ID}/Results',
        ]:
            ids = race.extract_ids(url)
            self.assertEqual(ids[0], RACE_ID)
            self.assertEqual(ids[1], EVENT_ID)
            self.assertIsNone(ids[2])

    def test_extract_bad_ids(self):
        """
        Verify correct exceptions
        Returns:

        """
        for url in [
            # NOTE: If more sophisticated input processing is implemented,
            # this should not raise an error. The event_id is actually all
            # that the scraper needs to get all its data.
            EVENT_ID, int(EVENT_ID),
            f'https://results.athlinks.com/event/{EVENT_ID}',
        ]:
            self.assertIsNotNone(url)
            with self.assertRaisesRegex(ValueError, 'Could not extract IDs'):
                race.extract_ids(EVENT_ID)  # Send an invalid value on purpose. Pisses off IDE

    def test_parse_metadata(self):
        """

        Returns:

        """
        mock_response = create_mock_response('race_meta_response.json')
        mock_spider = mock.Mock(event_id=EVENT_ID, event_course_id=None)
        result = race.RaceSpider.parse_metadata(
            mock_spider,
            mock_response)
        self.assertIsInstance(result, types.GeneratorType)

        # Expect `parse_metadata` to yield one Request for the first race page
        # and one RaceItem. Order doesn't matter.
        sequence = list(result)
        self.assertEqual(len(sequence), 2)
        requests = select_by_criteria(sequence,
                                      lambda o: isinstance(o, scrapy.Request))
        race_items = select_by_criteria(sequence,
                                        lambda o: isinstance(o, items.RaceItem))
        self.assertEqual(len(requests), 1)
        self.assertEqual(len(race_items), 1)

        # Validate the returned Request
        parse_result = self._test_request_and_return_parsed_url(requests[0],
                                                                mock_spider.parse)
        self.assertEqual(parse_result.path, f'/event/{EVENT_ID}')
        query = parse_qs(parse_result.query)
        self.assert_from_is_zero(query)

        # Validate the returned RaceItem
        race_item = race_items[0]
        get_dict_like(self, race_item, [
            ('name', str),
            ('event_id', int),
            ('event_course_id', int),
            ('distance_m', int),
            ('split_info', list),
            ('date_utc_ms', int)
        ])
        for split in race_item['split_info']:
            get_dict_like(self, split, [
                ('name', str),
                ('distance_m', int),
            ])

        # NOTE: This will fail if placed before the generator's consumption.
        # Remember: `parse_metadata` doesn't actually run until the generator
        # is consumed.
        self.assertEqual(mock_spider.event_course_id, EVENT_COURSE_ID)  # matches file

    def test_parse(self):
        """
        Test parser
        Returns:

        """
        mock_response = create_mock_response('race_response.json')
        mock_response.url = f'https://results.athlinks.com/event/{EVENT_ID}'  # ?from=10'
        mock_spider = mock.Mock(event_id=EVENT_ID, event_course_id=EVENT_COURSE_ID)
        result = race.RaceSpider.parse(
            mock_spider,
            mock_response)

        self.assertIsInstance(result, types.GeneratorType)

        # The method should return a generator with:
        #   - A Request for an athlete results page
        #     for each athlete in the json data
        #   - A Request for the next page of athlete data.
        sequence = list(result)
        athlete_requests = select_by_criteria(
            sequence,
            lambda o: isinstance(o, scrapy.Request) and bool(re.search('results.athlinks.com/individual', o.url))
        )
        race_page_requests = select_by_criteria(
            sequence,
            lambda o: isinstance(o, scrapy.Request) and bool(re.search('results.athlinks.com/event/[0-9]\\d*', o.url))
        )
        self.assertEqual(len(athlete_requests), len(sequence) - 1)
        self.assertEqual(len(race_page_requests), 1)

        bibs = []
        for request in athlete_requests:
            parse_result = self._test_request_and_return_parsed_url(request,
                                                                    mock_spider.parse_athlete)
            self.assertEqual(parse_result.path, '/individual')
            query = parse_qs(parse_result.query)
            bibs.extend(query['bib'])
            self.assert_param_equals(query, 'eventId', EVENT_ID)
            self.assert_param_equals(query, 'eventCourseId', EVENT_COURSE_ID)
        # Check uniqueness of bib numbers
        self.assertEqual(len(bibs), len(set(bibs)))

        parse_result_race = self._test_request_and_return_parsed_url(
            race_page_requests[0],
            mock_spider.parse)
        self.assertEqual(parse_result_race.path, f'/event/{EVENT_ID}')
        query_race = parse_qs(parse_result_race.query)
        # Check that the 'from' parameter is incremented (the specific
        # amount depends on the implementation)
        self.assertGreater(int(query_race['from'][0]), 0)

    def test_parse_blank(self):
        """
        Test parse blank
        Returns:

        """
        for blank_text in ['', '[]']:
            result = race.RaceSpider.parse(
                mock.Mock(),
                mock.Mock(text=blank_text)
            )
            sequence = list(result)
            self.assertEqual(len(sequence), 0)

    def test_parse_athlete(self):
        """

        Returns:

        """
        mock_response = create_mock_response('individual_response.json')
        _ = mock.Mock(event_id=EVENT_ID, event_course_id=EVENT_COURSE_ID)
        result = race.RaceSpider.parse_athlete(
            mock_response)

        # Expect method to yield one AthleteItem.
        self.assertIsInstance(result, types.GeneratorType)
        sequence = list(result)
        self.assertEqual(len(sequence), 1)
        item = sequence[0]
        self.assertIsInstance(item, items.AthleteItem)

        get_dict_like(self, item, [
            ('name', str),
            ('split_data', list),
        ])
        for split in item['split_data']:
            get_dict_like(self, split, [
                ('name', str),
                ('number', int),
                ('time_ms', int),
                ('distance_m', int),
                ('time_with_penalties_ms', int),
            ])
