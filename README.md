# Portfolio NC Plus One

Back-end project, events platform REST API. Allowing registration, browsing, and
RSVP-ing to/of events.

## Architecture

The application uses a root-level `nc_plus_one` Python package, organized by
feature. Run the commands below from the project root; installing the requirements
is enough to import the package, with no editable installation step.

```text
nc_plus_one/
├── main.py                 # FastAPI app, router registration, error responses
├── errors.py               # Framework-independent business exceptions
├── auth/
│   ├── router.py           # Login and registration HTTP endpoints
│   ├── schemas.py          # Pydantic request validation
│   ├── service.py          # Login and registration rules
│   ├── repository.py       # User SQL queries
│   ├── security.py         # Password hashing and JWT encoding/validation
│   └── dependencies.py     # FastAPI bearer-token authentication
├── events/
│   ├── router.py           # Event browsing HTTP endpoints
│   ├── service.py          # Event lookup rules
│   └── repository.py       # Event SQL queries
├── rsvps/
│   ├── router.py           # RSVP endpoints beneath /api/events/{id}
│   ├── service.py          # RSVP existence and duplicate checks
│   └── repository.py       # RSVP SQL queries
└── db/
    ├── connection.py       # Shared connections and query transactions
    ├── seed.py             # Schema and fixture loader
    ├── schema.sql          # Table definitions
    └── data/               # JSON seed fixtures
scripts/
└── setup.sql               # Local database creation/reset
tests/
├── conftest.py             # Shared client and temporary-schema fixtures
├── auth/                   # Authentication route and service tests
├── events/                 # Event route and service tests
├── rsvps/                  # RSVP route and service tests
└── db/                     # Connection and seed tests
```

Each feature follows the same request flow:

```text
HTTP request → router → service → repository → db.connection → PostgreSQL
```

Routers validate input using request schemas, resolve authentication dependencies,
and choose success status codes. Services enforce business rules and coordinate
repository calls. Repositories contain SQL and use the shared query helper, which
commits or rolls back each query and closes its connection. The seed loader uses
its own transaction to apply schema changes and fixture inserts together.

Protected RSVP routes use `auth.dependencies.require_token` to validate bearer
tokens through `auth.security`. The decoded user ID is passed to the RSVP service.
Services raise business exceptions from `errors.py`; `main.py` converts these to
the API's existing status codes and `{"error": {"code": ..., "message": ...}}`
responses. Authentication dependency errors retain their existing HTTP handling.

Feature folders keep related changes together as the API grows. Separating routes,
services, and repositories makes rules testable without HTTP or PostgreSQL and
keeps SQL out of request handlers. Shared database infrastructure avoids duplicate
connection code. RSVPs have their own feature because their rules and storage are
distinct, while keeping their existing event-based URLs. The RSVP service reuses
the events repository to check event existence. Plain functions keep these
boundaries explicit without introducing service classes or a dependency container.

When extending the API:

- Add endpoints to the relevant feature's `router.py` and request models to
  `schemas.py` when needed. Register new feature routers in `main.py`.
- Put business rules in `service.py`, SQL in `repository.py`, and reusable
  business failures in `errors.py`, with their HTTP mapping in `main.py`.
- Add route integration tests and isolated service tests in the matching feature
  test folder. Put shared database tests in `tests/db`.

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
psql -f scripts/setup.sql
```

This script will drop any existing instance of the `nc_plus_one` database
and replace it with a new one.

## `.env` Environment

Copy `.env.example` to `.env` at the project root and set your connection and
development signing key:

```bash
cp .env.example .env
```

| Variable | Used by | Behavior |
| --- | --- | --- |
| `DSN` | API database queries | A PostgreSQL DSN; when absent, psycopg2 uses PostgreSQL environment settings and defaults. |
| `JWT_SECRET` | Login and protected routes | Signing key required to issue and validate JWTs. |
| `DATABASE_URL` | Seed command only | Defaults to `dbname=nc_plus_one`; export it in the shell to override. |
| `TEST_DATABASE_URL` | Database and route integration tests | Database where the test role can create temporary schemas. |

The API loads `.env` without overriding existing environment variables. The seed
command reads `DATABASE_URL` from the process environment and does not load `.env`.

## Seed the Database

After creating the database, run from the project root:

```bash
python -m nc_plus_one.db.seed
```

The seed recreates the `users`, `venues`, `events`, and `rsvps` tables using
`nc_plus_one/db/schema.sql`, then loads the JSON files in `nc_plus_one/db/data`.
It replaces existing data each time and resets IDs to match the fixtures' foreign
keys. If an insert fails, the schema changes and inserts are rolled back together.

The default connection uses the local `nc_plus_one` database and your PostgreSQL
environment settings. To choose a different connection:

```bash
DATABASE_URL='postgresql://localhost/nc_plus_one' python -m nc_plus_one.db.seed
```

The function can also use an existing psycopg2 connection and an optional directory
containing `users.json`, `venues.json`, `events.json`, and `rsvps.json`:

```python
from contextlib import closing

import psycopg2
from nc_plus_one.db.seed import seed

with closing(psycopg2.connect("dbname=nc_plus_one")) as connection:
    seed(connection)
```

The user fixtures contain bcrypt hashes in `hashed_password`. All seeded users
have the development password `password123`.

## Run the API

After configuring `.env` and seeding the database, run from the project root:

```bash
python -m uvicorn nc_plus_one.main:app --reload
```

The API is available at `http://127.0.0.1:8000/api/events`, with interactive
documentation at `http://127.0.0.1:8000/docs`.

## Tests

Run the tests that do not require a database with:

```bash
python -m pytest -v
```

Run the full suite against a PostgreSQL database where your role can create
schemas. Each database-dependent test uses a temporary schema, which is removed
afterwards:

```bash
TEST_DATABASE_URL='dbname=nc_plus_one' python -m pytest -v
```

Database-dependent tests are skipped when `TEST_DATABASE_URL` is unset; isolated
service tests and connection mocks still run.

GitHub Actions runs the tests on pushes to `main` and when a pull request is opened.
The workflow uses Python 3.13 and a PostgreSQL 18
service with its own test database and sets `TEST_DATABASE_URL` automatically.
