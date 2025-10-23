"""
Debug test for solve_gf2 function.
"""
from common.fountain.matrix import solve_gf2

def test_debug_solve_gf2():
    """Debug the failing full rank case."""
    A = [[1, 1, 0], [1, 0, 1], [0, 1, 1]]
    b = [1, 1, 0]
    
    print("Original matrix A:", A)
    print("Original RHS b:", b)
    
    # Manual step through
    n = len(A)
    A_copy = [row[:] for row in A]
    b_copy = b[:]
    row = 0
    
    for col in range(len(A_copy[0])):
        print(f"\nProcessing column {col}, current row {row}")
        print("Current A:", A_copy)
        print("Current b:", b_copy)
        
        # Find pivot
        pivot = None
        for r in range(row, n):
            if A_copy[r][col] == 1:
                pivot = r
                break
        print(f"Pivot found at row {pivot}")
        
        if pivot is None:
            print("No pivot, continuing")
            continue
            
        # Swap rows
        if pivot != row:
            A_copy[row], A_copy[pivot] = A_copy[pivot], A_copy[row]
            b_copy[row], b_copy[pivot] = b_copy[pivot], b_copy[row]
            print(f"Swapped rows {row} and {pivot}")
            print("After swap A:", A_copy)
            print("After swap b:", b_copy)
        
        # Eliminate
        for r in range(row + 1, n):
            if A_copy[r][col] == 1:
                print(f"Eliminating row {r}")
                for c in range(col, len(A_copy[0])):
                    A_copy[r][c] ^= A_copy[row][c]
                b_copy[r] ^= b_copy[row]
                print(f"After eliminating row {r}: A={A_copy}, b={b_copy}")
        
        row += 1
    
    print(f"\nFinal row count: {row}, matrix columns: {len(A_copy[0])}")
    print("Final A:", A_copy)
    print("Final b:", b_copy)
    
    result = solve_gf2(A, b)
    print("solve_gf2 result:", result)

if __name__ == "__main__":
    test_debug_solve_gf2()
