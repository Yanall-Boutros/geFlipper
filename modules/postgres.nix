{ pkgs, ... }:

{
  #virtualisation.docker.enable = true;

  # Create an internal container bridge network if it doesn't exist
  systemd.services.init-fastapi-net = {
    description = "Create Docker bridge network for FastAPI microservices";
    after = [ "docker.service" ];
    requires = [ "docker.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.docker}/bin/docker network create fastapi-network";
      ExecStop = "${pkgs.docker}/bin/docker network rm fastapi-network";
      ExecStartIgnoreShellModificationCheck = true;
      ExecStartPrev = "-${pkgs.docker}/bin/docker network inspect fastapi-network";
    };
  };

  virtualisation.oci-containers = {
    backend = "docker";
    containers = {
      postgres-db = {
        image = "postgres:16-alpine";
        ports = [ "5432:5432" ];
        environment = {
          POSTGRES_USER = "root";
          POSTGRES_DB = "geflipper";
        };
        environmentFiles = [ "/var/src/secrets/postgres.env" ]; 
        volumes = [ "postgres_data:/var/lib/postgresql/data" ];
        extraOptions = [ "--network=fastapi-network" ];
      };
    };
  };
}
