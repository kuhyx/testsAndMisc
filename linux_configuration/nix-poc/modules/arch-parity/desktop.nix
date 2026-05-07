{ config, lib, ... }:
let
  cfg = config.linuxConfigPoc;
in {
  config = lib.mkIf cfg.enable {
    services.xserver.enable = true;
    services.xserver.windowManager.i3.enable = true;
    services.xserver.displayManager.startx.enable = true;

    # Mirror i3 + i3blocks config deployment using Home Manager.
    home-manager.useGlobalPkgs = true;
    home-manager.useUserPackages = true;
    home-manager.users.${cfg.mainUser} = {
      xdg.configFile."i3/config".source = "${cfg.repoPath}/i3-configuration/i3/config";
      xdg.configFile."i3blocks/config".source = "${cfg.repoPath}/i3-configuration/i3blocks/config";
      xdg.configFile."i3blocks".recursive = true;
      xdg.configFile."i3blocks".source = "${cfg.repoPath}/i3-configuration/i3blocks";
    };
  };
}
