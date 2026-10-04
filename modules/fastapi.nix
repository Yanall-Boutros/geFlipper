{ config, lib, pkgs, ... }:
let
  cfg = config.services.geflipper.fastapi;
in 
{
  # Automatically load the custom-built image stream into the local Docker daemon on boot
  options.services.geflipper.fastapi = {
    enable = lib.mkEnableOption "FastAPI service";
    package = lib.mkOption {
      type = lib.types.package;
      description = "FastAPI Docker image stream derivation to load.";
    };
    sourcePath = lib.mkOption {
      type = lib.types.path;
      description = "Path to the backend source code directory to mount into /app.";
    };
    environmentFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = "/var/src/secrets/fastapi.env";
      description = "Path to host secrets file containing runtime environment variables for FastAPI.";
    };
  };
  config = lib.mkIf cfg.enable {
    virtualisation.oci-containers = {
      backend = "docker";
      containers.fastapi-backend = {
        image = "fastapi-backend:latest";
        imageFile = cfg.package;
        ports = [ "8000:8000" ];
	volumes = [ 
          "${cfg.sourcePath}:/app"
        ];
        environment = {
          DB_HOST = "postgres-db";
          DB_PORT = "5432";
          DB_USER = "root";
          DB_NAME = "geflipper";
        };
	environmentFiles = lib.optional (cfg.environmentFile != null) cfg.environmentFile;
        extraOptions = [ "--network=fastapi-network" ];
      };
    };
  };
}
