{
  description = "Unified Flake for lean FastAPI and Postgres microservices";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      lib = pkgs.lib;
      
      fastapiImage = pkgs.dockerTools.buildLayeredImage {
        name = "fastapi-backend";
        tag = "latest";
        contents = [
          pkgs.python3
          pkgs.cacert
          (pkgs.python3.withPackages (ps: with ps; [
            fastapi
            uvicorn
            sqlalchemy
            asyncpg
            pydantic
            requests
          ]))
        ];
	extraCommands = ''
          mkdir -p app
          cp -r ${./backend}/* app/
        '';
        config = {
          Cmd = [ "uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "8000" "--app-dir" "/app" ];
          ExposedPorts = { "8000/tcp" = {}; };
          WorkingDir = "/app";
        };
      };
      backendSource = ./backend; # This might be bloat or not needed

    in {
      # Manual build hook: nix build .#backend-image
	packages.${system}.backend-image = fastapiImage;
	nixosModules = {
		postgres = ./modules/postgres.nix;
		fastapi = ./modules/fastapi.nix;
		default = { ... }: {
		  imports = [ ./modules/postgres.nix ./modules/fastapi.nix ];
		  services.geflipper.fastapi.package = lib.mkDefault fastapiImage;
		  services.geflipper.fastapi.sourcePath = lib.mkDefault backendSource;
		};
	};
    };
}
