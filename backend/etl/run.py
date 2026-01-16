import logging
import sys

from etl.db import get_connection
from etl.extract import fetch_all_records
from etl.load import load_records
from etl.transform import transform_records

# run this with: python -m etl.run   (from the backend/ folder)
# needs to be run as -m so python treats etl/ as an actual package, otherwise
# the "from etl.db import ..." style imports above dont resolve right

# logging to stdout with timestamps so if this ever ends up running unattended
# (like a scheduled github actions job down the line) we can still tell what
# happened and when just from the log output, no need to babysit it
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("etl.run")


def main():
    # the whole pipeline, three steps run in order. kept as separate calls on
    # purpose instead of one big function so if something breaks we know
    # immediately which stage it died in - talking to cdc, cleaning the data,
    # or writing to postgres. makes debugging way less of a guessing game
    log.info("Extracting records from CDC API...")
    raw_records = fetch_all_records()
    log.info("Fetched %d raw records", len(raw_records))

    log.info("Transforming records...")
    records = transform_records(raw_records)
    log.info("Transformed %d usable records", len(records))

    log.info("Loading records into Postgres...")
    conn = get_connection()
    try:
        load_records(conn, records)
    finally:
        # close the connection even if load_records blows up halfway through,
        # dont want to leak a hanging connection every time something goes wrong
        conn.close()

    log.info("ETL run complete.")


if __name__ == "__main__":
    sys.exit(main())
