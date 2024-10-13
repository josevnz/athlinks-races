import json
import re
from urllib.parse import urlparse, parse_qs

from scrapy import FormRequest, Request, Spider

from scrapy_athlinks.items import AthleteItem, AthleteSplitItem, RaceItem

MAX_RESULT_LIMIT = 100  # As high as Athlinks will accept


class RaceSpider(Spider):
    name = 'race'
    allowed_domains = ['results.athlinks.com']

    def __init__(self, url=None, **kwargs):
        super().__init__(url=url, **kwargs)

        # TODO? More advanced input processing. All we actually need to
        # get going is the event_id.
        # url = process_inputs(url, event_id, event_course_id)

        # Not sure if 0 (master_event_id) or 2 (course_id) are ever needed.
        self.master_event_id, self.event_id, self.course_id = extract_ids(url)
        self.event_course_id = None

    def start_requests(self):
        yield Request(
            url=f'https://results.athlinks.com/metadata/event/{self.event_id}',
            callback=self.parse_metadata
        )

    def parse_metadata(self, response):
        jsonresponse = json.loads(response.text)

        # This attribute must be present on the RaceSpider instance for
        # it to construct urls for individual athlete result pages.
        self.event_course_id = jsonresponse['eventCourseMetadata'][0]['eventCourseId']

        yield json_to_race_item(jsonresponse)

        yield create_race_page_request(self, first_result_num=0)

    def parse(self, response):
        # Check if we have reached the end of results pages
        if response.text == '':
            return
        jsonresponse = json.loads(response.text)
        if len(jsonresponse) == 0:  # []
            return

        athletes_data = jsonresponse[0]['interval']['intervalResults']

        # Parse each athlete's results page and return an athlete item.
        for athlete_data in athletes_data:
            yield create_athlete_request(self, athlete_data['bib'])

        # Request another page of athlete data.
        # (May or may not have any athletes, but gotta check)
        queries = parse_qs(urlparse(response.url).query)
        try:
            cur_start_result = int(queries['from'][0])
        except KeyError:  # must have been first page
            cur_start_result = 0
        next_start_result = cur_start_result + MAX_RESULT_LIMIT
        yield create_race_page_request(self, first_result_num=next_start_result)

    def parse_athlete(self, response):
        """
    Ref:
      https://stackoverflow.com/questions/42610814/scrapy-yield-items-as-sub-items-in-json
    """
        jsonresponse = json.loads(response.text)

        yield AthleteItem(
            name=jsonresponse['displayName'],
            split_data=[
                AthleteSplitItem(
                    name=split['intervalName'],
                    number=split['intervalOrder'],  # think this is visual-only
                    time_ms=split['pace']['time']['timeInMillis'],
                    distance_m=split['pace']['distance']['distanceInMeters'],
                    time_with_penalties_ms=split['timeWithPenalties']['timeInMillis'],
                )
                for split in jsonresponse['intervals']
            ]
        )


def extract_ids(race_url):
    err_potential = ValueError(f'Could not extract IDs from race url: {race_url}')
    regexp = r'/event\/([0-9]\d*)\/results\/Event\/([0-9]\d*)(?:\/Course\/([0-9]\d*))?'
    try:
        s = re.search(regexp, race_url)
    except TypeError:
        raise err_potential
    if not bool(s):
        raise err_potential
    return tuple(int(i) if isinstance(i, str) else i for i in s.groups())


def json_to_race_item(jsonresponse):
    return RaceItem(
        name=jsonresponse['eventName'],
        event_id=jsonresponse['eventId'],
        event_course_id=jsonresponse['eventCourseMetadata'][0]['eventCourseId'],
        distance_m=jsonresponse['eventCourseMetadata'][0]['distance'],
        split_info=[
            {
                'name': split['name'],
                'distance_m': split['distance'],
                # Curious what this could be other than 'course'
                # Leaving it here to remind me to investigate
                # 'intervalType': split['intervalType']
            }
            for split in jsonresponse['eventCourseMetadata'][0]['metadata']['intervals']
        ],
        date_utc_ms=jsonresponse['eventStartDateTime']['timeInMillis']  # is this typically done?
    )


def create_race_page_request(race_spider, first_result_num=0):
    """
  
  NOTE: I think this could go back inside the spider as an instance method too.
  """
    # CYA
    first_result_str = str(first_result_num) if first_result_num is not None else '0'

    params = {
        'limit': str(MAX_RESULT_LIMIT),
        'from': first_result_str,  # if not specified, Athlinks assumes '0'
        # 'eventCourseId': event_course_id, # not needed, but I seen it elsewhere
    }

    return FormRequest(
        url=f'https://results.athlinks.com/event/{race_spider.event_id}',
        method='GET',
        formdata=params,
        callback=race_spider.parse
    )


def create_athlete_request(race_spider, bib_num):
    return FormRequest(
        url=f'https://results.athlinks.com/individual',
        method='GET',
        formdata={
            'bib': str(bib_num),
            'eventId': str(race_spider.event_id),
            'eventCourseId': str(race_spider.event_course_id),
        },
        callback=race_spider.parse_athlete
    )
