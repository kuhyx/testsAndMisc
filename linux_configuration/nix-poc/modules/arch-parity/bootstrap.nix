{ config, lib, ... }:
let
  cfg = config.linuxConfigPoc;
  repo = toString cfg.repoPath;
in {
  config = lib.mkIf (cfg.enable && cfg.enableImperativeBootstrap) {
    system.activationScripts.linuxConfigImperativeBootstrap = {
      text = ''
        echo "[linuxConfigPoc] Running imperative bootstrap scripts"
        bash ${repo}/hosts/install.sh || true
        bash ${repo}/hosts/guard/setup_hosts_guard.sh || true
        bash ${repo}/scripts/setup_periodic_system.sh || true
      '';
      deps = [ "users" "groups" ];
    };
  };
}
