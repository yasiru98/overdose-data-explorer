import logging

import requests

# cdc's public socrata dataset for the VSRR provisional overdose death counts.
# found this by digging around data.cdc.gov, dataset id is xkb8-kh2a. its the
# monthly rolling 12-month-ending series, not a clean one-number-per-year thing,
# which is why the transform step has to do some work later
CDC_API_URL = "https://data.cdc.gov/resource/xkb8-kh2a.json"

# socrata caps how much it hands back in one response so we have to page through
# it. 5000 felt like a reasonable middle ground, not so small were making a ton of
# requests, not so big a single request gets slow/flaky
PAGE_SIZE = 5000

log = logging.getLogger("etl.extract")


def fetch_all_records():
    """grabs every '12 month-ending' row from the cdc dataset, paging through
    since the api wont just hand over the full history in one shot"""
    records = []
    offset = 0

    while True:
        params = {
            "$limit": PAGE_SIZE,
            "$offset": offset,
            # only pulling the rolling 12-month-ending numbers, not the raw single
            # month counts (those are way noisier and not what were showing anyway)
            "$where": "period='12 month-ending'",
            # ordering by :id so paging is stable. without an explicit order socrata
            # can hand back rows in a different order between requests which means
            # offset-based paging could skip or repeat rows
            "$order": ":id",
        }
        response = requests.get(CDC_API_URL, params=params, timeout=30)
        response.raise_for_status()
        page = response.json()

        # empty page = we've reached the end, nothing left to grab
        if not page:
            break

        records.extend(page)
        log.info("Fetched %d records (offset %d)", len(page), offset)
        offset += PAGE_SIZE

    return records
