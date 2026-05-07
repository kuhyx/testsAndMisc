{ config, lib, pkgs, ... }:
let
  cfg = config.linuxConfigPoc;
  repo = toString cfg.repoPath;
  commonScriptPath = with pkgs; [
    bash
    coreutils
    curl
    findutils
    gawk
    gnugrep
    gnused
    procps
    util-linux
  ];
in {
  config = lib.mkIf cfg.enable {
    systemd.services.periodic-system-maintenance = {
      description = "Periodic System Maintenance (Pacman Wrapper & Hosts File)";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        User = "root";
        ExecStart = "${repo}/scripts/system-maintenance/bin/periodic-system-maintenance.sh";
        StandardOutput = "journal";
        StandardError = "journal";
        TimeoutStartSec = "300";
        TimeoutStopSec = "30";
        Restart = "no";
      };
      path = commonScriptPath;
    };

    systemd.timers.periodic-system-maintenance = {
      description = "Run Periodic System Maintenance every hour";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "hourly";
        OnBootSec = "5min";
        RandomizedDelaySec = "300";
        Persistent = true;
      };
      unitConfig = {
        Requires = "periodic-system-maintenance.service";
      };
    };

    systemd.services.periodic-system-startup = {
      description = "System Maintenance on Startup (Pacman Wrapper & Hosts File)";
      after = [ "network-online.target" "systemd-resolved.service" ];
      wants = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        User = "root";
        ExecStart = "${repo}/scripts/system-maintenance/bin/periodic-system-maintenance.sh";
        StandardOutput = "journal";
        StandardError = "journal";
        RemainAfterExit = true;
        TimeoutStartSec = "300";
        TimeoutStopSec = "30";
      };
      path = commonScriptPath;
    };

    systemd.services.hosts-file-monitor = {
      description = "Hosts File Monitor and Auto-Restore Service";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "simple";
        User = "root";
        ExecStart = "${repo}/scripts/system-maintenance/bin/hosts-file-monitor.sh";
        Restart = "always";
        RestartSec = "10";
        StandardOutput = "journal";
        StandardError = "journal";
        NoNewPrivileges = false;
        PrivateTmp = true;
        MemoryMax = "50M";
        CPUQuota = "10%";
      };
      path = commonScriptPath;
    };

    systemd.services.auto-system-update = {
      description = "Automatic System Update (pacman + yay AUR)";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      serviceConfig = {
        Type = "oneshot";
        User = "root";
        ExecStart = "${repo}/scripts/system-maintenance/bin/auto-system-update.sh";
        StandardOutput = "journal";
        StandardError = "journal";
        TimeoutStartSec = "1800";
        TimeoutStopSec = "30";
        Restart = "no";
      };
      path = commonScriptPath;
    };

    systemd.timers.auto-system-update = {
      description = "Run Automatic System Update daily";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "*-*-* 04:00:00";
        RandomizedDelaySec = "1800";
        Persistent = true;
      };
      unitConfig = {
        Requires = "auto-system-update.service";
      };
    };
  };
}
