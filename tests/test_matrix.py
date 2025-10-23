"""
Tests for matrix operations, specifically solve_gf2 function.
"""
import pytest
from common.fountain.matrix import solve_gf2


def test_solve_gf2_identity_matrix():
    """Test solving with identity matrix."""
    A = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    b = [1, 0, 1]
    result = solve_gf2(A, b)
    assert result == [1, 0, 1]


def test_solve_gf2_simple_system():
    """Test solving a simple 2x2 system."""
    A = [[1, 1], [0, 1]]
    b = [1, 1]
    result = solve_gf2(A, b)
    assert result == [0, 1]  # x + y = 1, y = 1 => x = 0


def test_solve_gf2_underdetermined():
    """Test that underdetermined systems return None."""
    A = [[1, 0, 1], [0, 1, 1]]  # 2 equations, 3 unknowns
    b = [1, 0]
    result = solve_gf2(A, b)
    assert result is None


def test_solve_gf2_full_rank():
    """Test a full rank system."""
    A = [[1, 0, 0], [0, 1, 0], [1, 1, 1]]  # This is actually full rank
    b = [1, 1, 0]
    result = solve_gf2(A, b)
    # Verify solution by checking A * result = b (mod 2)
    assert result is not None
    for i in range(len(A)):
        assert sum(A[i][j] * result[j] for j in range(len(result))) % 2 == b[i]


def test_solve_gf2_zero_rhs():
    """Test system with zero right-hand side."""
    A = [[1, 1], [1, 0]]
    b = [0, 0]
    result = solve_gf2(A, b)
    assert result == [0, 0]


def test_solve_gf2_single_equation():
    """Test single equation system."""
    A = [[1, 1, 1]]
    b = [1]
    result = solve_gf2(A, b)
    assert result is None  # Underdetermined
