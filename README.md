# Portfolio NC Plus One

Back-end project, events platform REST API. Allowing registration, browsing, and
RSVP-ing to/of events.

## Database Setup

To setup up the `nc_plus_one` database, ensure [PostgreSQL](https://www.postgresql.org/download/)
is downloaded and installed, then run:

```bash
psql -f db/setup.sql
```

This script will drop any existing instance of the `nc_plus_one` database
and replace it with a new one.
