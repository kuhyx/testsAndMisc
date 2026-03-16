#!/usr/bin/env python3
"""Generate ALL diagrams for PYTANIE 20: Analityka danych strumieniowych.

Monochrome, A4-printable PNGs (300 DPI).
Re-exports all diagram generators from submodules.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Ensure sibling modules are importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _q20_architectures import (
    gen_exactly_once,
    gen_lambda_kappa_table,
    gen_lambda_vs_kappa,
    gen_spark_streaming_arch,
)
from _q20_batch_and_windows import gen_batch_vs_streaming, gen_window_types
from _q20_late_and_decisions import gen_decision_tree, gen_late_data_strategies
from _q20_platforms import (
    gen_flink_arch,
    gen_kafka_streams_arch,
    gen_platform_comparison,
    gen_streaming_ecosystem,
    gen_true_vs_microbatch,
)
from _q20_time_monitoring_sessions import (
    gen_event_vs_processing_time,
    gen_session_users,
    gen_sliding_sla,
    gen_tumbling_fraud,
)

__all__ = [
    "gen_batch_vs_streaming",
    "gen_decision_tree",
    "gen_event_vs_processing_time",
    "gen_exactly_once",
    "gen_flink_arch",
    "gen_kafka_streams_arch",
    "gen_lambda_kappa_table",
    "gen_lambda_vs_kappa",
    "gen_late_data_strategies",
    "gen_platform_comparison",
    "gen_session_users",
    "gen_sliding_sla",
    "gen_spark_streaming_arch",
    "gen_streaming_ecosystem",
    "gen_true_vs_microbatch",
    "gen_tumbling_fraud",
    "gen_window_types",
]

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    _logger.info("Generating ALL PYTANIE 20 diagrams...")
    gen_batch_vs_streaming()
    gen_window_types()
    gen_event_vs_processing_time()
    gen_tumbling_fraud()
    gen_sliding_sla()
    gen_session_users()
    gen_streaming_ecosystem()
    gen_true_vs_microbatch()
    gen_platform_comparison()
    gen_kafka_streams_arch()
    gen_flink_arch()
    gen_spark_streaming_arch()
    gen_lambda_vs_kappa()
    gen_lambda_kappa_table()
    gen_exactly_once()
    gen_late_data_strategies()
    gen_decision_tree()
    _logger.info("All 17 PYTANIE 20 diagrams generated successfully!")
