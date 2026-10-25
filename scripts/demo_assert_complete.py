import os
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


def main():
    sim = load_simulation()
    from common.shared.demo_payloads import generate_bulk_pos_logs

    payload = generate_bulk_pos_logs(10 * 1024)
    package = sim._prepare_package(payload, seed=1337)
    session = sim.ReceiverSession.from_metadata(package["metadata"])

    for frame in package["frames"]:
        if frame["type"] != "symbol":
            continue
        status = session.add_frame(frame["qr_value"])
        if status.get("decode_complete"):
            if status["recovered_text"].encode("utf-8") != payload:
                print("FAIL: recovered payload differs from original")
                return 1
            print("OK: reconstruction completed")
            return 0

    print("FAIL: reconstruction did not complete")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
