{ lib, ... }:
{
  options.linuxConfigPoc = {
    enable = lib.mkEnableOption "Arch linux_configuration parity proof-of-concept";

    repoPath = lib.mkOption {
      type = lib.types.path;
      default = ../../..;
      description = "Path to the linux_configuration repository root.";
    };

    mainUser = lib.mkOption {
      type = lib.types.str;
      default = "kuhy";
      description = "Primary desktop username for user-scoped config (i3/i3blocks).";
    };

    enableImperativeBootstrap = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Run original shell installers at activation (hosts + guard + periodic setup).";
    };

    enableResolutionReport = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Generate a package resolution report grouped by migration category.";
    };

    resolutionReportEtcPath = lib.mkOption {
      type = lib.types.str;
      default = "linux-config-poc/package-resolution-report.txt";
      description = "Path under /etc where the package resolution report is materialized.";
    };

    enableResolutionReportJson = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Generate a machine-readable JSON package resolution report.";
    };

    resolutionReportJsonEtcPath = lib.mkOption {
      type = lib.types.str;
      default = "linux-config-poc/package-resolution-report.json";
      description = "Path under /etc where the JSON package resolution report is materialized.";
    };

    packageMap = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = {
        # Fonts / desktop
        "ttf-dejavu" = "dejavu_fonts";
        "noto-fonts" = "noto-fonts";
        "ttf-font-awesome" = "font-awesome";
        "adobe-source-sans-pro-fonts" = "source-sans";
        "ttf-liberation" = "liberation_ttf";

        # Toolchain / language ecosystems
        "go-tools" = "gotools";
        "cargo" = "cargo";
        "rust" = "rustc";
        "nodejs" = "nodejs";
        "npm" = "nodejs";
        "yarn" = "yarn";
        "node-gyp" = "nodePackages.node-gyp";
        "lua52" = "lua5_2";

        # Python package translations
        "python-nose" = "python3Packages.nose";
        "python-pyproject-metadata" = "python3Packages.pyproject-metadata";
        "meson-python" = "python3Packages.meson-python";
        "python-numpy" = "python3Packages.numpy";
        "python-markdown" = "python3Packages.markdown";
        "python-pyparsing" = "python3Packages.pyparsing";
        "python-pyqt5" = "python3Packages.pyqt5";
        "python-pefile" = "python3Packages.pefile";
        "python-booleanoperations" = "python3Packages.booleanoperations";
        "python-brotli" = "python3Packages.brotli";
        "python-defcon" = "python3Packages.defcon";
        "python-fontmath" = "python3Packages.fontmath";
        "python-fontpens" = "python3Packages.fontpens";
        "python-fonttools" = "python3Packages.fonttools";
        "python-fs" = "python3Packages.fs";
        "python-tqdm" = "python3Packages.tqdm";
        "python-unicodedata2" = "python3Packages.unicodedata2";
        "python-zopfli" = "python3Packages.zopfli";
        "python-pyaml" = "python3Packages.pyyaml";

        # Java / Perl
        "java-hamcrest" = "hamcrest";
        "perl-font-ttf" = "perlPackages.FontTTF";
        "perl-sort-versions" = "perlPackages.SortVersions";

        # Multimedia / desktop mismatches
        "pavucontrol-qt" = "pavucontrol";
        "qt5-wayland" = "qt5.qtwayland";
        "qt6-tools" = "qt6.full";
        "qt6-shadertools" = "qt6.qtshadertools";
        "ffmpeg" = "ffmpeg-full";
        "pyside6" = "python3Packages.pyside6";

        # TeX stack consolidation
        "texlive-plaingeneric" = "texliveFull";
        "texlive-latexextra" = "texliveFull";
        "texlive-bibtexextra" = "texliveFull";
        "texlive-pictures" = "texliveFull";
        "texlive-fontsextra" = "texliveFull";
        "texlive-formatsextra" = "texliveFull";
        "texlive-pstricks" = "texliveFull";
        "texlive-games" = "texliveFull";
        "texlive-humanities" = "texliveFull";
        "texlive-science" = "texliveFull";
      };
      description = "Mapping from Arch package names to nixpkgs attributes.";
    };
  };
}
