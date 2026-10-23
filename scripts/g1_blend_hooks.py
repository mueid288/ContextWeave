"""Shared CacheBlend client hooks for matched + in-process G1 benches.

G1-DIAG #1 (2026-10-23) showed MP ``LMCacheMPConnector`` + ``ENABLE_BLENDING``
without ``VLLMModelTracker.register_model`` → Gate R got=0 (reorder ≡ cold).

Stock vLLM never calls ``register_model`` (LMCache #4131). CacheBlend's
in-worker ``LMCBlender`` then cannot load the model for RoPE / layer-1 filter.
Fix: disable V1 worker multiprocessing, patch ``GPUModelRunner.load_model``,
and use in-process ``LMCacheConnectorV1`` for the blend arm.
"""

from __future__ import annotations

import importlib
import os
import sys
import types

BLEND_KV_CONNECTOR = "LMCacheConnectorV1"


def ensure_vllm_attention_compat() -> bool:
    """Alias ``vllm.attention.Attention`` for lmcache ≤0.4.2 on vLLM ≥0.17.

    lmcache 0.4.2 does ``from vllm.attention import Attention``. vLLM 0.18 moved
    the class to ``vllm.model_executor.layers.attention.attention`` (lmcache
    ≥0.5.0 already try/excepts this). Without the alias, in-process blend dies
    at ``Creating blender`` with ``ModuleNotFoundError: vllm.attention``.
    """
    try:
        importlib.import_module("vllm.attention")
        return True
    except ModuleNotFoundError:
        pass

    new_paths = (
        "vllm.model_executor.layers.attention.attention",
        "vllm.attention.layer",
    )
    Attention = None
    for path in new_paths:
        try:
            mod = importlib.import_module(path)
            Attention = getattr(mod, "Attention", None)
            if Attention is not None:
                break
        except Exception:
            continue
    if Attention is None:
        print(
            "WARN: vllm.attention shim failed — Attention class not found",
            flush=True,
        )
        return False

    alias = types.ModuleType("vllm.attention")
    alias.Attention = Attention
    sys.modules["vllm.attention"] = alias
    try:
        import vllm

        vllm.attention = alias  # type: ignore[attr-defined]
    except Exception:
        pass
    print(
        "shimmed vllm.attention.Attention → "
        f"{Attention.__module__}.{Attention.__qualname__}",
        flush=True,
    )
    return True


def setup_blend_env(*, blend_special_str: str, cpu_gb: float | None = None) -> None:
    """LMCache CacheBlend env (chunk size, layerwise, recompute ratio)."""
    os.environ.setdefault("LMCACHE_CHUNK_SIZE", "256")
    os.environ["LMCACHE_ENABLE_BLENDING"] = "True"
    os.environ["LMCACHE_BLEND_SPECIAL_STR"] = blend_special_str
    os.environ.setdefault("LMCACHE_USE_LAYERWISE", "True")
    os.environ.setdefault("LMCACHE_BLEND_CHECK_LAYERS", "1")
    os.environ.setdefault("LMCACHE_BLEND_RECOMPUTE_RATIOS", "0.15")
    if cpu_gb is not None:
        os.environ["LMCACHE_LOCAL_CPU"] = "True"
        os.environ["LMCACHE_MAX_LOCAL_CPU_SIZE"] = str(cpu_gb)
    else:
        os.environ.setdefault("LMCACHE_LOCAL_CPU", "True")
        os.environ.setdefault("LMCACHE_MAX_LOCAL_CPU_SIZE", "40")


def patch_vllm_register_model_for_blend() -> None:
    """Hook ``GPUModelRunner.load_model`` → ``VLLMModelTracker.register_model``.

    Must run in the same process as the worker (see ``prepare_blend_worker``).
    """
    from lmcache.integration.vllm.utils import ENGINE_NAME
    from lmcache.v1.compute.models.utils import VLLMModelTracker

    for mod_name in (
        "vllm.v1.worker.gpu_model_runner",
        "vllm.v1.worker.gpu.model_runner",
    ):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        cls = getattr(mod, "GPUModelRunner", None)
        if cls is None:
            continue
        orig = cls.load_model
        if getattr(orig, "_cw_blend_patched", False):
            continue

        def load_model(self, *args, _orig=orig, **kwargs):  # noqa: ANN001
            out = _orig(self, *args, **kwargs)
            model_obj = getattr(self, "model", None)
            if model_obj is not None:
                VLLMModelTracker.register_model(ENGINE_NAME, model_obj)
            return out

        load_model._cw_blend_patched = True  # type: ignore[attr-defined]
        cls.load_model = load_model  # type: ignore[method-assign]
        print(f"patched {mod_name}.GPUModelRunner.load_model for CacheBlend", flush=True)


def ensure_flashinfer_sparse_compat() -> bool:
    """Satisfy lmcache 0.4.2's eager ``flash_infer_sparse`` import.

    ``attention/utils.py`` imports ``LMCFlashInferSparseBackend`` even when
    ``enable_sparse=False``. That module needs
    ``flashinfer.page.block_sparse_indices_to_vector_sparse_offsets``, which
    newer/older flashinfer wheels may lack. Stub the symbol so non-sparse
    FlashAttention CacheBlend can load; calling the stub raises if sparse is
    actually enabled.
    """
    name = "block_sparse_indices_to_vector_sparse_offsets"
    try:
        import flashinfer.page as page
    except ImportError:
        print("WARN: flashinfer not installed — sparse shim skipped", flush=True)
        return False
    if hasattr(page, name):
        return True

    def _missing(*_args, **_kwargs):  # noqa: ANN001
        raise RuntimeError(
            f"flashinfer.page.{name} is not in this wheel; "
            "keep LMCACHE sparse/enable_sparse off for CacheBlend"
        )

    setattr(page, name, _missing)
    print(f"shimmed flashinfer.page.{name} (sparse unused)", flush=True)
    return True


def prepare_blend_worker(*, blend_special_str: str, cpu_gb: float | None = None) -> None:
    """Env + register_model patch so in-worker LMCBlender can engage."""
    # In-process worker so the monkeypatch is visible (not a forked child).
    os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"
    setup_blend_env(blend_special_str=blend_special_str, cpu_gb=cpu_gb)
    ensure_vllm_attention_compat()
    ensure_flashinfer_sparse_compat()
    try:
        patch_vllm_register_model_for_blend()
    except Exception as exc:  # noqa: BLE001 — lmcache may be absent on CPU CI
        print(f"WARN: register_model patch skipped ({exc})", flush=True)


def blend_kv_transfer_config():
    """In-process LMCache connector (official CacheBlend path)."""
    from vllm.config import KVTransferConfig

    return KVTransferConfig(
        kv_connector=BLEND_KV_CONNECTOR,
        kv_role="kv_both",
    )
