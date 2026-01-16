import os

import psycopg2

# reading connection info from env vars instead of hardcoding creds in the repo.
# if DATABASE_URL is set (a full connection string, like what neon/other hosted
# postgres providers give you) just use that directly - this is what the
# scheduled github actions run and any hosted deployment will use.
# otherwise fall back to the discrete host/port/etc vars, defaulting to
# whats in docker-compose.yml so local dev still works with zero setup
def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5433"),
        dbname=os.environ.get("DB_NAME", "epidemic"),
        user=os.environ.get("DB_USER", "epidemic"),
        password=os.environ.get("DB_PASSWORD", "epidemic"),
    )
