{ config, lib, pkgs, ... }:
let
  cfg = config.linuxConfigPoc;
  repo = toString cfg.repoPath;
  commonScriptPath = with pkgs; [
    bash
    coreutils
    findutils
    gawk
    gnugrep
    gnused
    util-linux
  ];

  customHostsEntries = pkgs.runCommand "linux-config-custom-hosts" { } ''
    sed -n '/^# Custom blocking entries$/,/^EOF$/p' ${cfg.repoPath}/hosts/install.sh \
      | sed '$d' > "$out"
  '';
in {
  config = lib.mkIf cfg.enable {
    networking.extraHosts = builtins.readFile customHostsEntries;

    # Protect hosts lookup ordering against bypasses.
    system.nssDatabases.hosts = [ "files" "myhostname" "dns" ];

    systemd.services.hosts-guard = {
      description = "Enforce canonical /etc/hosts contents";
      after = [ "local-fs.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${repo}/hosts/guard/enforce-hosts.sh";
        Nice = "10";
        IOSchedulingClass = "idle";
      };
      path = commonScriptPath;
    };

    systemd.paths.hosts-guard = {
      description = "Watch /etc/hosts and trigger enforcement";
      wantedBy = [ "multi-user.target" ];
      pathConfig = {
        PathChanged = [ "/etc/hosts" ];
        Unit = "hosts-guard.service";
      };
    };

    systemd.services.nsswitch-guard = {
      description = "Enforce canonical /etc/nsswitch.conf (prevents hosts bypass)";
      after = [ "local-fs.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${repo}/hosts/guard/enforce-nsswitch.sh";
        Nice = "10";
        IOSchedulingClass = "idle";
      };
      path = commonScriptPath;
    };

    systemd.paths.nsswitch-guard = {
      description = "Watch /etc/nsswitch.conf for tampering";
      wantedBy = [ "multi-user.target" ];
      pathConfig = {
        PathChanged = [ "/etc/nsswitch.conf" ];
        Unit = "nsswitch-guard.service";
      };
    };

    systemd.services.resolved-guard = {
      description = "Enforce canonical /etc/systemd/resolved.conf (prevents hosts bypass)";
      after = [ "local-fs.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${repo}/hosts/guard/enforce-resolved.sh";
        Nice = "10";
        IOSchedulingClass = "idle";
      };
      path = commonScriptPath;
    };

    systemd.paths.resolved-guard = {
      description = "Watch /etc/systemd/resolved.conf for tampering";
      wantedBy = [ "multi-user.target" ];
      pathConfig = {
        PathChanged = [ "/etc/systemd/resolved.conf" "/etc/systemd/resolved.conf.d" ];
        Unit = "resolved-guard.service";
      };
    };
  };
}
