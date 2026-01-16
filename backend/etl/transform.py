import calendar
import logging
from datetime import date

log = logging.getLogger("etl.transform")

# quick lookup like {"January": 1, "February": 2, ...} built off the stdlib calendar
# module instead of typing all 12 out by hand. calendar.month_name[0] is just an
# empty string so we filter that out
MONTH_NUMBERS = {name: i for i, name in enumerate(calendar.month_name) if name}


def _period_end_date(year: int, month_name: str) -> date:
    # cdc gives us year and month name as separate fields (like 2015 + "January")
    # but we want an actual date column so its sortable and queryable properly.
    # using the last day of that month since "period" is a 12-month window that
    # closes at months end
    month_num = MONTH_NUMBERS[month_name]
    last_day = calendar.monthrange(year, month_num)[1]
    return date(year, month_num, last_day)


def _to_number(value):
    # everything coming back from cdc's api is a string, even the numeric fields.
    # and some rows just dont have a value at all when the data's suppressed for
    # quality reasons (saw this happen with a few low-count cocaine rows while
    # testing). so this just tries to turn "4603" into 4603.0 and anything missing
    # or weird becomes None instead of blowing up the whole run
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def transform_record(raw: dict):
    """cleans up one raw cdc row into the shape our table expects.
    returns None if the row's missing something we actually need so the
    caller can skip it instead of the whole run dying over one bad row"""
    try:
        year = int(raw["year"])
        month = raw["month"]
        state_abbr = raw["state"]
        state_name = raw["state_name"]
        indicator = raw["indicator"]
    except (KeyError, ValueError):
        # missing a required field, or year wasnt actually a number. rare,
        # but better to skip and keep going than crash the whole etl run
        return None

    return {
        "state_abbr": state_abbr,
        "state_name": state_name,
        "year": year,
        "month": month,
        "period_end_date": _period_end_date(year, month),
        "indicator": indicator,
        "data_value": _to_number(raw.get("data_value")),
        "predicted_value": _to_number(raw.get("predicted_value")),
        "percent_complete": _to_number(raw.get("percent_complete")),
    }


def transform_records(raw_records):
    cleaned = []
    skipped = 0

    for raw in raw_records:
        row = transform_record(raw)
        if row is None:
            skipped += 1
            continue
        cleaned.append(row)

    if skipped:
        # not a big deal if this is small, just means a handful of rows didnt
        # have everything needed. worth knowing about if this number ever
        # jumps up a lot though, could mean cdc changed their field names on us
        log.warning("Skipped %d rows with missing required fields", skipped)

    return cleaned
