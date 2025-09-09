from typing import Callable, Any, Literal
from logging import getLogger, INFO, basicConfig
from datetime import date, timedelta, datetime
from os import environ
from time import sleep
from json import load, dump, JSONDecodeError
from dataclasses import dataclass
from dataclasses import asdict as dataclass_asdict

from dotenv import load_dotenv
from requests import get as requests_get
from bs4 import BeautifulSoup
from ics import Calendar, Event
from ics.grammar.parse import ContentLine


@dataclass
class CalendarEventJSON:

    name: str
    begin: str  # ISO 8601 format datetime
    end: str  # ISO 8601 format datetime
    status: Literal['CONFIRMED', 'CANCELLED']
    location: str
    description: str

    x_apple_travel_time: str | None = None


class CalendarGenerator:

    def set_env_var(self, name: str, default_value: Any = None, value_converter: Callable[[str], Any] = str) -> None:

        value = environ.get(name, default_value)

        if value is None:
            self.logger.error(f'{name} is not set')
            raise ValueError(f'{name} is not set')

        setattr(self, name, value_converter(value))

    def __init__(self) -> None:

        basicConfig(level=INFO)

        self.logger = getLogger(__name__)

        self.CALENDAR_JSON_FILE_NAME = 'local_data/calendar.json'

        load_dotenv()

        self.set_env_var('SCHEDULE_BASE_URL')
        self.set_env_var('ENGLISH_TEACHER_FULL_NAME')
        # if True, the first english lesson on each week will be cancelled
        self.set_env_var('IS_CANCEL_FIRST_ENGLISH_LESSON', False, bool)
        self.set_env_var('TIMEZONE_UTC_HOURS_SHIFT', 0, int)
        self.set_env_var('WEEKS_TO_FETCH', 2, int)
        self.set_env_var('FETCH_EVERY_HOURS', 6, int)

        self.set_env_var('FIRST_LESSON_X_TRAVEL_TIME', 'PT15M')

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Removes all \n, \r, large whitespaces (20 and 2 characters) from the given text.
        """
        return text.replace('\n', '').replace('\r', '').replace(' ' * 20, '').replace('  ', '')

    def load_calendar_json(self) -> dict[str, list[CalendarEventJSON]]:

        with open(self.CALENDAR_JSON_FILE_NAME, 'a+', encoding='UTF-8'):
            pass

        with open(self.CALENDAR_JSON_FILE_NAME, 'r', encoding='UTF-8') as f:

            try:
                return {
                    date_iso: [CalendarEventJSON(**event) for event in events]
                    for date_iso, events in load(f).items()
                }

            except JSONDecodeError:
                return {}

    def save_calendar_json(self, data: dict[str, list[CalendarEventJSON]]) -> None:

        data = {
            date_iso: [dataclass_asdict(event) for event in events]
            for date_iso, events in data.items()
        }

        with open(self.CALENDAR_JSON_FILE_NAME, 'w', encoding='UTF-8') as f:
            dump(data, f, ensure_ascii=False)

    def get_calendar(self) -> Calendar:

        calendar_json: dict[str, list[CalendarEventJSON]] = self.load_calendar_json()

        current_date = date.today() - timedelta(days=date.today().weekday())

        for _ in range(self.WEEKS_TO_FETCH):

            response = requests_get(
                f"{self.SCHEDULE_BASE_URL}/{current_date.strftime('%Y-%m-%d')}",
                headers={'Accept-Language': 'ru-RU,ru;q=0.9'},
            )

            if response.status_code != 200:
                self.logger.error(f'Failed to fetch schedule for {current_date.isoformat()}: {response.status_code}')
                break

            soup = BeautifulSoup(response.content, 'html.parser')

            day_tags = soup.select('#accordion > div.panel.panel-default')

            if not day_tags:

                current_date += timedelta(weeks=1)
                continue

            is_first_english_lesson_cancelled = False

            for day_tag in day_tags:

                for i, lesson_tag in enumerate(day_tag.select('ul > li')):

                    lesson_tag_divs = lesson_tag.find_all('div', recursive=False)

                    subject = self.normalize_text(lesson_tag_divs[1].select_one('div > div > span').text)
                    teacher = self.normalize_text(lesson_tag_divs[3].select_one('div > div > span').text)

                    if 'Английский язык' in subject and self.ENGLISH_TEACHER_FULL_NAME not in teacher:
                        continue

                    time_tag = lesson_tag_divs[0].select_one('div > div > span')
                    time_begin, time_end = self.normalize_text(time_tag.text).split('–')

                    time_begin_hours, time_begin_minutes = map(int, time_begin.split(':'))
                    time_end_hours, time_end_minutes = map(int, time_end.split(':'))

                    is_cancelled = 'cancelled' in time_tag.get('class')

                    if all((
                            'Английский язык' in subject,
                            self.IS_CANCEL_FIRST_ENGLISH_LESSON,
                            not is_first_english_lesson_cancelled,
                    )):

                        is_cancelled = True
                        is_first_english_lesson_cancelled = True

                    begin_datetime = datetime(
                        year=current_date.year,
                        month=current_date.month,
                        day=current_date.day,
                        hour=time_begin_hours - self.TIMEZONE_UTC_HOURS_SHIFT,
                        minute=time_begin_minutes,
                    )
                    end_datetime = datetime(
                        year=current_date.year,
                        month=current_date.month,
                        day=current_date.day,
                        hour=time_end_hours - self.TIMEZONE_UTC_HOURS_SHIFT,
                        minute=time_end_minutes,
                    )

                    begin_date_iso = begin_datetime.date().isoformat()

                    if i == 0:
                        calendar_json[begin_date_iso] = []

                    calendar_json[begin_date_iso].append(CalendarEventJSON(
                        name=subject,
                        begin=begin_datetime.isoformat(),
                        end=end_datetime.isoformat(),
                        status='CANCELLED' if is_cancelled else 'CONFIRMED',
                        location=self.normalize_text(lesson_tag_divs[2].select_one('div > div > span').text),
                        description=f"Преподаватель: {teacher}",
                        **({'x_apple_travel_time': self.FIRST_LESSON_X_TRAVEL_TIME} if i == 0 else {}),
                    ))

                current_date += timedelta(days=1)

            current_date += timedelta(days=(7 - current_date.weekday()))

        self.save_calendar_json(calendar_json)

        calendar = Calendar()

        for calendar_json_events in calendar_json.values():
            for calendar_json_event in calendar_json_events:

                event = Event(
                    name=calendar_json_event.name,
                    begin=calendar_json_event.begin,
                    end=calendar_json_event.end,
                    status=calendar_json_event.status,
                    location=calendar_json_event.location,
                    description=calendar_json_event.description,
                )

                if calendar_json_event.x_apple_travel_time:
                    event.extra.append(ContentLine(
                        name='X-APPLE-TRAVEL-DURATION;VALUE=DURATION', value=calendar_json_event.x_apple_travel_time
                    ))

                calendar.events.add(event)

        return calendar

    def save_to_ics(self, file_name: str, calendar: Calendar) -> None:
        with open(file_name, 'w', encoding='UTF-8') as f:
            f.writelines(calendar.serialize_iter())

    def run_auto_update(self) -> None:
        while True:

            self.logger.info('Fetching new schedule and updating .ics file')

            self.save_to_ics('timetables/timetable.ics', self.get_calendar())

            self.logger.info('Updated .ics file successfully, sleeping...')

            sleep(self.FETCH_EVERY_HOURS * 60 * 60)


if __name__ == "__main__":
    CalendarGenerator().run_auto_update()
