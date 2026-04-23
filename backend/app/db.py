import logging
import os

import psycopg2
from psycopg2 import pool

log = logging.getLogger("app.db")

# using a connection pool here instead of the etl's plain get_connection(),
# since this is a live web server that could get hit by multiple requests
# around the same time, not a one-shot script that opens one connection and
# closes it when its done. 1-5 connections is way more than plenty for local
# dev / a small demo, can bump it up later if this ever needs to handle real
# traffic
#
# same DATABASE_URL-or-discrete-vars fallback as etl/db.py, so this can point
# at either the local docker container or a hosted postgres (like neon)
# depending on what's set in the environment
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    _pool = pool.SimpleConnectionPool(1, 5, _database_url)
else:
    _pool = pool.SimpleConnectionPool(
        1,
        5,
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5433"),
        dbname=os.environ.get("DB_NAME", "epidemic"),
        user=os.environ.get("DB_USER", "epidemic"),
        password=os.environ.get("DB_PASSWORD", "epidemic"),
    )

# the raw CDC data has a bunch of indicators (Cocaine, Heroin, etc) mixed in with
# the overall total. the map only ever wants the total, so this is the one we
# filter down to for the /api/deaths endpoint
TOTAL_INDICATOR = "Number of Drug Overdose Deaths"

SELECT_SERIES_SQL = """
SELECT state_abbr, state_name, period_end_date, data_value
FROM overdose_deaths
WHERE indicator = %s
  -- cdc mixes a couple non-state rows in with the real states:
  --   US = the national total (way bigger than any single state, badly
  --        skewed the color ramp when it was included)
  --   YC = "New York City" specifically, broken out separately from New
  --        York state - not a feature in us-states.json so it'd never
  --        render, just dead weight in the response
  -- Puerto Rico (PR) stays in though, it's a real feature on the map
  AND state_abbr NOT IN ('US', 'YC')
ORDER BY period_end_date, state_name;
"""


def _run_query(conn):
    with conn.cursor() as cur:
        cur.execute(SELECT_SERIES_SQL, (TOTAL_INDICATOR,))
        return cur.fetchall()


def fetch_death_series():
    """grabs the full rolling-12-month-ending time series for every state,
    one row per state per month. this is small enough (a few thousand rows)
    to just hand the whole thing back in one response and let the frontend
    scrub through it locally instead of us needing a separate endpoint per
    month"""
    conn = _pool.getconn()
    try:
        try:
            rows = _run_query(conn)
        except psycopg2.OperationalError:
            # neon (our hosted postgres) suspends its compute after a few
            # minutes of no traffic and kills existing connections when it
            # does. the pool has no way of knowing that happened until we
            # actually try to use one of those connections and it fails.
            # when that happens, throw the dead connection away - putting
            # it back would just hand the same broken one to the next
            # request - and retry once on a fresh connection
            log.warning("Connection from pool was dead, retrying with a new one")
            _pool.putconn(conn, close=True)
            conn = _pool.getconn()
            rows = _run_query(conn)
    finally:
        # always give the connection back to the pool, even if the query
        # blew up above - otherwise we'd leak connections out of the pool
        # every time something goes wrong and eventually run out
        _pool.putconn(conn)

    return [
        {
            "state_abbr": row[0],
            "state_name": row[1],
            "period_end_date": row[2].isoformat(),
            "data_value": row[3],
        }
        for row in rows
    ]
