import logging

import psycopg2.extras

log = logging.getLogger("etl.load")

# ON CONFLICT is what makes this safe to run over and over. if a row for the
# same state/year/month/indicator already exists it just updates the numbers
# instead of inserting a duplicate. this is basically the whole reason we can
# stick this on a schedule later without worrying about the table filling up
# with dupes every month
UPSERT_SQL = """
INSERT INTO overdose_deaths (
    state_abbr, state_name, year, month, period_end_date,
    indicator, data_value, predicted_value, percent_complete
) VALUES (
    %(state_abbr)s, %(state_name)s, %(year)s, %(month)s, %(period_end_date)s,
    %(indicator)s, %(data_value)s, %(predicted_value)s, %(percent_complete)s
)
ON CONFLICT (state_abbr, year, month, indicator)
DO UPDATE SET
    data_value = EXCLUDED.data_value,
    predicted_value = EXCLUDED.predicted_value,
    percent_complete = EXCLUDED.percent_complete,
    loaded_at = now();
"""


def load_records(conn, records):
    # execute_batch sends these in batches instead of one cur.execute() per row,
    # which matters a lot once were dealing with tens of thousands of records
    # from the full cdc history, doing it one at a time would take forever
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, UPSERT_SQL, records, page_size=1000)
    conn.commit()
    log.info("Loaded/updated %d rows", len(records))
