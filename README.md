### SPBU's Timetable to ICS Calendar Converter
This project automatically fetches a timetable from Saint Petersburg State Unviersity's (SPBU) website
and converts it into an ICS calendar format.
It also shares the calendar via a public URL, so you can easily subscribe to it
in your favorite calendar application.

### How to run it manually
1. Clone the repository: `git clone https://github.com/LaGGgggg/spbu_timetable_ics_calendar.git`
2. Navigate to the project directory: `cd spbu_timetable_ics_calendar`
3. Create an `.env` file in the project root with the following content and fill in your details:
   ```dotenv
    # Required variables:
    # Your group's schedule URL from the SPBU's timetable website.
    SCHEDULE_BASE_URL=https://timetable.spbu.ru/AMCP/StudentGroupEvents/Primary/428500
    # Your english teacher's full name (as it appears on the timetable website).
    # This is required to filter out english lessons which you don't actually have.
    ENGLISH_TEACHER_FULL_NAME="Семенова Ю. О."
    # Not required, but strongly recommended to set your timezone offset from UTC in hours. 3 for Saint Petersburg.
    TIMEZONE_UTC_HOURS_SHIFT=3

    # Not required variables with default values:

    # If True, the first english lesson in a week will be marked as cancelled.
    IS_CANCEL_FIRST_ENGLISH_LESSON=True
    # Number of weeks to fetch from the timetable website.
    WEEKS_TO_FETCH=2
    # How often (in hours) to fetch and update the calendar.
    FETCH_EVERY_HOURS=6
    # Travel time in minutes to add before the first lesson of the day. This feature is for Apple Calendar users.
    # Format of the value: "PT15M" for 15 minutes.
    FIRST_LESSON_X_TRAVEL_TIME=PT15M

    # Required docker compose variables:
    # Your email for generating a free SSL certificate with Let's Encrypt.
    SSL_EMAIL=<your_email>
    # Your server's domain name where the calendar will be hosted.
    ICS_HOST=<your_server_domain_name>
    # Your auth token for Timeweb Cloud API to automatically issue and renew SSL certificates with any ports opened.
    # You can use any other methods or providers to get SSL certificates.
    # For it you should change docker-compose.yml and nginx config accordingly.
    TIMEWEBCLOUD_AUTH_TOKEN="<your_timewebcloud_auth_token>"
   ```
4. Build and run docker compose, after check the logs: `docker compose up -d --build && docker compose logs -f`
5. Access the calendar at `https://<your_server_domain_name>/calendar.ics`
