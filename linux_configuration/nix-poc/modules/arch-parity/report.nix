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

  resolvePackage = path: lib.attrByPath (lib.splitString "." path) null pkgs;
  existsPath = path: (resolvePackage path) != null;

  mappedRecords = map
    (original:
      let
        mapped = if builtins.hasAttr original cfg.packageMap then builtins.getAttr original cfg.packageMap else original;
      in {
        inherit original mapped;
        resolved = (resolvePackage mapped) != null;
      })
    pacmanNamesRaw;

  unresolvedRecords = builtins.filter (record: !record.resolved) mappedRecords;

  sortStrings = builtins.sort (a: b: a < b);
  sortRecordsByOriginal = builtins.sort (
    a: b:
      if a.original == b.original
      then a.mapped < b.mapped
      else a.original < b.original
  );

  candidatePaths = record:
    let
      pythonCandidate =
        if lib.hasPrefix "python-" record.original
        then "python3Packages.${lib.removePrefix "python-" record.original}"
        else "";
      underscoreFromOriginal = lib.replaceStrings [ "-" ] [ "_" ] record.original;
      dashFromOriginal = lib.replaceStrings [ "_" ] [ "-" ] record.original;
      underscoreFromMapped = lib.replaceStrings [ "-" ] [ "_" ] record.mapped;
      dashFromMapped = lib.replaceStrings [ "_" ] [ "-" ] record.mapped;
      candidates = [
        record.original
        record.mapped
        underscoreFromOriginal
        dashFromOriginal
        underscoreFromMapped
        dashFromMapped
        pythonCandidate
      ];
    in
      lib.unique (builtins.filter (candidate: candidate != "") candidates);

  easySuggestions = record:
    builtins.filter
      (candidate: existsPath candidate)
      (candidatePaths record);
  easySuggestionsSorted = record: sortStrings (easySuggestions record);

  isAurOrOverlayLikely = record:
    (builtins.elem record.original aurNames)
    || (lib.hasSuffix "-git" record.original)
    || (lib.hasPrefix "lib32-" record.original)
    || (lib.hasSuffix "-bin" record.original);

  easyMapRecords = builtins.filter (record: (builtins.length (easySuggestions record)) > 0) unresolvedRecords;
  needsOverlayRecords = builtins.filter
    (record: ((builtins.length (easySuggestions record)) == 0) && (isAurOrOverlayLikely record))
    unresolvedRecords;
  likelyUnavailableRecords = builtins.filter
    (record: ((builtins.length (easySuggestions record)) == 0) && !(isAurOrOverlayLikely record))
    unresolvedRecords;

  easyMapRecordsSorted = sortRecordsByOriginal easyMapRecords;
  needsOverlayRecordsSorted = sortRecordsByOriginal needsOverlayRecords;
  likelyUnavailableRecordsSorted = sortRecordsByOriginal likelyUnavailableRecords;
  aurNamesSorted = sortStrings aurNames;

  formatSimpleRecord = record: "- ${record.original} -> ${record.mapped}";
  formatEasyRecord = record:
    "- ${record.original} -> ${record.mapped} | suggestions: ${lib.concatStringsSep ", " (easySuggestionsSorted record)}";

  renderLines = lines:
    if (builtins.length lines) == 0
    then "- none"
    else lib.concatStringsSep "\n" lines;

  toEasyJsonRecord = record: {
    original = record.original;
    mapped = record.mapped;
    suggestions = easySuggestionsSorted record;
  };

  toSimpleJsonRecord = record: {
    original = record.original;
    mapped = record.mapped;
  };

  reportText = ''
    linux_configuration nix-poc package resolution report
    ================================================

    Source files:
    - ${pacmanPackageFile}
    - ${aurPackageFile}

    Summary:
    - Total pacman package entries: ${toString (builtins.length pacmanNamesRaw)}
    - Unresolved pacman entries after current mapping: ${toString (builtins.length unresolvedRecords)}
    - AUR package entries: ${toString (builtins.length aurNames)}

    Category: easy-map (likely solvable by small mapping/path fixes)
    ---------------------------------------------------------------
    ${renderLines (map formatEasyRecord easyMapRecordsSorted)}

    Category: needs-overlay (AUR/multilib/git/bin packages)
    -------------------------------------------------------
    ${renderLines (map formatSimpleRecord needsOverlayRecordsSorted)}

    Category: likely-unavailable (needs manual investigation)
    ---------------------------------------------------------
    ${renderLines (map formatSimpleRecord likelyUnavailableRecordsSorted)}

    AUR inventory
    -------------
    ${renderLines (map (name: "- ${name}") aurNamesSorted)}
  '';

  reportJson = {
    schemaVersion = "1.0";
    sourceFiles = {
      pacman = pacmanPackageFile;
      aur = aurPackageFile;
    };
    summary = {
      pacmanEntries = builtins.length pacmanNamesRaw;
      unresolvedPacmanEntries = builtins.length unresolvedRecords;
      aurEntries = builtins.length aurNames;
    };
    categories = {
      easyMap = map toEasyJsonRecord easyMapRecordsSorted;
      needsOverlay = map toSimpleJsonRecord needsOverlayRecordsSorted;
      likelyUnavailable = map toSimpleJsonRecord likelyUnavailableRecordsSorted;
    };
    aurInventory = aurNamesSorted;
  };
in {
  config = lib.mkIf (cfg.enable && cfg.enableResolutionReport) {
    warnings = [
      "linuxConfigPoc: package resolution report generated at /etc/${cfg.resolutionReportEtcPath}${lib.optionalString cfg.enableResolutionReportJson " and /etc/${cfg.resolutionReportJsonEtcPath}"}"
    ];

    environment.etc = {
      "${cfg.resolutionReportEtcPath}".text = reportText;
    } // lib.optionalAttrs cfg.enableResolutionReportJson {
      "${cfg.resolutionReportJsonEtcPath}".text = builtins.toJSON reportJson;
    };
  };
}
