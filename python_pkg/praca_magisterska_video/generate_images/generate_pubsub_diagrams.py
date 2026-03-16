#!/usr/bin/env python3
"""Generate Pub/Sub diagrams for PYTANIE 19.

  Subscription types (4 separate images):
    1. Topic-based
    2. Content-based
    3. Type-based
    4. Hierarchical (wildcards)
  Delivery guarantees (3 separate images):
    5. At-most-once
    6. At-least-once
    7. Exactly-once.

All: A4-width, B&W, 300 DPI, laser-printer-friendly.
One diagram per image -- no cramming.
"""

from __future__ import annotations

import logging

from _pubsub_qos import (
    draw_qos_at_least_once,
    draw_qos_at_most_once,
    draw_qos_exactly_once,
)
from _pubsub_topic_content import (
    draw_sub_content,
    draw_sub_topic,
)
from _pubsub_type_hierarchical import (
    draw_sub_hierarchical,
    draw_sub_type,
)

logger = logging.getLogger(__name__)

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logger.info("Generating Pub/Sub diagrams" " (7 separate images)...")
    draw_sub_topic()
    draw_sub_content()
    draw_sub_type()
    draw_sub_hierarchical()
    draw_qos_at_most_once()
    draw_qos_at_least_once()
    draw_qos_exactly_once()
    logger.info("Done!")
