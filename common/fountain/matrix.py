# File: common/fountain/matrix.py

def solve_gf2(matrix: list[list[int]], rhs: list[int]) -> list[int] | None:
    """Simple Gaussian elimination over GF(2)."""
    n = len(matrix)
    m = len(matrix[0])
    A = [row[:] for row in matrix]
    b = rhs[:]
    
    row = 0
    for col in range(m):
        pivot = None
        for r in range(row, n):
            if A[r][col] == 1:
                pivot = r
                break
        if pivot is None:
            continue
            
        A[row], A[pivot] = A[pivot], A[row]
        b[row], b[pivot] = b[pivot], b[row]
        
        for r in range(row + 1, n):
            if A[r][col] == 1:
                for c in range(col, m):
                    A[r][c] ^= A[row][c]
                b[r] ^= b[row]
        row += 1

    # Check for inconsistency (row with all zeros but non-zero RHS)
    for i in range(row, n):
        if b[i] == 1:
            return None  # Inconsistent system
    
    # If we have fewer pivot rows than columns, system is underdetermined
    if row < m:
        return None

    # Back-substitution
    x = [0] * m
    for i in reversed(range(row)):
        leading = next((c for c in range(m) if A[i][c] == 1), None)
        if leading is None:
            continue
        x[leading] = b[i]
        for j in range(leading + 1, m):
            x[leading] ^= A[i][j] & x[j]
    return x
