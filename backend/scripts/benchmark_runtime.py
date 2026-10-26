"""
FinGuard AI — Model Artifact, Startup Time & Inference Performance Benchmark
Audits model sizes, loading latency, memory consumption, and inference speeds.
"""
import os
import sys
import time
import tracemalloc
from pathlib import Path
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.registry import registry_service
from app.services.engine import inference_engine


def run_benchmark():
    print("=" * 70)
    print(" FinGuard AI: AWS Readiness Benchmark & Model Feasibility Audit")
    print("=" * 70)
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
    print(f"Models Base Directory: {settings.resolved_models_dir}")
    print("-" * 70)

    tracemalloc.start()
    baseline_mem = tracemalloc.get_traced_memory()[0]

    all_models = registry_service.list_models()
    serving_models = [
        m for m in all_models
        if m.is_available and m.model_family in ["XGBoost", "MLP", "Autoencoder"]
    ]
    unsupported = [m for m in all_models if m not in serving_models]
    print(f"Audited {len(all_models)} model registrations:")
    print(f"  • {len(serving_models)} Verified Production-Serving Models (XGBoost, MLP, Autoencoder)")
    print(f"  • {len(unsupported)} Experimental/Unsupported Models (e.g. LSTM sequential)")
    print("-" * 70)

    results = []

    for model_meta in serving_models:
        model_id = model_meta.model_id
        dataset_dir = settings.resolved_models_dir / model_meta.dataset_id
        model_path = dataset_dir / model_meta.model_artifact_filename
        scaler_path = dataset_dir / model_meta.scaler_artifact_filename if model_meta.scaler_artifact_filename else None

        model_size_kb = os.path.getsize(model_path) / 1024 if model_path.exists() else 0
        scaler_size_kb = os.path.getsize(scaler_path) / 1024 if scaler_path and scaler_path.exists() else 0
        total_size_kb = model_size_kb + scaler_size_kb

        # Measure load time
        t0 = time.perf_counter()
        loaded_model = inference_engine.load_model(model_meta)
        loaded_scaler = inference_engine.load_scaler(model_meta)
        load_time_ms = (time.perf_counter() - t0) * 1000

        # Create dummy input vector with exact feature dimension
        dim = len(model_meta.ordered_model_features)
        dummy_single = np.ones((1, dim), dtype=np.float32)
        dummy_batch_1000 = np.ones((1000, dim), dtype=np.float32)

        # Warm up
        inference_engine.predict(model_meta, dummy_single)

        # Measure single inference latency over 50 iterations
        single_times = []
        for _ in range(50):
            t_start = time.perf_counter()
            inference_engine.predict(model_meta, dummy_single)
            single_times.append((time.perf_counter() - t_start) * 1000)

        p50 = np.percentile(single_times, 50)
        p95 = np.percentile(single_times, 95)
        avg = np.mean(single_times)

        # Measure 1000-row batch inference latency
        t_batch_start = time.perf_counter()
        inference_engine.predict(model_meta, dummy_batch_1000)
        batch_time_ms = (time.perf_counter() - t_batch_start) * 1000

        curr_mem = tracemalloc.get_traced_memory()[0]
        mem_increase_mb = (curr_mem - baseline_mem) / (1024 * 1024)

        results.append({
            "model_id": model_id,
            "family": model_meta.model_family,
            "dataset": model_meta.dataset_id,
            "total_size_kb": total_size_kb,
            "load_time_ms": load_time_ms,
            "single_p50_ms": p50,
            "single_p95_ms": p95,
            "batch_1000_ms": batch_time_ms,
            "mem_mb": mem_increase_mb
        })

        print(f"[{model_id}] {model_meta.model_family.upper()} ({model_meta.dataset_id})")
        print(f"  Artifact Size: {total_size_kb:.1f} KB | Load Time: {load_time_ms:.1f} ms")
        print(f"  Single Latency: p50={p50:.2f}ms, p95={p95:.2f}ms | 1K Batch: {batch_time_ms:.1f} ms")
        print()

    total_size_mb = sum(r["total_size_kb"] for r in results) / 1024
    total_mem_peak_mb = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    tracemalloc.stop()

    print("=" * 70)
    print(" SUMMARY METRICS")
    print("=" * 70)
    print(f"Combined Models Size: {total_size_mb:.2f} MB")
    print(f"Peak Traced Memory:   {total_mem_peak_mb:.2f} MB")
    avg_single = np.mean([r["single_p50_ms"] for r in results])
    print(f"Average Single Inference Latency (p50): {avg_single:.2f} ms")
    avg_batch = np.mean([r["batch_1000_ms"] for r in results])
    print(f"Average 1000-Row Batch Latency:         {avg_batch:.2f} ms")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
