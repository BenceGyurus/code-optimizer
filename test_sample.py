# Test sample for OptiCode optimization

def process_data(items):
    # This should be caught as a list_comprehension candidate
    result = []
    result = [item * 2 for item in items if item > 10]
    return result

def matrix_multiply_inefficient(matrix_a, matrix_b):
    # This should be caught as unnecessary_nested_loops
    rows_a = len(matrix_a)
    cols_a = len(matrix_a[0])
    cols_b = len(matrix_b[0])
    
    result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]
    
    import numpy as np

    # Assuming matrix_a and matrix_b are converted to NumPy arrays.
    # For example, if they were lists of lists:
    # matrix_a_np = np.array(matrix_a)
    # matrix_b_np = np.array(matrix_b)
    # Then use matrix_a_np and matrix_b_np below.

    result = np.dot(matrix_a, matrix_b)
    # Alternatively, using the @ operator (Python 3.5+):
    # result = matrix_a @ matrix_b
    
    return result

if __name__ == "__main__":
    data = [5, 12, 8, 20]
    print(f"Processed: {process_data(data)}")
