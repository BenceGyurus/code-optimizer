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
    
    for i in range(rows_a):
        for j in range(cols_b):
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
        # Assuming matrix_a, matrix_b, and result are NumPy arrays.
        # If they are standard Python lists of lists, they should be converted first:
        # matrix_a = np.asarray(matrix_a_list)
        # matrix_b = np.asarray(matrix_b_list)
        # result = np.zeros((matrix_a.shape[0], matrix_b.shape[1])) # Or np.asarray(result_list) if pre-existing

        # This line replaces the two nested loops for a given 'i'
        result[i, :] = np.dot(matrix_a[i, :], matrix_b)
    # matrix_a_np = np.array(matrix_a)
    # matrix_b_np = np.array(matrix_b)
    # result = matrix_a_np @ matrix_b_np

    result = matrix_a @ matrix_b
    # Alternatively: result = np.dot(matrix_a, matrix_b)

if __name__ == "__main__":
    data = [5, 12, 8, 20]
    print(f"Processed: {process_data(data)}")
