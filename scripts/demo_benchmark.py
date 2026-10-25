import os
import random
import sys


def load_simulation():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sim_path = os.path.join(repo_root, "web", "public", "python")
    # simulation.py imports `common`; the repo root copy must win over any
    # generated web/public/python/common left behind by a web build.
    for path in (sim_path, repo_root):
        if path not in sys.path:
            sys.path.insert(0, path)
    import simulation as sim  # type: ignore

    return sim


def run_benchmark(
    sim,
    payload: bytes,
    loss_rate: float,
    seed: int = 1337,
    max_loops: int = 5,
):
    """
    Replay the looping broadcast (sync + metadata + symbol frames) at a fixed
    cadence, dropping each frame with probability ``loss_rate``.
    """
    rng = random.Random(seed)
    package = sim._prepare_package(payload, seed=seed)
    metadata = package["metadata"]
    frame_interval = metadata["frame_interval_ms"] / 1000
    session = sim.ReceiverSession.from_metadata(metadata)

    simulated_time = 0.0
    status = None
    for _ in range(max_loops):
        for frame in package["frames"]:
            simulated_time += frame_interval
            if frame["type"] != "symbol" or rng.random() < loss_rate:
                continue
            status = session.add_frame(frame["qr_value"])
            if status.get("decode_complete"):
                break
        if status and status.get("decode_complete"):
            break

    if status is None:
        status = session._status_dict(redundant=False, newly_added=False)
    complete = bool(status.get("decode_complete"))
    if complete:
        assert session.recovered_text.encode("utf-8") == payload
    return {
        "raw_len": len(payload),
        "wire_len": metadata["orig_len"],
        "k": metadata["k"],
        "loss_rate": loss_rate,
        "simulated_time_s": round(simulated_time, 1),
        "frames_per_k": round(simulated_time / frame_interval / metadata["k"], 2),
        "complete": complete,
        "decode_ms": status.get("decode_ms"),
    }


def main():
    sim = load_simulation()
    from common.shared.demo_payloads import generate_bulk_pos_logs

    for size_kb in (10, 100, 500):
        payload = generate_bulk_pos_logs(size_kb * 1024)
        for loss in (0.0, 0.15, 0.30):
            r = run_benchmark(sim, payload, loss)
            print(
                f"raw={r['raw_len'] // 1024}KB wire={r['wire_len']}B k={r['k']} "
                f"loss={r['loss_rate']:.0%} time={r['simulated_time_s']}s "
                f"frames/k={r['frames_per_k']} complete={r['complete']} "
                f"decode={r['decode_ms']}ms"
            )


if __name__ == "__main__":
    main()
