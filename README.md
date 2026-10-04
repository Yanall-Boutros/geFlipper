# geFlipper

A tool for finding profitable flips on the Old School RuneScape Grand Exchange.
geFlipper collects item prices and trade volumes from the RuneScape Wiki APIs,
stores them in Postgres, and will run trading indicators over that history to
decide what to buy, when to sell, and how long to hold.

> **Status:** early work in progress. The database layer, migrations, unit
> tests and a FastAPI app are in place. The first background collector records
> daily GE prices from the Weird Gloop dump, and `GET /api/v1/price-data` serves
> them. The remaining collectors and the indicators are not built yet.

## How it fits together

```
RuneScape Wiki / Weird Gloop APIs
            │
            ▼
  FastAPI service (backend/)            ◄── HTTP API under /api/v1
    ├─ background collectors
    ├─ SQLAlchemy async models
    └─ Alembic migrations
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
| `docs/indicators.md` | Notes on the trading indicators planned for flipping. |
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

## Configuration

The backend reads its settings from environment variables
(`backend/app/core/config.py`). Never put credentials in the code.

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_USER` | `root` | |
| `DB_PASS` | *(empty)* | Required. |
| `DB_HOST` | `localhost` | `postgres-db` inside the deployed container network. |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `geflipper` | |
| `USER_AGENT` | `geFlipper - OSRS item price tracker` | Sent to the wiki APIs, which require a descriptive User-Agent. |
| `ENABLE_COLLECTORS` | `1` | Set to `0` to run the API without the background collectors. |

## Deployment (NixOS)

The flake exports two NixOS modules and one package:

| Output | Purpose |
| --- | --- |
| `nixosModules.postgres` | Runs `postgres:16-alpine` as `postgres-db` on the `fastapi-network` Docker network, storing data in the `postgres_data` volume. |
| `nixosModules.fastapi` | Loads the Nix-built image into Docker at boot and runs it as `fastapi-backend` on port 8000. |
| `packages.x86_64-linux.backend-image` | The backend image on its own (`nix build .#backend-image`). |

### 1. Update your flake.nix input and output dependencies, and configuration.nix
flake.nix:
```nix
{
  inputs.geflipper = {
	url = "github:Yanall-Boutros/geFlipper";# Alternatively, your own repo "github:<owner>/geFlipper";
	inputs.nixpkgs.follows = "nixpkgs";
  }


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

### 3. Rebuild and migrate

```sh
nix flake update
nixos-rebuild switch

```

### 4. Resetting infrastructure
Updates to the flake and how the services are scheduled might break previous builds. Resetting the docker network should allow systemd to appropriately handle future updates.
```
sudo docker stop postgres-db 
docker network rm fastapi-network 

```
## Roadmap

- [x] Daily GE price collector (Weird Gloop `os_dump.json`)
- [x] Unit tests for the backend
- [ ] Background collectors for the wiki price endpoints (`/latest`, `/5m`, `/1h`, `/timeseries`)
- [ ] API endpoints for querying single items and price history (so far only a paginated `/price-data` list)
- [ ] Indicators for every tracked item (see [`docs/indicators.md`](docs/indicators.md))
- [ ] Work out how much of an item to buy, how long to hold it, and when to buy and sell
- [x] Run migrations automatically on deploy ( currently migrates via [`flake.nix`](flake.nix) )
