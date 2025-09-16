{
  description = "Python development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      pythonPackages = pkgs.python311.withPackages (ps:
        with ps; [
          numpy
          pandas
          pyyaml
          # Testing dependencies
          pytest
          pytest-cov
          pytest-mock
          pytest-benchmark
        ]);
    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          pythonPackages
          pkgs.pyright
          pkgs.ruff
        ];

        shellHook = ''
          echo "Python development environment activated"
        '';
      };
    });
}
