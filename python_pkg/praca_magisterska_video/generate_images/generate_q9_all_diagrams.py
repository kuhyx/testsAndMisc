#!/usr/bin/env python3
"""Generate ALL diagrams for PYTANIE 9: Procesy i wątki (SOI).

Replaces every ASCII diagram with a monochrome A4-printable PNG (300 DPI).
Re-exports all diagram generators from submodules.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Ensure sibling modules are importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _q9_basics import (
    gen_memory_layout,
    gen_pcb_structure,
    gen_process_states,
    gen_process_vs_thread,
    gen_speed_comparison,
    gen_thread_structure,
)
from _q9_classic_sync import (
    gen_classic_problems,
    gen_semaphore_concept,
    gen_sync_comparison,
)
from _q9_ipc import gen_ipc_details, gen_ipc_table, gen_scenario_table
from _q9_race_deadlock import (
    gen_coffman_strategies,
    gen_deadlock_scenario,
    gen_race_condition,
    gen_starvation_priority,
)

__all__ = [
    "gen_classic_problems",
    "gen_coffman_strategies",
    "gen_deadlock_scenario",
    "gen_ipc_details",
    "gen_ipc_table",
    "gen_memory_layout",
    "gen_pcb_structure",
    "gen_process_states",
    "gen_process_vs_thread",
    "gen_race_condition",
    "gen_scenario_table",
    "gen_semaphore_concept",
    "gen_speed_comparison",
    "gen_starvation_priority",
    "gen_sync_comparison",
    "gen_thread_structure",
]

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN — generate all
# ============================================================
if __name__ == "__main__":
    _logger.info("Generating ALL PYTANIE 9 diagrams...")
    gen_process_vs_thread()
    gen_memory_layout()
    gen_process_states()
    gen_thread_structure()
    gen_pcb_structure()
    gen_speed_comparison()
    gen_scenario_table()
    gen_ipc_details()
    gen_ipc_table()
    gen_race_condition()
    gen_deadlock_scenario()
    gen_coffman_strategies()
    gen_starvation_priority()
    gen_classic_problems()
    gen_sync_comparison()
    gen_semaphore_concept()
    _logger.info("All 16 PYTANIE 9 diagrams generated successfully!")
