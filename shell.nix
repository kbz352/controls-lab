{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  nativeBuildInputs = [
    pkgs.python313Packages.rpi-gpio
  ];
}
