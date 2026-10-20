# Portfolio NC Plus One

Back-end project, events platform REST API. Allowing registration, browsing, and
RSVP-ing to/of events.

## Python Setup

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Database Setup

To setup up the `nc_plus_one` database, ensure [PostgreSQL](https://www.postgresql.org/download/)
is downloaded and installed, then run:

```bash
psql -f db/setup.sql
```

This script will drop any existing instance of the `nc_plus_one` database
and replace it with a new one.

## `.env` Environment

The `connection.py` script is reliant on a connection defined by a
DSN string environment variable `DSN="..."`.

An example `.env` file can be found in `.env.example` at the project
route.

## Seed the Database

After creating the database, run from the project root:

```bash
python -m db.seed
```

The seed recreates the `users`, `venues`, `events`, and `rsvps` tables using
`db/schema.sql`, then loads the JSON files in `db/data`. It replaces existing
data each time and resets IDs to match the fixtures' foreign keys. If an insert
fails, the schema changes and inserts are rolled back together.

The default connection uses the local `nc_plus_one` database and your PostgreSQL
environment settings. To choose a different connection:

```bash
DATABASE_URL='postgresql://localhost/nc_plus_one' python -m db.seed
```

The function can also use an existing psycopg2 connection and an optional directory
containing `users.json`, `venues.json`, `events.json`, and `rsvps.json`:

```python
from contextlib import closing

import psycopg2
from db.seed import seed

with closing(psycopg2.connect("dbname=nc_plus_one")) as connection:
    seed(connection)
```

The fixture passwords are copied as supplied for development.

## Tests

Run the integration tests against a PostgreSQL database where your role can create
schemas. Each test uses a temporary schema, which is removed afterwards:

```bash
TEST_DATABASE_URL='dbname=nc_plus_one' python -m pytest -v
```

Tests are skipped when `TEST_DATABASE_URL` is unset.
