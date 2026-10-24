"""Owner-operated RAG demo: lexical retrieve → cw-serve-order → vLLM."""

from contextweave.product.rag_demo.chunk import Chunk, chunk_corpus, make_document_id
from contextweave.product.rag_demo.client import AskResult, ask, build_ask_body
from contextweave.product.rag_demo.index import LexicalIndex, build_index, load_index, save_index
from contextweave.product.rag_demo.retrieve import retrieve

__all__ = [
    "AskResult",
    "Chunk",
    "LexicalIndex",
    "ask",
    "build_ask_body",
    "build_index",
    "chunk_corpus",
    "load_index",
    "make_document_id",
    "retrieve",
    "save_index",
]
