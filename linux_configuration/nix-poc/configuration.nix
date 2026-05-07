{ pkgs, ... }:
{
  imports = [
    ./modules/arch-parity-poc.nix
  ];

  linuxConfigPoc = {
    enable = true;
    mainUser = "kuhy";

    # Turn this on when you intentionally want to run the original imperative
    # shell installers during activation (hosts install + guard setup, etc.).
    # Keep it off by default for safe evaluation and incremental migration.
    enableImperativeBootstrap = false;
  };

  # Minimal baseline the host config still needs while this remains a POC.
  networking.hostName = "arch-parity-poc";
  time.timeZone = "Europe/Warsaw";

  # Convenience tools for verification/debugging during migration.
  environment.systemPackages = with pkgs; [
    git
    jq
  ];

  system.stateVersion = "25.05";
}
