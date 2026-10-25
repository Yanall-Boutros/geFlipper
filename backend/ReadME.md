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
    │       └── endpoints/    # one router per resource:
    │                         #   priceData.py: GET /price-data
    │                         #   items.py: GET /items/{id}, /history, /indicators
    ├── core/
    │   ├── config.py         # settings loaded from environment variables
    │   ├── events.py         # price_data_updated: collector -> indicator engine signal
    │   ├── lifecycle.py      # LifecycleTask: base for app-lifetime background tasks
    │   └── security.py       # empty placeholder
    ├── db/
    │   ├── base.py           # declarative Base shared by every model
    │   ├── database.py       # async engine + SessionLocal
    │   ├── utils/handler.py  # BaseHandler: async CRUD plus filtered list/count
    │   └── migrations/       # Alembic env.py, template and versions/
    ├── models/               # PriceDataModel, ItemIndicatorsModel (registered in __init__.py)
    ├── schemas/              # Pydantic v2 schemas: rswiki/priceData.py, indicators.py, pagination.py
    └── services/
        ├── collectors/       # BaseCollector: run collect(db) every `interval` seconds
        ├── rswiki/           # RSWikiPriceData: the GE price collector
        └── indicators/       # IndicatorEngine and one module per indicator
tests/                        # pytest suite (see Testing below)
pytest.ini                    # pytest config: asyncio_mode = auto, coverage report
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

## Testing

The unit tests live in `tests/` and use pytest with pytest-asyncio. They don't
need Postgres or network access: the database is an in-memory SQLite engine
(`aiosqlite`), and the wiki API is mocked. The dev shell includes everything
the tests need.

```sh
nix-shell
cd backend
pytest                                   # whole suite
pytest tests/test_rswiki_price_data.py   # one file
pytest -k collect -v                     # tests matching a name
```

| File | Covers |
| --- | --- |
| `test_api.py` | `GET /health` and `GET /price-data`: pagination, response shape, query validation |
| `test_items.py` | `GET /items/{id}` (latest snapshot, 404) and `GET /items/{id}/history`: ordering, pagination, inclusive `start`/`end` range, 404, query validation |
| `test_indicators_api.py` | `GET /items/{id}/indicators`, plus an end-to-end run of every real indicator through the engine |
| `test_indicator_engine.py` | `IndicatorEngine`: catch-up order, idempotency, skipping unpriced updates, the window/previous-row plumbing, waking on the signal, surviving failures |
| `test_indicators_<name>.py` | One file per indicator module, checked against hand-worked values |
| `test_handler.py` | `BaseHandler` CRUD, `list` ordering/offset/limit/filters, `count` with filters |
| `test_deps.py` | `get_db` yields a session and closes it |
| `test_rswiki_price_data.py` | Dump parsing (required keys, untraded items), fetching (User-Agent, HTTP errors), and `collect()`: skipping unchanged dumps, chunked inserts, `ON CONFLICT DO NOTHING`, signalling the indicator engine |
| `test_collector_base.py` | `BaseCollector`: one session per run, retry after failure, interval sleep |
| `test_lifecycle.py` | `LifecycleTask` start/stop/restart |
| `test_main.py` | `build_tasks()` with and without `ENABLE_COLLECTORS`, the `lifespan` hook, route mounting |
| `test_config.py` | Settings from environment variables, password escaping |
| `test_schemas.py` | Pydantic schemas and `Page` |

`tests/conftest.py` sets `ENABLE_COLLECTORS=0` before the app is imported and
provides these fixtures:

- `engine` / `session_factory`: a fresh in-memory database with every table
  created, and a session factory bound to it (pass it to `IndicatorEngine`).
- `db`: an `AsyncSession` on that database.
- `client`: an `httpx.AsyncClient` for the app, with `get_db` overridden to use
  that database.
- `price_row(id, jagex_timestamp=JAGEX_TIMESTAMP, **overrides)`: a helper that
  builds the column values for one `price_data` row.

`tests/indicator_helpers.py` has `points(prices, volumes=None)`, which builds
daily `Point`s for the indicator unit tests.

SQLite doesn't support some Postgres-only code, and it drops timezones from
`timestamptz` columns, so a timestamp read back from SQLite is naive.
- The collector's `postgresql.insert(...).on_conflict_do_nothing()` is tested
  with a mocked session. The tests compile the statement with the Postgres
  dialect instead of running it.
- The indicator engine picks the SQLite or Postgres `insert` from the
  session's dialect, so its tests run for real on SQLite.

Check migrations and Postgres behaviour against a real database with
`alembic upgrade head`.

### Continuous integration

GitHub Actions runs three workflows on every push and pull request:

| Workflow | File | Fails when |
| --- | --- | --- |
| Black | `.github/workflows/black.yml` | Any Python file isn't formatted with black 26.5.1 (`black --check .` from the repo root) |
| Coverage | `.github/workflows/coverage.yml` | Line coverage of `app/` is below 80% |
| Unit tests | `.github/workflows/tests.yml` | Any test fails |

CI uses Python 3.14 and installs `requirements-dev.txt` with pip instead of the
Nix shell. When you change a dependency in `shell.nix`, update its pin there
too.

GitHub can't block a commit. To stop failing changes from reaching `main`,
mark the workflows as required status checks in the repository's branch
protection settings.

## Database access

Routes get a session from the `get_db` dependency. It opens one
`AsyncSession` per request and closes it afterwards:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.utils.handler import BaseHandler
from app.models import PriceDataModel

@router.get("/{item_id}")
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    latest = await BaseHandler(db).list(
        PriceDataModel,
        limit=1,
        order_by=[PriceDataModel.jagex_timestamp.desc()],
        filters=[PriceDataModel.id == item_id],
    )
    ...
```

`BaseHandler` has `list(model, offset, limit, order_by, filters)` and
`count(model, filters)` for filtered, paginated endpoints; wrap their results
in `app.schemas.pagination.Page`. `read(model, pk)` needs the full primary key,
which for `price_data` and `item_indicators` is `(id, jagex_timestamp)`.
`items.py`'s `item_time_series()` builds the paginated, range-filtered page for
any model keyed that way.

```sh
curl 'localhost:8000/api/v1/price-data?offset=0&limit=100'
# {"items": [...], "total": 4662, "offset": 0, "limit": 100}

curl 'localhost:8000/api/v1/items/4151'
# latest snapshot of one item (404 if unknown)

curl 'localhost:8000/api/v1/items/4151/history?start=2026-10-01T00:00:00Z&limit=50'
# {"items": [{"jagex_timestamp": ..., "update_detected": ..., "price": ..., "last": ..., "volume": ...}, ...], "total": ..., ...}

curl 'localhost:8000/api/v1/items/4151/indicators?limit=50'
# {"items": [{"jagex_timestamp": ..., "samples": ..., "ema_5": ..., "rsi_14": ..., ...}, ...], "total": ..., ...}
```

`limit` defaults to 100 and is capped at 1000. `/price-data` is ordered by item
id, then `jagex_timestamp`. The per-item routes are ordered oldest first, and
`start`/`end` are inclusive (`start` after `end` returns 422).

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

The backend image includes Alembic, and the container's command (in
`flake.nix`) runs `alembic -c /app/app/alembic.ini upgrade head` before it
starts `uvicorn`. Deploying new code therefore applies its migrations. If a
migration fails, `uvicorn` doesn't start; check the container's logs.

To migrate by hand, use a machine with the dev shell, pointed at the production
database (Postgres is published on port 5432 of the host):

```sh
nix-shell
export DB_HOST=<server> DB_PASS=<password>
cd backend/app && alembic upgrade head
```

## Background data collection

Data collection runs inside the FastAPI process as long-lived asyncio tasks.
They start when the app starts and are cancelled when it shuts down, using
FastAPI's `lifespan` hook in `main.py`. FastAPI's `BackgroundTasks` isn't
suitable, because it only runs work after a single request finishes, not on a
schedule. Set `ENABLE_COLLECTORS=0` to run the API without them; that disables
the indicator engine too.

- `core/lifecycle.py`: `LifecycleTask`, the base for anything that runs for the
  life of the app. Subclasses implement `run()`, and `start()`/`stop()` manage
  the asyncio task.
- `services/collectors/base.py`: `BaseCollector(LifecycleTask)`. Subclasses set
  `name` and `interval` (seconds) and implement `collect(db)`. Each run gets
  its own `AsyncSession`. A failed run is logged and retried on the next
  interval; it never takes down the app.
- `main.py`: `build_tasks()` lists the tasks to start: `RSWikiPriceData` and
  `IndicatorEngine`.

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
overwritten. Items missing any of `id`, `name`, `examine`, `members` or `icon`
are skipped with a warning. Untraded items have no `price`, `last` or
`volume`, and those columns are NULL. After a successful insert the collector
sets `core.events.price_data_updated`, which wakes the indicator engine. Build time series on `jagex_timestamp`:

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

## Indicator engine

`services/indicators/engine.py` holds `IndicatorEngine(LifecycleTask)`. It
appends one `item_indicators` row per priced item for every Jagex update in
`price_data`. The rationale for each indicator is in
[`docs/indicators.md`](../docs/indicators.md).

**When it runs**
- On startup, and whenever the collector sets `price_data_updated`.
- Every hour (`fallback_interval`) in case a signal is missed.

**Each run (`process_pending`)**
1. Finds every `jagex_timestamp` in `price_data` newer than the latest one in
   `item_indicators`.
2. Processes those updates oldest first. A first deploy backfills the whole
   history.
3. For each update, loads each item's latest priced points (up to the
   largest indicator `window`, at most 30) with one `ROW_NUMBER()` query, and
   each item's previous indicator row.
4. Calls every indicator in `INDICATORS` and inserts the rows in chunks with
   `ON CONFLICT DO NOTHING`, so re-running an update is harmless.

Untraded items (NULL `price`) get no row for that update and don't count as a
sample. A failed run is logged and retried on the next signal or after the
fallback interval.

**`item_indicators`**
- Primary key `(id, jagex_timestamp)`, with a foreign key to `price_data` that
  cascades on delete.
- `samples` counts the item's priced updates so far, including this one.

| Columns | Module | Needs |
| --- | --- | --- |
| `ema_5`, `ema_20`, `ema_200`, `env_upper`, `env_lower` | `ema.py` | From the first update; EMA-*n* is reliable once `samples >= n`. The envelope is EMA-5 ± 2%. |
| `rsi_14` (+ internal `rsi_avg_gain`, `rsi_avg_loss`) | `rsi.py` | 15 updates, then Wilder smoothing from the previous row |
| `stoch_k`, `stoch_d` | `stochastic.py` | 14 updates for %K and 16 for %D; NULL while the range is flat |
| `vwap_20`, `vwap_dev_pct` | `vwap.py` | 20 updates with some volume |
| `vp_poc`, `vp_vah`, `vp_val` | `volume_profile.py` | 30 updates with some volume |
| `rel_volume` | `relative_volume.py` | 21 updates (this one plus the 20 before) |

Until an indicator has the history it needs, its columns are NULL.

### Adding an indicator

1. Create `services/indicators/<name>.py` with an `Indicator` subclass. Set
   `window` to the number of points it needs, including the current one.
   Implement `compute(points, prev)`. `points` holds the item's latest priced
   `Point(jagex_timestamp, price, volume)`s, oldest first, and `prev` is its
   previous row as a dict, or `None`. Return a dict of column values. Keep it
   pure: no database access.
2. Add an instance to `INDICATORS` in `engine.py`.
3. Add the columns to `ItemIndicatorsModel` and `IndicatorSchema`, and write a
   migration that adds them as nullable. Rows computed earlier keep NULLs, so
   an indicator that carries state must reseed when `prev` lacks it.
4. Add `tests/test_indicators_<name>.py`.
