"""Event time, fraud detection, SLA monitoring, and session diagrams for Q20."""

from __future__ import annotations

from _q20_common import (
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    draw_box,
    np,
    plt,
    rng,
    save_fig,
)
import matplotlib.patches as mpatches


# ============================================================
# 3. Event Time vs Processing Time scatter + watermark
# ============================================================
def gen_event_vs_processing_time() -> None:
    """Gen event vs processing time."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.suptitle(
        "Event Time vs Processing Time + Watermark",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # --- Panel 1: Ideal vs Real ---
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.set_xlabel("Event Time", fontsize=FS_LABEL)
    ax.set_ylabel("Processing Time", fontsize=FS_LABEL)
    ax.set_title("Idealny vs Realny świat", fontsize=FS_LABEL, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Ideal line
    ax.plot([0, 9], [0, 9], "k--", lw=1.5, label="ideał (brak opóźnień)")

    # Real scattered points (processing >= event, some out of order)
    event_times = np.sort(rng.uniform(1, 8, 15))
    proc_times = event_times + rng.exponential(0.5, 15)
    # Make some out of order
    idx = [3, 7, 11]
    for i in idx:
        proc_times[i] += 1.5

    ax.scatter(
        event_times, proc_times, c="black", s=30, zorder=5, label="zdarzenia (realne)"
    )

    # Highlight out-of-order
    for i in idx:
        ax.annotate(
            "out-of-order",
            xy=(event_times[i], proc_times[i]),
            xytext=(event_times[i] + 0.8, proc_times[i] + 0.5),
            fontsize=FS_SMALL,
            ha="left",
            arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#555"},
        )

    ax.legend(fontsize=FS_SMALL, loc="upper left")
    ax.text(
        7,
        2,
        "Opóźnienie\nsieciowe ↑",
        fontsize=FS,
        ha="center",
        style="italic",
        color="#555",
    )

    # --- Panel 2: Watermark concept ---
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.set_xlabel("Event Time", fontsize=FS_LABEL)
    ax.set_ylabel("Processing Time", fontsize=FS_LABEL)
    ax.set_title("Watermark — granica postępu", fontsize=FS_LABEL, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Events
    ax.scatter(event_times, proc_times, c="black", s=30, zorder=5)

    # Watermark line (below most points, tracks progress)
    wm_x = np.linspace(0, 9, 50)
    wm_y = wm_x + 0.3  # watermark slightly above ideal
    ax.plot(wm_x, wm_y, "k-", lw=2.5, label="Watermark")
    ax.fill_between(wm_x, 0, wm_y, alpha=0.15, color="gray")

    ax.text(
        2.0,
        1.0,
        'PONIŻEJ watermark:\n„na pewno dotarło"',
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    # Late event
    late_x, late_y = event_times[7], proc_times[7]
    ax.scatter(
        [late_x], [late_y], c="white", s=80, zorder=6, edgecolors="black", linewidths=2
    )
    ax.annotate(
        "LATE DATA!\n(po watermarku)",
        xy=(late_x, late_y),
        xytext=(late_x + 1.2, late_y + 0.8),
        fontsize=FS_SMALL,
        ha="left",
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "lw": 1, "color": LN},
    )

    ax.legend(fontsize=FS_SMALL, loc="upper left")

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, "q20_event_vs_processing_time.png")


# ============================================================
# 4. Tumbling window example — fraud detection
# ============================================================
def gen_tumbling_fraud() -> None:
    """Gen tumbling fraud."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Tumbling Window — fraud detection (okno = 1 min)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Time axis
    ax.annotate(
        "",
        xy=(11.5, 1.0),
        xytext=(0.5, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(6.0, 0.4, "czas", fontsize=FS, ha="center")

    # Window 1: normal
    draw_box(ax, 1.0, 1.5, 4.5, 3.0, "", fill=GRAY4, rounded=True, lw=2)
    ax.text(
        3.25, 4.2, "[14:00 — 14:01]", fontsize=FS_LABEL, ha="center", fontweight="bold"
    )
    # Transactions
    txns1 = ["Sklep A: 50 zł", "Sklep B: 30 zł", "Stacja: 80 zł"]
    for i, t in enumerate(txns1):
        draw_box(
            ax,
            1.3,
            3.3 - i * 0.55,
            4.0,
            0.45,
            t,
            fill=GRAY1,
            fontsize=FS_SMALL,
            rounded=False,
        )
    ax.text(
        3.25,
        1.7,
        "count = 3  →  OK",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color="#2E7D32",
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": "#E8F5E9",
            "edgecolor": "#2E7D32",
        },
    )

    # Window 2: fraud!
    draw_box(ax, 6.0, 1.5, 4.5, 3.0, "", fill=GRAY1, rounded=True, lw=2)
    ax.text(
        8.25, 4.2, "[14:01 — 14:02]", fontsize=FS_LABEL, ha="center", fontweight="bold"
    )
    txns2 = ["ATM Warszawa: 500 zł", "ATM Kraków: 500 zł", "... +45 transakcji"]
    for i, t in enumerate(txns2):
        draw_box(
            ax,
            6.3,
            3.3 - i * 0.55,
            4.0,
            0.45,
            t,
            fill=GRAY3,
            fontsize=FS_SMALL,
            rounded=False,
        )
    ax.text(
        8.25,
        1.7,
        "count = 47  →  ALERT!",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color="#C62828",
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": "#F8D7DA",
            "edgecolor": "#C62828",
        },
    )

    save_fig(fig, "q20_tumbling_fraud.png")


# ============================================================
# 5. Sliding window — SLA monitoring
# ============================================================
def gen_sliding_sla() -> None:
    """Gen sliding sla."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Sliding Window — monitoring SLA (okno=5min, krok=1min)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Time axis
    ax.annotate(
        "",
        xy=(11.5, 0.5),
        xytext=(0.5, 0.5),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    times = ["14:05", "14:06", "14:07", "14:08", "14:09"]
    latencies = [120, 180, 340, 290, 150]
    sla = 200

    for i, (t, lat) in enumerate(zip(times, latencies, strict=False)):
        x = 1.5 + i * 2.0
        ax.text(x, 0.1, t, fontsize=FS, ha="center")

        # Bar proportional to latency
        bar_h = lat / 100.0
        is_breach = lat > sla
        fill = "#F8D7DA" if is_breach else GRAY1
        edge = "#C62828" if is_breach else LN
        draw_box(
            ax,
            x - 0.5,
            1.0,
            1.0,
            bar_h,
            "",
            fill=fill,
            rounded=False,
            edgecolor=edge,
            lw=1.5,
        )
        ax.text(
            x,
            1.0 + bar_h + 0.15,
            f"{lat}ms",
            fontsize=FS,
            ha="center",
            fontweight="bold",
            color="#C62828" if is_breach else LN,
        )

        # Status
        status = "ALERT!" if is_breach else "OK"
        ax.text(
            x,
            1.0 + bar_h + 0.55,
            status,
            fontsize=FS_SMALL,
            ha="center",
            fontweight="bold",
            color="#C62828" if is_breach else "#2E7D32",
        )

    # SLA line
    sla_y = 1.0 + sla / 100.0
    ax.plot([0.8, 11.2], [sla_y, sla_y], "k--", lw=1.5)
    ax.text(11.3, sla_y, f"SLA={sla}ms", fontsize=FS, va="center", fontweight="bold")

    # Sliding window bracket
    ax.annotate(
        "",
        xy=(1.0, 5.3),
        xytext=(5.0, 5.3),
        arrowprops={"arrowstyle": "<->", "lw": 1.5, "color": LN},
    )
    ax.text(3.0, 5.6, "okno = 5 min", fontsize=FS, ha="center", fontweight="bold")

    ax.annotate(
        "",
        xy=(3.0, 4.8),
        xytext=(5.0, 4.8),
        arrowprops={"arrowstyle": "<->", "lw": 1, "color": "#555"},
    )
    ax.text(
        4.0,
        4.4,
        "krok = 1 min\n(nakładanie!)",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    save_fig(fig, "q20_sliding_sla.png")


# ============================================================
# 6. Session window — user sessions
# ============================================================
def gen_session_users() -> None:
    """Gen session users."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 5))
    fig.suptitle(
        "Session Window — sesje użytkowników (gap = 30 min)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # Anna: 2 sessions
    ax = axes[0]
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Użytkownik Anna", fontsize=FS_LABEL, fontweight="bold")

    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )

    # Clicks cluster 1
    for x in [1.0, 1.8, 2.5, 3.2]:
        ax.plot(x, 1.0, "ko", markersize=6)
    # Clicks cluster 2
    for x in [9.0, 9.8, 10.5]:
        ax.plot(x, 1.0, "ko", markersize=6)

    # Sessions
    rect1 = mpatches.FancyBboxPatch(
        (0.7, 1.5),
        2.8,
        1.2,
        boxstyle="round,pad=0.1",
        facecolor=GRAY1,
        edgecolor=LN,
        lw=1.5,
    )
    ax.add_patch(rect1)
    ax.text(
        2.1,
        2.1,
        "Sesja 1\n4 kliknięcia, 12 min",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    rect2 = mpatches.FancyBboxPatch(
        (8.7, 1.5),
        2.1,
        1.2,
        boxstyle="round,pad=0.1",
        facecolor=GRAY3,
        edgecolor=LN,
        lw=1.5,
    )
    ax.add_patch(rect2)
    ax.text(
        9.75,
        2.1,
        "Sesja 2\n3 kliknięcia, 8 min",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    # Gap
    ax.annotate(
        "",
        xy=(8.5, 0.5),
        xytext=(3.8, 0.5),
        arrowprops={"arrowstyle": "<->", "lw": 1.5, "color": LN},
    )
    ax.text(
        6.15,
        0.1,
        "cisza 45 min > gap(30)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        style="italic",
    )

    # Bob: 1 session
    ax = axes[1]
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Użytkownik Bob", fontsize=FS_LABEL, fontweight="bold")

    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )

    # Clicks spread evenly
    bobs = [1.0, 2.5, 4.0, 5.5, 7.0, 8.5, 10.0]
    for x in bobs:
        ax.plot(x, 1.0, "ko", markersize=6)

    rect = mpatches.FancyBboxPatch(
        (0.7, 1.5),
        9.6,
        1.2,
        boxstyle="round,pad=0.1",
        facecolor=GRAY1,
        edgecolor=LN,
        lw=2,
    )
    ax.add_patch(rect)
    ax.text(
        5.5,
        2.1,
        "Sesja 1 (ciągła) — 7 kliknięć, każde < 30 min od poprzedniego",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, "q20_session_users.png")
