{ pkgs, fastapiImage, ... }:

{
  #virtualisation.docker.enable = true;

  # Automatically load the custom-built image stream into the local Docker daemon on boot
  systemd.services.load-fastapi-image = {
    description = "Load Nix-built FastAPI image into local Docker";
    after = [ "docker.service" ];
    requires = [ "docker.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.bash}/bin/bash -c '${fastapiImage} | ${pkgs.docker}/bin/docker load'";
    };
  };

  virtualisation.oci-containers = {
    backend = "docker";
    containers = {
      fastapi-backend = {
        image = "fastapi-backend:latest"; 
        imageFile = null; 
        ports = [ "8000:8000" ];
        volumes = [ "/var/src/my-services/backend:/app" ];
        environment = {
          # DB_PASS must be provided via the environment file below
          DB_HOST = "postgres-db";
          DB_PORT = "5432";
          DB_USER = "root";
          DB_NAME = "geflipper";
        };
        environmentFiles = [ "/var/src/secrets/fastapi.env" ];
        extraOptions = [ "--network=fastapi-network" ];
      };
    };
  };
}
