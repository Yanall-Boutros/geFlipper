# geFlipper backend

An async FastAPI service backed by PostgreSQL through SQLAlchemy 2.x and
`asyncpg`. Alembic manages the database schema.

For deployment and the overall project, see the [root README](../README.md).

## Layout

```
backend/
└── app/                      # the `app` package; run commands from backend/
    ├── main.py               # FastAPI app; mounts /api/v1, starts background tasks
    ├── alembic.ini           # Alembic config (connection URL comes from core/config.py)
    ├── api/
    │   ├── deps.py           # get_db(): per-request AsyncSession dependency
    │   └── v1/
    │       ├── router.py     # v1 router: GET /health, includes endpoints/
    │       └── endpoints/    # one router per resource (priceData.py: GET /price-data)
    ├── core/
    │   ├── config.py         # settings loaded from environment variables
    │   ├── lifecycle.py      # LifecycleTask: base for app-lifetime background tasks
    │   └── security.py       # placeholder
    ├── db/
    │   ├── base.py           # declarative Base shared by every model
    │   ├── database.py       # async engine + SessionLocal
    │   ├── utils/handler.py  # BaseHandler: async create/read/update/delete
    │   └── migrations/       # Alembic env.py, template and versions/
    ├── models/               # SQLAlchemy models (registered in models/__init__.py)
    ├── schemas/              # Pydantic v2 schemas
    └── services/             # collectors/ (BaseCollector) and API clients (rswiki/)
```

All imports use the `app.` prefix (for example `from app.db.base import Base`),
so run the server and scripts from `backend/`.

## Running locally

From the repo root:

```sh
nix-shell                          # Python + fastapi, uvicorn, sqlalchemy, asyncpg, alembic
export DB_PASS=<password>          # plus DB_HOST/DB_USER/... if not using the defaults
cd backend
uvicorn app.main:app --reload
```

The root README's [Quick start](../README.md#quick-start-local-development)
shows how to start a local Postgres container.

## Database access

Routes get a session from the `get_db` dependency. It opens one
`AsyncSession` per request and closes it afterwards:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.utils.handler import BaseHandler
from app.models import PriceDataModel

@api_router.get("/items/{item_id}")
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    return await BaseHandler(db).read(PriceDataModel, item_id)
```

`BaseHandler` also has `list(model, offset, limit, order_by)` and
`count(model)` for paginated endpoints. Wrap the result in
`app.schemas.pagination.Page`:

```sh
curl 'localhost:8000/api/v1/price-data?offset=0&limit=100'
# {"items": [...], "total": 4662, "offset": 0, "limit": 100}
```

`limit` defaults to 100 and is capped at 1000. Rows are ordered by item id,
then `jagex_timestamp`.

Every `BaseHandler` method is async and must be awaited. Validate incoming
data with a Pydantic schema before handing it to the handler. The schemas set
`from_attributes=True`, so they can also be built directly from model
instances.

## Migrations

Alembic lives in `app/db/migrations/`. `env.py` gets the connection URL from
`app.core.config.settings` and the table definitions from `Base.metadata`, so
the `DB_*` variables must be set for any command that touches the database.

Run Alembic from `backend/app/`, or from anywhere with `-c`:

```sh
cd backend/app
alembic upgrade head          # apply all pending migrations
alembic downgrade -1          # roll back the most recent migration
alembic current               # show which revision the database is at
alembic history               # list all revisions
alembic check                 # fail if the models and the database have drifted
alembic upgrade head --sql    # print the SQL without connecting (review before applying)
```

### Changing the schema

1. Add or edit a model in `app/models/`.
2. **New model:** import it in `app/models/__init__.py`. Autogenerate only sees
   models that are imported there.
3. Generate a migration:
   ```sh
   alembic revision --autogenerate -m "add price history table"
   ```
4. Read the new file in `app/db/migrations/versions/`. Autogenerate misses some
   changes, such as renames (which it treats as a drop plus an add) and some
   type or constraint changes. Fix those by hand.
5. Apply it with `alembic upgrade head`, and commit the model and the migration
   together.

### Running migrations in production

The backend image doesn't include Alembic, and the container doesn't migrate on
startup. For now, run migrations from a machine with the dev shell, pointed at
the production database (Postgres is published on port 5432 of the host):

```sh
nix-shell
export DB_HOST=<server> DB_PASS=<password>
cd backend/app && alembic upgrade head
```

Migrate before restarting the backend with code that depends on the new
schema. A planned improvement is to add `alembic` to the image and run
`alembic upgrade head` before `uvicorn` starts.

## Background data collection

Data collection runs inside the FastAPI process as long-lived asyncio tasks.
They start when the app starts and are cancelled when it shuts down, using
FastAPI's `lifespan` hook in `main.py`. FastAPI's `BackgroundTasks` isn't
suitable, because it only runs work after a single request finishes, not on a
schedule. Set `ENABLE_COLLECTORS=0` to run the API without them.

- `core/lifecycle.py`: `LifecycleTask`, the base for anything that runs for the
  life of the app. Subclasses implement `run()`, and `start()`/`stop()` manage
  the asyncio task.
- `services/collectors/base.py`: `BaseCollector(LifecycleTask)`. Subclasses set
  `name` and `interval` (seconds) and implement `collect(db)`. Each run gets
  its own `AsyncSession`. A failed run is logged and retried on the next
  interval; it never takes down the app.
- `main.py`: `build_tasks()` lists the tasks to start.

### Collectors

| Collector | Source | Interval | Target |
| --- | --- | --- | --- |
| GE prices (`RSWikiPriceData`) | Weird Gloop `os_dump.json` (`services/rswiki/priceData.py`) | polls every 30 min; writes once per Jagex update (~daily) | `price_data` |
| Latest prices *(planned)* | Wiki `/latest` | ~1 min | *latest prices table (TBD)* |
| 5-minute averages *(planned)* | Wiki `/5m` | 5 min | *5m history table (TBD)* |
| Hourly averages *(planned)* | Wiki `/1h` | 1 h | *1h history table (TBD)* |
| History backfill *(planned)* | Wiki `/timeseries` | on demand | *history table (TBD)* |

`price_data` is append-only, with one row per item per Jagex GE update and
primary key `(id, jagex_timestamp)`. Each row carries the dump's
`%JAGEX_TIMESTAMP%` (when Jagex published the prices) as `jagex_timestamp`, and
`%UPDATE_DETECTED%` (when the wiki noticed the update) as `update_detected`,
both stored as UTC `timestamptz`. The collector skips a dump whose Jagex
timestamp isn't newer than the latest one stored, so rows are never
overwritten. Build time series on `jagex_timestamp`:

```sql
SELECT jagex_timestamp, price, volume
FROM price_data WHERE id = 10344 ORDER BY jagex_timestamp;
```

The wiki endpoints are under `https://prices.runescape.wiki/api/v1/osrs`. The
wiki requires a descriptive `User-Agent` header (`settings.USER_AGENT`) and asks
clients to stay under its rate limits. The legacy `sync_tables.py` in the repo
root shows the payload shapes.

### Adding a collector

```python
class LatestPrices(BaseCollector):
    name = "rswiki_latest"
    interval = 60

    async def collect(self, db: AsyncSession) -> None:
        raw = await asyncio.to_thread(self.fetch)   # requests is blocking
        ...                                         # validate, then upsert
        await db.commit()
```

Then add `LatestPrices()` to `build_tasks()` in `main.py`.

Guidelines for collectors:

- **Don't block the event loop.** Use an async HTTP client such as `httpx.AsyncClient`, or wrap the existing `requests` calls in `asyncio.to_thread`.
- **Make writes idempotent.** Use Postgres upserts (`sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update(...)`) so re-running a collection doesn't create duplicates.
- **Run a single worker.** Each uvicorn worker would start its own copy of the collectors. Before scaling to multiple workers, move collection into its own process or add a lock.
