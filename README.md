# geFlipper

A tool for finding profitable flips on the Old School RuneScape Grand Exchange.
geFlipper collects item prices and trade volumes from the RuneScape Wiki APIs,
stores them in Postgres, and runs trading indicators over that history. The
goal is to decide what to buy, when to sell, and how long to hold.

> **Status:** early work in progress. A background collector records GE prices
> from the Weird Gloop dump each time Jagex publishes an update (about daily).
> An indicator engine then computes EMA, RSI, stochastic, VWAP, volume profile
> and relative volume for every priced item. The API serves the raw prices
> (`/price-data`), per-item snapshots and history (`/items/{id}`,
> `/items/{id}/history`) and indicators (`/items/{id}/indicators`). The
> higher-frequency wiki collectors and buy/sell signals are not built yet.

## How it fits together

```
RuneScape Wiki / Weird Gloop APIs
            │
            ▼
  FastAPI service (backend/)            ◄── HTTP API under /api/v1
    ├─ GE price collector ──signal──► indicator engine
    ├─ SQLAlchemy async models
    └─ Alembic migrations (run on container start)
            │
            ▼
       PostgreSQL 16
```

Both services run as Docker containers on NixOS, defined by the Nix flake in
this repo.

## Repository layout

| Path | What it is |
| --- | --- |
| `backend/` | The FastAPI service and its tests. See [`backend/ReadME.md`](backend/ReadME.md) for development, testing, migrations and background tasks. |
| `flake.nix` | Builds the backend Docker image and exports the NixOS modules. |
| `modules/postgres.nix` | NixOS module that runs the Postgres container. |
| `modules/fastapi.nix` | NixOS module that loads the backend image and runs it. |
| `shell.nix` | Development shell with Python, every backend dependency and the test tools. |
| `docs/indicators.md` | The trading indicators: the reasoning behind them, and what is implemented. |
| `init_database.py`, `sync_tables.py`, `env_template` | The original MariaDB scripts. No longer used; kept for reference only (see [Legacy scripts](#legacy-scripts)). |

## Quick start (local development)

You need [Nix](https://nixos.org/download) and Docker.

```sh
# 1. Start a throwaway Postgres
docker run -d --name geflipper-db -p 5432:5432 \
  -e POSTGRES_USER=root -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=geflipper \
  postgres:16-alpine

# 2. Enter the dev shell and point the backend at the database
nix-shell ./shell.nix # Alternatively, use direnv. $ echo "use nix" > .envrc && direnv allow
export DB_PASS=devpass

# 3. Create the tables
cd backend/app && alembic upgrade head && cd ..

# 4. Run the API (from backend/)
uvicorn app.main:app --reload
```

Check that it's running at <http://localhost:8000/api/v1/health>. The
interactive API docs are at <http://localhost:8000/docs>.

Run the unit tests from `backend/` with `pytest`. They don't need the database
(see [Testing](backend/ReadME.md#testing)).

## API

All routes are under `/api/v1`. The interactive docs at `/docs` list every
parameter.

| Route | Returns |
| --- | --- |
| `GET /health` | `{"status": "ok"}` |
| `GET /price-data` | Every `price_data` row, paginated (`offset`, `limit` ≤ 1000) |
| `GET /items/{id}` | The item's latest snapshot (404 if unknown) |
| `GET /items/{id}/history` | Price points, oldest first, paginated, with optional inclusive `start`/`end` |
| `GET /items/{id}/indicators` | Indicator rows, oldest first, with the same paging and range parameters |

## Configuration

The backend reads its settings from environment variables
(`backend/app/core/config.py`). Never put credentials in the code.

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_USER` | `root` | |
| `DB_PASS` | *(empty)* | Required in practice; nothing checks for it, but Postgres will reject the connection. |
| `DB_HOST` | `localhost` | `postgres-db` inside the deployed container network. |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `geflipper` | |
| `USER_AGENT` | `geFlipper - OSRS item price tracker` | Sent to the wiki APIs, which require a descriptive User-Agent. |
| `ENABLE_COLLECTORS` | `1` | Set to `0` to run the API without the background tasks (the price collector and the indicator engine). |

## Deployment (NixOS)

The flake exports three NixOS modules and one package:

| Output | Purpose |
| --- | --- |
| `nixosModules.postgres` | Runs `postgres:16-alpine` as `postgres-db` on the `fastapi-network` Docker network, storing data in the `postgres_data` volume. |
| `nixosModules.fastapi` | Loads the Nix-built image into Docker at boot and runs it as `fastapi-backend` on port 8000, with `sourcePath` mounted at `/app`. The container runs `alembic upgrade head`, then `uvicorn`. |
| `nixosModules.default` | Imports both modules and sets the fastapi module's `package` and `sourcePath` to this flake's image and `backend/`. |
| `packages.x86_64-linux.backend-image` | The backend image on its own (`nix build .#backend-image`). |

### 1. Update your flake.nix input and output dependencies, and configuration.nix
flake.nix:
```nix
{
  inputs.geflipper = {
    url = "github:Yanall-Boutros/geFlipper"; # or your own fork: "github:<owner>/geFlipper"
    inputs.nixpkgs.follows = "nixpkgs";
  };


  outputs = { nixpkgs, geflipper, ... }@inputs: {
    nixosConfigurations.<host> = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
      	geflipper.nixosModules.default # imports both fastapi and postgres modules, with default packages / configurations
        # ...your other modules
      ];
    };
  };
}
```
configuration.nix:
```nix
virtualisation.docker.enable = true;
services.geflipper.postgres = {
	enable = true;
	environmentFile = "/var/src/secrets/postgres.env";
};
services.geflipper.fastapi = {
	enable = true;
	environmentFile = "/var/src/secrets/fastapi.env";
};

```

### 2. Prepare the server

The modules expect these paths on the host:

| Path | Contents |
| --- | --- |
| `/var/src/secrets/postgres.env` | `POSTGRES_PASSWORD=<password>` |
| `/var/src/secrets/fastapi.env` | `DB_PASS=<same password>` |

### 3. Rebuild

```sh
nix flake update
sudo nixos-rebuild switch
```

Migrations run automatically: the backend container runs
`alembic upgrade head` before starting `uvicorn`. On first start the indicator
engine backfills indicators for every update already in `price_data`.

### 4. Resetting infrastructure

Changes to the flake or to how the services are ordered can leave the Docker
network in a state systemd can't recover from. Stop both containers, then
remove the network; the next `nixos-rebuild switch` (or a restart of
`init-fastapi-net.service`) recreates it:

```sh
sudo systemctl stop docker-fastapi-backend docker-postgres-db
sudo docker network rm fastapi-network
```

## Legacy scripts

`init_database.py` and `sync_tables.py` are the project's original MariaDB
scripts (`pymysql`, credentials from a `.env` built from `env_template`). The
FastAPI backend replaced them, and nothing imports or runs them. They are kept
because they show the wiki API payload shapes.
## Roadmap

- [x] Daily GE price collector (Weird Gloop `os_dump.json`)
- [x] Unit tests for the backend
- [x] API endpoints for querying single items and price history (`/items/{id}`, `/items/{id}/history`)
- [x] Indicators for every tracked item (see [`docs/indicators.md`](docs/indicators.md))
- [x] Run migrations automatically on deploy ( currently migrates via [`flake.nix`](flake.nix) )
- [ ] Work out how much of an item to buy, how long to hold it, and when to buy and sell
