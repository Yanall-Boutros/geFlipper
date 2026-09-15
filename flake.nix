{
  description = "Unified Flake for lean FastAPI and Postgres microservices";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      
      # The ultra-lean, optimized OCI image definition
      fastapiImage = pkgs.dockerTools.streamLayeredImage {
        name = "fastapi-backend";
        tag = "latest";
        contents = [
          pkgs.python311
          pkgs.cacert
          (pkgs.python311.withPackages (ps: with ps; [
            fastapi
            uvicorn
            psycopg2
          ]))
        ];
        config = {
          Cmd = [ "uvicorn" "main:app" "--host" "0.0.0.0" "--port" "8000" "--app-dir" "/app" ];
          ExposedPorts = { "8000/tcp" = {}; };
          WorkingDir = "/app";
        };
      };

    in {
      # Manual build hook: nix build .#backend-image
      packages.${system}.backend-image = fastapiImage;

      # --- EXPORT SEPARATE MODULES ---
      nixosModules = {
        # Module 1: Just the postgres database setup
        postgres = import ./modules/postgres.nix;

        # Module 2: Just the fastapi app (passing the compiled image package into it)
        fastapi = { config, ... }: {
          imports = [ (import ./modules/fastapi.nix { inherit pkgs fastapiImage; }) ];
        };
      };
    };
}
