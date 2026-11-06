"""How the API writes dates, hours and counts in its messages (`api.errors`; CLAUDE.md "Writing for the public")."""

from datetime import UTC, date, datetime, timedelta, timezone

from api.errors import counted, day_text, hour_text


def test_days_hours_and_counts_read_as_public_text_does():
    assert day_text(date(2025, 7, 8)) == "July 8, 2025"
    assert hour_text(datetime(2025, 7, 8, 15, tzinfo=UTC)) == "3 p.m. UTC, July 8, 2025"
    assert hour_text(datetime(2025, 7, 8, 9, 30, tzinfo=UTC)) == "9:30 a.m. UTC, July 8, 2025"
    assert hour_text(datetime(2025, 7, 8, 0, tzinfo=UTC)) == "midnight UTC, July 8, 2025"
    assert hour_text(datetime(2025, 7, 8, 12, tzinfo=UTC)) == "noon UTC, July 8, 2025"
    cdt = timezone(timedelta(hours=-5))
    assert hour_text(datetime(2025, 7, 8, 19, tzinfo=cdt)) == "midnight UTC, July 9, 2025"  # said in UTC
    assert (counted(1, "day"), counted(3, "day"), counted(1200, "grid cell")) == ("1 day", "3 days", "1,200 grid cells")
