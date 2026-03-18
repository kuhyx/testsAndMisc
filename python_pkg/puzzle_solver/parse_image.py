"""Parse a puzzle screenshot into a solvable JSON representation.

Pipeline
--------
1. Threshold + contour detection  →  find square bounding boxes
2. Cluster centres into a regular grid  →  (row, col) for each square
3. Analyse each square's interior  →  classify type
4. Pair teleporters and key/lock  →  assign group IDs
5. Export JSON (editable by hand before solving)
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

_MIN_SQUARE_AREA = 80
_MAX_SQUARE_AREA = 12000
_MIN_ASPECT_RATIO = 0.45
_PLAYER_FILL_THRESHOLD = 0.40
_NORMAL_FILL_CEILING = 0.12
_MIN_INTERIOR_SIZE = 6
_RING_CIRCULARITY = 0.65
_RING_AREA_RATIO = 0.08

# ── Public API ───────────────────────────────────────────────────────


def parse_image(image_path: str, *, threshold: int = 55) -> dict:
    """Parse a screenshot and return a puzzle dict (ready for solver or JSON)."""
    img = cv2.imread(image_path)
    if img is None:
        msg = f"Cannot load image: {image_path}"
        raise FileNotFoundError(msg)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    raw = _detect_square_candidates(gray, threshold)
    squares = _merge_overlapping(raw)
    grid_map = _snap_to_grid(squares)
    classified = _classify_all(gray, grid_map)
    _assign_teleporter_and_kl_groups(classified)
    return _build_output(classified)


def save_puzzle(puzzle: dict, path: str) -> None:
    """Write puzzle dict to a JSON file."""
    with Path(path).open("w") as f:
        json.dump(puzzle, f, indent=2)


# ── Square detection ─────────────────────────────────────────────────


def _detect_square_candidates(
    gray: np.ndarray, thresh: int
) -> list[tuple[int, int, int, int]]:
    _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[int, int, int, int]] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < _MIN_SQUARE_AREA or area > _MAX_SQUARE_AREA:
            continue
        aspect = min(w, h) / max(w, h)
        if aspect < _MIN_ASPECT_RATIO:
            continue
        candidates.append((x, y, w, h))
    return candidates


def _merge_overlapping(
    candidates: list[tuple[int, int, int, int]],
) -> list[tuple[int, int, int, int]]:
    """Merge bounding boxes whose centres are very close."""
    if not candidates:
        return []

    cands = sorted(candidates, key=lambda c: c[2] * c[3], reverse=True)
    used = [False] * len(cands)
    merged: list[tuple[int, int, int, int]] = []

    for i, (x1, y1, w1, h1) in enumerate(cands):
        if used[i]:
            continue
        cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
        group = [(x1, y1, w1, h1)]
        used[i] = True

        for j in range(i + 1, len(cands)):
            if used[j]:
                continue
            x2, y2, w2, h2 = cands[j]
            cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2
            if (
                abs(cx1 - cx2) < max(w1, w2) * 0.55
                and abs(cy1 - cy2) < max(h1, h2) * 0.55
            ):
                group.append(cands[j])
                used[j] = True

        gx = min(g[0] for g in group)
        gy = min(g[1] for g in group)
        gx2 = max(g[0] + g[2] for g in group)
        gy2 = max(g[1] + g[3] for g in group)
        merged.append((gx, gy, gx2 - gx, gy2 - gy))

    return merged


# ── Grid snapping ────────────────────────────────────────────────────


def _cluster_values(vals: list[int], min_gap: int) -> list[int]:
    if not vals:
        return []
    vals = sorted(vals)
    clusters: list[list[int]] = [[vals[0]]]
    for v in vals[1:]:
        if v - clusters[-1][-1] < min_gap:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(np.mean(c)) for c in clusters]


def _snap_to_grid(
    squares: list[tuple[int, int, int, int]],
) -> dict[tuple[int, int], tuple[int, int, int, int]]:
    centres = [(x + w // 2, y + h // 2) for x, y, w, h in squares]
    xs = [c[0] for c in centres]
    ys = [c[1] for c in centres]

    def _median_gap(vals: list[int]) -> int:
        s = sorted(set(vals))
        gaps = [s[i + 1] - s[i] for i in range(len(s) - 1)]
        return int(np.median(gaps)) if gaps else 30

    x_gap = max(8, int(_median_gap(xs) * 0.4))
    y_gap = max(8, int(_median_gap(ys) * 0.4))

    x_clusters = _cluster_values(xs, x_gap)
    y_clusters = _cluster_values(ys, y_gap)

    grid: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for sq, (cx, cy) in zip(squares, centres, strict=False):
        col = min(range(len(x_clusters)), key=lambda i: abs(x_clusters[i] - cx))
        row = min(range(len(y_clusters)), key=lambda i: abs(y_clusters[i] - cy))
        grid[(row, col)] = sq
    return grid


# ── Classification ───────────────────────────────────────────────────


def _classify_all(
    gray: np.ndarray,
    grid_map: dict[tuple[int, int], tuple[int, int, int, int]],
) -> dict[tuple[int, int], dict]:
    classified: dict[tuple[int, int], dict] = {}
    for (row, col), (x, y, w, h) in grid_map.items():
        sq_type, extra = _classify_one(gray, (x, y, w, h))
        classified[(row, col)] = {
            "pos": [row, col],
            "type": sq_type,
            "pixel_center": [x + w // 2, y + h // 2],
            "pixel_bbox": [x, y, w, h],
            **extra,
        }
    return classified


Bbox = tuple[int, int, int, int]


def _classify_by_fill(
    fill: float,
    gray: np.ndarray,
    bbox: Bbox,
    interior: np.ndarray,
) -> tuple[str, dict] | None:
    """Try to classify based on fill ratio and feature detectors."""
    if fill > _PLAYER_FILL_THRESHOLD:
        return "player", {}
    if fill < _NORMAL_FILL_CEILING:
        return "normal", {}

    antenna = _detect_antenna(gray, bbox)
    if antenna:
        return "teleporter", {"antenna_sides": antenna}
    if _is_ring_pattern(interior):
        return "goal", {}

    return _classify_interior_feature(fill, interior)


def _classify_interior_feature(
    fill: float,
    interior: np.ndarray,
) -> tuple[str, dict] | None:
    """Classify portal, key/lock, or return None for unknown."""
    side = _detect_portal_side(interior)
    if side:
        return "portal", {"side": side}
    if _has_interior_feature(interior):
        return "key_or_lock", {"fill_ratio": round(fill, 3)}
    return None


def _classify_one(
    gray: np.ndarray,
    bbox: Bbox,
) -> tuple[str, dict]:
    x, y, w, h = bbox
    border = max(3, min(w, h) // 5)
    ix1, iy1 = x + border, y + border
    ix2, iy2 = x + w - border, y + h - border
    if ix2 <= ix1 or iy2 <= iy1:
        return "normal", {}

    interior = gray[iy1:iy2, ix1:ix2]
    fill = float(np.mean(interior) / 255.0)

    result = _classify_by_fill(fill, gray, bbox, interior)
    if result is not None:
        return result
    return "unknown", {"fill_ratio": round(fill, 3)}


# ── Feature detectors ────────────────────────────────────────────────


def _detect_antenna(
    gray: np.ndarray,
    bbox: Bbox,
    margin: int = 8,
    thr: float = 0.08,
) -> list[str] | None:
    """Check for bright pixels in a narrow strip outside each edge."""
    x, y, w, h = bbox
    ih, iw = gray.shape
    sides: list[str] = []
    qw, qh = w // 4, h // 4  # quarter-width / height

    # up
    if y > margin:
        s = gray[y - margin : y - 1, x + qw : x + w - qw]
        if s.size and float(np.mean(s) / 255) > thr:
            sides.append("up")
    # down
    if y + h + margin < ih:
        s = gray[y + h + 1 : y + h + margin, x + qw : x + w - qw]
        if s.size and float(np.mean(s) / 255) > thr:
            sides.append("down")
    # left
    if x > margin:
        s = gray[y + qh : y + h - qh, x - margin : x - 1]
        if s.size and float(np.mean(s) / 255) > thr:
            sides.append("left")
    # right
    if x + w + margin < iw:
        s = gray[y + qh : y + h - qh, x + w + 1 : x + w + margin]
        if s.size and float(np.mean(s) / 255) > thr:
            sides.append("right")

    return sides or None


def _is_ring_pattern(interior: np.ndarray) -> bool:
    h, w = interior.shape
    if h < _MIN_INTERIOR_SIZE or w < _MIN_INTERIOR_SIZE:
        return False

    _, bw = cv2.threshold(interior, 40, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        peri = cv2.arcLength(cnt, closed=True)
        if peri == 0:
            continue
        circ = 4 * np.pi * area / (peri * peri)
        if circ > _RING_CIRCULARITY and area > (h * w) * _RING_AREA_RATIO:
            return True
    return False


def _detect_portal_side(interior: np.ndarray) -> str | None:
    h, w = interior.shape
    if h < _MIN_INTERIOR_SIZE or w < _MIN_INTERIOR_SIZE:
        return None

    thirds_w, thirds_h = w // 3, h // 3
    regions = {
        "left": float(np.mean(interior[:, :thirds_w])),
        "right": float(np.mean(interior[:, w - thirds_w :])),
        "up": float(np.mean(interior[:thirds_h, :])),
        "down": float(np.mean(interior[h - thirds_h :, :])),
    }

    best = max(regions, key=lambda k: regions[k])
    opposites = {"left": "right", "right": "left", "up": "down", "down": "up"}
    opp = regions[opposites[best]]

    if regions[best] > max(opp * 2.5, 8):
        return best
    return None


def _has_interior_feature(interior: np.ndarray) -> bool:
    _, bw = cv2.threshold(interior, 40, 255, cv2.THRESH_BINARY)
    total_white = int(np.sum(bw > 0))
    return total_white > interior.size * 0.06


# ── Teleporter / key-lock grouping ───────────────────────────────────


def _assign_teleporter_and_kl_groups(classified: dict[tuple[int, int], dict]) -> None:
    # ── Teleporters ──
    tele = [(p, d) for p, d in classified.items() if d["type"] == "teleporter"]
    gid = 1
    used: set[tuple[int, int]] = set()
    for i, (p1, d1) in enumerate(tele):
        if p1 in used:
            continue
        s1 = set(d1.get("antenna_sides", []))
        for p2, d2 in tele[i + 1 :]:
            if p2 in used:
                continue
            s2 = set(d2.get("antenna_sides", []))
            if s1 == s2:
                d1["group"] = gid
                d2["group"] = gid
                used |= {p1, p2}
                gid += 1
                break

    # pair any remaining teleporters sequentially
    unpaired = [
        p
        for p, d in classified.items()
        if d["type"] == "teleporter" and "group" not in d
    ]
    for i in range(0, len(unpaired) - 1, 2):
        classified[unpaired[i]]["group"] = gid
        classified[unpaired[i + 1]]["group"] = gid
        gid += 1

    # ── Key / lock ──
    kl = [p for p, d in classified.items() if d["type"] == "key_or_lock"]
    lid = 1
    for i in range(0, len(kl) - 1, 2):
        classified[kl[i]]["type"] = "key"
        classified[kl[i]]["lock_id"] = lid
        classified[kl[i + 1]]["type"] = "lock"
        classified[kl[i + 1]]["lock_id"] = lid
        lid += 1
    # odd one out → mark unknown
    if len(kl) % 2:
        classified[kl[-1]]["type"] = "unknown"


# ── Output builder ───────────────────────────────────────────────────


def _build_output(classified: dict[tuple[int, int], dict]) -> dict:
    squares: list[dict] = []
    notes: list[str] = []

    for pos in sorted(classified):
        d = classified[pos]
        sq: dict = {"pos": d["pos"], "type": d["type"]}

        if "side" in d:
            sq["side"] = d["side"]
        if "group" in d:
            sq["group"] = d["group"]
        if "lock_id" in d:
            sq["lock_id"] = d["lock_id"]

        # keep pixel info for debugging (prefixed with _)
        sq["_pixel_center"] = d["pixel_center"]
        sq["_pixel_bbox"] = d["pixel_bbox"]

        if d["type"] == "unknown":
            notes.append(
                f"grid {d['pos']} pixel {d['pixel_center']}: "
                f"classified 'unknown' (fill={d.get('fill_ratio', '?')}) "
                "- edit type manually"
            )
        squares.append(sq)

    return {"squares": squares, "notes": notes}


# ── Debug visualisation ──────────────────────────────────────────────

TYPE_COLOURS = {
    "normal": (200, 200, 200),
    "player": (0, 255, 0),
    "goal": (0, 200, 255),
    "portal": (255, 100, 0),
    "teleporter": (255, 0, 255),
    "key": (0, 255, 255),
    "lock": (0, 0, 255),
    "key_or_lock": (100, 100, 255),
    "unknown": (0, 0, 200),
}


def draw_debug(image_path: str, puzzle: dict, output_path: str) -> None:
    """Draw classified squares on the image and save for visual verification."""
    img = cv2.imread(image_path)
    if img is None:
        return

    for sq in puzzle["squares"]:
        x, y, w, h = sq["_pixel_bbox"]
        colour = TYPE_COLOURS.get(sq["type"], (128, 128, 128))
        cv2.rectangle(img, (x, y), (x + w, y + h), colour, 2)
        label = sq["type"][0].upper()
        if sq["type"] == "portal":
            arrows = {"left": "<", "right": ">", "up": "^", "down": "v"}
            label = arrows.get(sq.get("side", ""), "O")
        cv2.putText(
            img, label, (x + 2, y + h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour, 1
        )

    cv2.imwrite(output_path, img)
