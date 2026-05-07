{ config, lib, pkgs, ... }:
let
  cfg = config.linuxConfigPoc;

  readList = file:
    let
      lines = lib.splitString "\n" (builtins.readFile file);
      trimmed = map lib.strings.trim lines;
    in
      builtins.filter (line: line != "" && !(lib.hasPrefix "#" line)) trimmed;

  pacmanPackageFile = "${toString cfg.repoPath}/fresh-install/pacman_packages.txt";
  aurPackageFile = "${toString cfg.repoPath}/fresh-install/aur_packages.txt";

  pacmanNamesRaw = readList pacmanPackageFile;
  aurLinesRaw = readList aurPackageFile;
  aurNames = map (line: builtins.head (lib.splitString " " line)) aurLinesRaw;

  mappedPacmanNames = map
    (name: if builtins.hasAttr name cfg.packageMap then builtins.getAttr name cfg.packageMap else name)
    pacmanNamesRaw;

  resolvePackage = name: lib.attrByPath (lib.splitString "." name) null pkgs;

  resolvedPacmanPkgs = builtins.filter (pkg: pkg != null) (map resolvePackage mappedPacmanNames);
  missingPacmanPkgs = builtins.filter (name: (resolvePackage name) == null) mappedPacmanNames;
in {
  config = lib.mkIf cfg.enable {
    warnings = [
      "linuxConfigPoc: ${toString (builtins.length resolvedPacmanPkgs)} pacman packages resolved to nixpkgs attrs."
      "linuxConfigPoc: ${toString (builtins.length missingPacmanPkgs)} pacman packages still need mapping/overlays."
      "linuxConfigPoc: ${toString (builtins.length aurNames)} AUR packages detected and not yet represented as Nix derivations."
      "linuxConfigPoc: pacman-wrapper policy/challenges remain imperative scripts; full Nix-native equivalent requires dedicated policy module."
    ];

    environment.systemPackages =
      lib.unique (
        (with pkgs; [
          acpi
          bc
          dex
          i3blocks
          i3lock
          i3status
          iw
          jq
          networkmanagerapplet
          pavucontrol
          terminator
          xss-lock
        ])
        ++ resolvedPacmanPkgs
      );
  };
}
