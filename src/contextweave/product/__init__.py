"""Product desk: C1 amplification via canonical chunk order (live path)."""

from contextweave.product.frequency import FrequencyPrior
from contextweave.product.live_order import (
    DocumentChunk,
    apply_chat_documents,
    reorder_documents,
    resolve_mode,
)

__all__ = [
    "DocumentChunk",
    "FrequencyPrior",
    "apply_chat_documents",
    "reorder_documents",
    "resolve_mode",
]
