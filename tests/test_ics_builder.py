import json
import pytest
from unittest.mock import patch, MagicMock

from app.ics_builder import build_tidal_ics, build_alerts_only_ics


# Build a realistic full-year 2026 mock: alternating H/L for each day
def _make_year_mock():
    predictions = []
    for month in range(1, 13):
        # Approximate days per month
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
        for day in range(1, days_in_month + 1):
            predictions.extend([
                {"t": f"2026-{month:02d}-{day:02d} 03:15", "v": "5.2", "type": "H"},
                {"t": f"2026-{month:02d}-{day:02d} 09:30", "v": "0.8", "type": "L"},
                {"t": f"2026-{month:02d}-{day:02d} 15:45", "v": "4.9", "type": "H"},
                {"t": f"2026-{month:02d}-{day:02d} 21:00", "v": "1.1", "type": "L"},
            ])
    return {"predictions": predictions}


MOCK_STATIONS_RESPONSE = {
    "stations": [
        {"id": "9414290", "name": "San Francisco", "lat": "37.8063", "lng": "-122.4659",
         "state": "CA", "tidal": True, "greatlakes": False},
    ]
}


def _make_mock_response(data: dict):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _httpx_side_effect(url, **kwargs):
    if "mdapi" in url:
        return _make_mock_response(MOCK_STATIONS_RESPONSE)
    return _make_mock_response(_make_year_mock())


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def test_ics_parses():
    from icalendar import Calendar
    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics, counts = build_tidal_ics("9414290", 2026)
    cal = Calendar.from_ical(ics)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) > 600


def test_ics_returns_counts():
    with patch("httpx.get", side_effect=_httpx_side_effect):
        _, counts = build_tidal_ics("9414290", 2026)
    assert "hilo_high" in counts
    assert "hilo_low" in counts
    assert counts["hilo_high"] > 0
    assert counts["hilo_low"] > 0


def test_ics_uids_stable():
    from icalendar import Calendar

    def uids(ics):
        return {c["UID"] for c in Calendar.from_ical(ics).walk() if c.name == "VEVENT"}

    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics1, _ = build_tidal_ics("9414290", 2026)
        ics2, _ = build_tidal_ics("9414290", 2026)
    assert uids(ics1) == uids(ics2)


def test_ics_uids_unique():
    from icalendar import Calendar
    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics, _ = build_tidal_ics("9414290", 2026)
    uids = [c["UID"] for c in Calendar.from_ical(ics).walk() if c.name == "VEVENT"]
    assert len(uids) == len(set(uids))


def test_ics_crlf():
    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics, _ = build_tidal_ics("9414290", 2026)
    assert b"\r\n" in ics
    assert b"\n\n" not in ics


def test_alerts_only_ics_parses():
    from icalendar import Calendar
    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics, counts = build_alerts_only_ics("9414290", 2026)
    cal = Calendar.from_ical(ics)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert isinstance(events, list)
    # counts should be a dict (may be empty if mock data has no extremes)
    assert isinstance(counts, dict)


def test_ics_timed_events_use_station_timezone():
    # Regression: DTSTART was emitted as a floating time (no TZID) alongside an
    # unused UTC VTIMEZONE, so Google Calendar read NOAA's local (lst_ldt) tide
    # times as UTC and shifted every event by the station's UTC offset.
    from datetime import timezone
    from icalendar import Calendar
    with patch("httpx.get", side_effect=_httpx_side_effect):
        ics, _ = build_tidal_ics("9414290", 2026)
    assert b"DTSTART;TZID=America/Los_Angeles:" in ics
    cal = Calendar.from_ical(ics)
    assert {tz["TZID"] for tz in cal.walk("VTIMEZONE")} == {"America/Los_Angeles"}
    starts = {
        c["UID"]: c.decoded("DTSTART")
        for c in cal.walk("VEVENT") if c["UID"].endswith("-H@tideline")
    }
    # 03:15 local: PST (UTC-8) in January, PDT (UTC-7) in July
    jan = starts["tide-9414290-2026-01-15-0315-H@tideline"]
    jul = starts["tide-9414290-2026-07-15-0315-H@tideline"]
    assert jan.astimezone(timezone.utc).hour == 11
    assert jul.astimezone(timezone.utc).hour == 10
