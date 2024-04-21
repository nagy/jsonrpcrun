{
  pkgs ? import <nixpkgs> { },
  lib ? pkgs.lib,
}:

pkgs.stdenv.mkDerivation {
  name = "jsonrpcrun";

  src = lib.cleanSource ./.;

  buildInputs = [ pkgs.python3 ];

  installPhase = ''
    runHook preInstall

    install -Dm755 jsonrpcrun.py $out/bin/jsonrpcrun
    patchShebangs $out/bin/jsonrpcrun

    runHook postInstall
  '';
}
