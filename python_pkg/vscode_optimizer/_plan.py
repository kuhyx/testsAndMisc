"""Turn detected hardware plus current settings into a list of changes.

Pure functions: nothing here reads the filesystem or shells out. Each
proposal carries the value it replaces, so the plan can be shown as a diff.
"""

from __future__ import annotations

from python_pkg.vscode_optimizer._types import _Hw, _Opt

_RAM_THRESHOLDS = ((28000, 4096), (14000, 2048), (7000, 1024))
_DEFAULT_MEM = 512
_MIB_1024 = 1024
_MIN_THREADS = 4
_SUBMOD_LIMIT = 30
_WATCHER_EX: dict[str, bool] = dict.fromkeys(
    [
        "**/.git/objects/**",
        "**/.git/subtree-cache/**",
        "**/node_modules/**",
        "**/.venv/**",
        "**/venv/**",
        "**/__pycache__/**",
        "**/build/**",
        "**/.mypy_cache/**",
        "**/.ruff_cache/**",
        "**/.pytest_cache/**",
        "**/dist/**",
        "**/*.egg-info/**",
    ],
    True,
)
_SEARCH_EX: dict[str, bool] = dict.fromkeys(
    [
        "**/node_modules",
        "**/build",
        "**/.venv",
        "**/venv",
        "**/__pycache__",
        "**/.mypy_cache",
        "**/.ruff_cache",
        "**/.pytest_cache",
        "**/dist",
    ],
    True,
)


def _ideal_mem(ram_mb: int) -> int:
    for threshold, value in _RAM_THRESHOLDS:
        if ram_mb >= threshold:
            return value
    return _DEFAULT_MEM


def _dict_merge_opt(
    cur_settings: dict[str, object],
    key: str,
    ideal: dict[str, bool],
    reason: str,
) -> _Opt | None:
    cur = cur_settings.get(key, {})
    if not isinstance(cur, dict):
        cur = {}
    if all(k in cur for k in ideal):
        return None
    return _Opt(key, {**cur, **ideal}, reason, cur or None)


def _compute_opts(hw: _Hw, cur: dict[str, object]) -> list[_Opt]:
    """Return optimizations based on hardware and current settings."""
    opts: list[_Opt] = []

    def _p(key: str, val: object, reason: str) -> None:
        if cur.get(key) != val:
            opts.append(_Opt(key, val, reason, cur.get(key)))

    threads = max(_MIN_THREADS, hw.cpu_physical_cores)
    _p(
        "search.maxThreads",
        threads,
        f"{hw.cpu_physical_cores} physical cores - use them for workspace search",
    )
    mem = _ideal_mem(hw.ram_total_mb)
    _p(
        "files.maxMemoryForLargeFilesMB",
        mem,
        f"{hw.ram_total_mb // _MIB_1024} GB RAM - allow up to {mem} MB for large files",
    )
    if hw.gpu_vendor in ("NVIDIA", "AMD"):
        _p(
            "terminal.integrated.gpuAcceleration",
            "on",
            f"{hw.gpu_vendor} GPU - enable GPU-rendered terminal",
        )
        smooth = True
        for key in (
            "editor.smoothScrolling",
            "workbench.list.smoothScrolling",
            "terminal.integrated.smoothScrolling",
        ):
            _p(key, smooth, "Smooth scrolling is free with a dedicated GPU")
    no = False
    _p("search.followSymlinks", no, "Avoid duplicate results and wasted I/O")
    for result in (
        _dict_merge_opt(
            cur,
            "files.watcherExclude",
            _WATCHER_EX,
            "Exclude build/cache dirs from file watcher",
        ),
        _dict_merge_opt(
            cur, "search.exclude", _SEARCH_EX, "Exclude build/cache dirs from search"
        ),
    ):
        if result:
            opts.extend([result])
    _p("editor.guides.bracketPairs", "active", "Lightweight visual aid")
    _p(
        "diffEditor.maxComputationTime",
        0,
        f"Fast CPU ({hw.cpu_model}) - compute diffs fully",
    )
    _p("editor.minimap.enabled", no, "Minimap consumes GPU/CPU for little benefit")
    cur_sub = cur.get("git.detectSubmodulesLimit")
    if cur_sub is None or (isinstance(cur_sub, int) and cur_sub < _SUBMOD_LIMIT):
        opts.append(
            _Opt(
                "git.detectSubmodulesLimit",
                _SUBMOD_LIMIT,
                "Higher limit is fine with fast CPU",
                cur_sub,
            )
        )
    return opts


def _gpu_flags(hw: _Hw) -> list[str]:
    """Return Electron flags appropriate for the detected GPU."""
    if hw.gpu_vendor in ("NVIDIA", "AMD"):
        base = [
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
            "--ignore-gpu-blocklist",
            "--enable-features=CanvasOopRasterization",
        ]
        if hw.gpu_vendor == "NVIDIA":
            base.append("--enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoder")
        return base
    if hw.gpu_vendor == "Intel":
        return [
            "--enable-gpu-rasterization",
            "--ignore-gpu-blocklist",
            "--enable-features=VaapiVideoDecodeLinuxGL",
        ]
    return []
