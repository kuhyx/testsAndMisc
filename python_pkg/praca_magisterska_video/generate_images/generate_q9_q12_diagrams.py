#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 9 and PYTANIE 12.

  PYTANIE 9:  Processes & Threads
    (IPC mechanisms, deadlock, producer-consumer)
  PYTANIE 12: Network optimization models
    (Ford-Fulkerson, Hungarian, CPM, Kruskal, TSP, Min-cost).

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging

from python_pkg.praca_magisterska_video.generate_images._q9q12_network_flow import (
    gen_ford_fulkerson,
    gen_hungarian,
    gen_min_cost_flow,
)
from python_pkg.praca_magisterska_video.generate_images._q9q12_network_graph import (
    gen_cpm,
    gen_kruskal,
    gen_tsp,
)
from python_pkg.praca_magisterska_video.generate_images._q9q12_processes import (
    gen_deadlock_illustration,
    gen_ipc_mechanisms,
    gen_producer_consumer,
)

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating PYTANIE 9 diagrams...")
    gen_ipc_mechanisms()
    gen_deadlock_illustration()
    gen_producer_consumer()

    _logger.info("Generating PYTANIE 12 diagrams...")
    gen_ford_fulkerson()
    gen_hungarian()
    gen_cpm()
    gen_kruskal()
    gen_tsp()
    gen_min_cost_flow()

    _logger.info("All diagrams generated successfully!")
