{ ... }:
{
  imports = [
    ./arch-parity/options.nix
    ./arch-parity/packages.nix
    ./arch-parity/report.nix
    ./arch-parity/desktop.nix
    ./arch-parity/system-maintenance.nix
    ./arch-parity/hosts-guards.nix
    ./arch-parity/bootstrap.nix
  ];
}
