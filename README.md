# geFlipper

A tool for finding profitable flips on the Old School RuneScape Grand Exchange.
geFlipper collects item prices and trade volumes from the RuneScape Wiki APIs,
stores them in Postgres, and will run trading indicators over that history to
decide what to buy, when to sell, and how long to hold.

> **Status:** early work in progress. The database layer, migrations and a bare
> FastAPI app are in place, with the first background collector (the item
> catalogue). The remaining collectors and the indicators are not built yet.

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
| `backend/` | The FastAPI service. See [`backend/ReadME.md`](backend/ReadME.md) for development, migrations and background tasks. |
| `flake.nix` | Builds the backend Docker image and exports the NixOS modules. |
| `modules/postgres.nix` | NixOS module that runs the Postgres container. |
| `modules/fastapi.nix` | NixOS module that loads the backend image and runs it. |
| `shell.nix` | Development shell with Python and every backend dependency. |
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

## Configuration

The backend reads its database settings from environment variables
(`backend/app/core/config.py`). Never put credentials in the code.

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_USER` | `root` | |
| `DB_PASS` | *(empty)* | Required. |
| `DB_HOST` | `localhost` | `postgres-db` inside the deployed container network. |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `geflipper` | |

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


  outputs = { nixpkgs, geflipper, ... }: {
    nixosConfigurations.<host> = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        geflipper.nixosModules.postgres
        geflipper.nixosModules.fastapi
        # ...your other modules
      ];
    };
  };
}
```
configuration.nix:
```nix
virtualisation.docker.enable = true;
```

### 2. Prepare the server

The modules expect these paths on the host:

| Path | Contents |
| --- | --- |
| `/var/src/secrets/postgres.env` | `POSTGRES_PASSWORD=<password>` |
| `/var/src/secrets/fastapi.env` | `DB_PASS=<same password>` |
| `/var/src/my-services/backend` | A copy of this repo's `backend/` directory. It is mounted into the container at `/app`. |

The image contains only Python and the dependencies. The application code
comes from the mounted directory, so deploying a code change means updating
`/var/src/my-services/backend` and restarting the container:

```sh
rsync -a --delete backend/ <host>:/var/src/my-services/backend/
ssh <host> systemctl restart docker-fastapi-backend
```

### 3. Rebuild and migrate

```sh
nixos-rebuild switch --flake .#<host>
```

Then apply the database migrations (see
[Running migrations in production](backend/ReadME.md#running-migrations-in-production)).
The container doesn't run them on startup.

## Legacy scripts

`init_database.py` and `sync_tables.py` are the first version of the project.
They loaded wiki price data into MariaDB using raw SQL. The FastAPI service
replaces them, and nothing in the current code uses them. They're kept only as
a reference for the wiki API endpoints and table layouts, which the planned
background collectors will reproduce.

## Roadmap

- [ ] Background collectors for the wiki price endpoints
- [ ] API endpoints for querying items and price history
- [ ] Indicators for every tracked item (see [`docs/indicators.md`](docs/indicators.md))
- [ ] Work out how much of an item to buy, how long to hold it, and when to buy and sell
- [ ] Run migrations automatically on deploy
