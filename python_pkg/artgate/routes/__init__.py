"""Generation routes for the art bake-off.

Importing this package registers every vector subject, so ``all_shapes()``
never depends on the caller having imported the right module first. That
import-order hazard is exactly the kind of silent partial result the gates
exist to prevent -- a half-registered route would score a real-looking but
wrong number in the decision table.
"""

from __future__ import annotations

from python_pkg.artgate.routes import vector_shapes as _vector_shapes

__all__ = ["_vector_shapes"]
