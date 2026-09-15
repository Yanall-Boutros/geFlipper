{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
  	python3Packages.numpy
  	python3Packages.requests
  	python3Packages.python-dotenv
    python3Packages.sqlalchemy
	  python3Packages.asyncpg
    python3Packages.alembic
  ];
  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}:$LD_LIBRARY_PATH"
  '';
}
