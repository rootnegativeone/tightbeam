from common.fountain.schedule import repair_degree, symbol_indices


def test_systematic_symbols_map_to_their_own_block():
    assert [symbol_indices(42, esi, 10) for esi in range(10)] == [
        [i] for i in range(10)
    ]


def test_repair_degree_grows_with_log_k_and_caps_near_half():
    assert [repair_degree(k) for k in (1, 2, 3, 8, 50, 107, 500, 2000, 5000)] == [
        1, 2, 2, 4, 25, 32, 40, 48, 56,
    ]  # fmt: skip


def test_schedule_is_pinned():
    # Golden values: encoder and receiver (and any future non-Python encoder)
    # must derive identical index sets. Changing these is a wire-format break.
    assert symbol_indices(0xDEADBEEF, 107, 107) == [
        2, 6, 10, 13, 15, 18, 20, 27, 30, 32, 33, 35, 38, 41, 57, 58,
        59, 62, 68, 72, 75, 80, 81, 83, 87, 90, 93, 99, 100, 101, 104,
    ]  # fmt: skip


def test_repair_rows_mix_parities_and_stay_in_range():
    k = 107
    rows = [symbol_indices(7, esi, k) for esi in range(k, k + 200)]
    assert {len(r) % 2 for r in rows} == {0, 1}
    assert all(len(set(r)) == len(r) and 0 <= min(r) and max(r) < k for r in rows)
    assert {len(r) for r in rows} <= {repair_degree(k), repair_degree(k) - 1}
