{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  nativeBuildInputs = [
    pkgs.python313Packages.rpi-gpio
    pkgs.python313Packages.numpy
    pkgs.python313Packages.openpyxl # for writing to xlsx
    pkgs.python313Packages.pandas
  ];
}
