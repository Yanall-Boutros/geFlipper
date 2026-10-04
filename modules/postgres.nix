{ config, lib, pkgs, ... }:
let
	cfg = config.services.geflipper.postgres;
in
{
	options.services.geflipper.postgres = {
	enable = lib.mkEnableOption "PostgreSQL database service" // { default = true; };

	environmentFile = lib.mkOption {
			type = lib.types.nullOr lib.types.str;
			default = "/var/src/secrets/postgres.env";
			description = "Path to host secrets file containing POSTGRES_PASSWORD.";
		};
	};
	config = lib.mkIf cfg.enable {
    		# Create internal container bridge network if it doesn't exist
    		systemd.services.init-fastapi-net = {
    		  description = "Create Docker bridge network for FastAPI microservices";
    		  after = [ "docker.service" ];
    		  requires = [ "docker.service" ];
    		  wantedBy = [ "multi-user.target" ];
    		  serviceConfig = {
    		    Type = "oneshot";
    		    RemainAfterExit = true;
		    ExecStart = "-${pkgs.docker}/bin/docker network create fastapi-network";
		    ExecStop = "-${pkgs.docker}/bin/docker network rm fastapi-network";
    		  };
    		};

		systemd.services.docker-postgres-db = {
      			after = [ "init-fastapi-net.service" ];
      			requires = [ "init-fastapi-net.service" ];
    		};

		virtualisation.oci-containers = {
			backend = "docker";
			containers = {
				postgres-db = {
					image         = "postgres:16-alpine";
					ports         = [ "5432:5432" ];
					environment   = {
						POSTGRES_USER = "root";
						POSTGRES_DB   = "geflipper";
					};
					environmentFiles = [ "/var/src/secrets/postgres.env" ]; 
					volumes          = [ "postgres_data:/var/lib/postgresql/data" ];
					extraOptions     = [ "--network=fastapi-network" ];
				};
			};
		};
	};
}
