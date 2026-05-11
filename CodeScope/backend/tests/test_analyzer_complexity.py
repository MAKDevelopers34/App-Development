import unittest

from app.analyzer import CodeAnalyzer
from app.ai_explainer import _merge_ai_function_explanations


class AnalyzerComplexityTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = CodeAnalyzer()

    def test_input_schema_is_inferred_from_pasted_python_function(self):
        code = """def tricky(n):
    return n
"""

        schema = self.analyzer.infer_input_schema(code, "python")

        self.assertTrue(schema["available"])
        self.assertEqual(schema["function"], "tricky")
        self.assertEqual(schema["parameters"][0]["name"], "n")
        self.assertEqual(schema["parameters"][0]["kind"], "integer")

    def test_input_schema_is_included_in_analysis_result(self):
        code = """def two_sum(nums, target):
    return target in nums
"""

        result = self.analyzer.analyze(code, "sample.py", {"nums": [1, 2, 3], "target": 2})

        self.assertIn("input_schema", result)
        self.assertEqual(result["input_schema"]["function"], "two_sum")
        self.assertEqual(result["provided_inputs"]["target"], 2)

    def test_geometric_prefix_sum_is_linear(self):
        code = """def example2(n):
    i = 1
    while i < n:
        for j in range(i):
            print(j)
        i *= 2
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n)")

    def test_independent_inner_loop_inside_log_loop_is_n_log_n(self):
        code = """def example(n):
    i = 1
    while i < n:
        for j in range(n):
            print(j)
        i *= 2
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n log n)")

    def test_geometric_shrinking_work_is_linear(self):
        code = """def shrinking_work(n):
    total = 0
    while n > 1:
        for i in range(n):
            total += i
        n //= 2
    return total
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n)")

    def test_shifted_log_inner_loop_sums_to_linear(self):
        code = """def tricky(n):
    count = 0
    i = 1
    while i < n:
        j = i
        while j < n:
            j *= 2
            count += 1
        i += 1
    return count
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n)")

    def test_break_limited_log_loop_inside_quadratic_loops_is_n2_log_n(self):
        code = """def complex(n):
    count = 0
    for i in range(n):
        for j in range(n):
            k = 1
            while k < n:
                k *= 2
                if k > j:
                    break
                count += 1
    return count
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n² log n)")

    def test_subset_generation_counts_output_copy_cost(self):
        code = """def subsets(arr, index=0):
    if index == len(arr):
        return [[]]

    small = subsets(arr, index+1)
    result = []

    for s in small:
        result.append(s)
        result.append([arr[index]] + s)

    return result
"""

        time = self.analyzer.detect_time_complexity(code, "python")
        space = self.analyzer.detect_space_complexity(code, "python")

        self.assertEqual(time["complexity"], "O(n * 2^n)")
        self.assertEqual(space, "O(n * 2^n)")

    def test_harmonic_increment_while_loop_is_n_log_n(self):
        code = """def harmonic(n):
    count = 0
    for i in range(1, n+1):
        j = 1
        while j <= n:
            j += i
            count += 1
    return count
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n log n)")

    def test_nested_log_triangular_loop_is_log_cubed(self):
        code = """def tricky_loop(n):
    count = 0
    i = 1
    while i < n:
        j = 1
        while j < n:
            k = j
            while k > 0:
                k //= 2
                count += 1
            j *= 2
        i *= 2
    return count
"""

        result = self.analyzer.analyze(code, "tricky_loop.py", {"n": 1024})

        self.assertEqual(result["time_complexity"], "O(log³ n)")
        self.assertEqual(result["space_complexity"], "O(1)")
        self.assertEqual(result["input_effect_analysis"]["estimated_time_units"], "1,000")

    def test_regular_nested_loops_stay_quadratic(self):
        code = """def example(n):
    for i in range(n):
        for j in range(n):
            print(i, j)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n²)")

    def test_dynamic_array_doubling_is_linear_total_with_amortized_append(self):
        code = """def dynamic_array_ops(n):
    arr = []
    size = 1
    capacity = 1

    for i in range(n):
        if size == capacity:
            new_arr = [0] * (2 * capacity)
            for j in range(capacity):
                new_arr[j] = arr[j] if j < len(arr) else 0
            arr = new_arr
            capacity *= 2
        arr.append(i)
        size += 1
    return arr
"""

        result = self.analyzer.analyze(code, "dynamic.py", {"n": 1024})

        self.assertEqual(result["time_complexity"], "O(n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("amortized_analysis", result)
        self.assertEqual(result["amortized_analysis"]["amortized_per_operation"], "O(1)")
        self.assertFalse(result["issues"])

    def test_generic_quadratic_optimization_is_problem_dependent_not_hashmap(self):
        code = """def matrix_scan(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i * j
    return total
"""

        result = self.analyzer.analyze(code, "matrix.py")

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertTrue(result["optimizations"])
        self.assertNotIn("Hash Map", result["optimizations"][0]["title"])
        self.assertEqual(result["optimizations"][0]["complexity_after"], "problem-dependent")

    def test_pair_search_quadratic_optimization_can_suggest_hashmap(self):
        code = """def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""

        result = self.analyzer.analyze(code, "two_sum.py")

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertTrue(result["optimizations"])
        self.assertIn("Hash Map", result["optimizations"][0]["title"])

    def test_matrix_power_reports_professional_per_function_breakdown(self):
        code = """def multiply(A, B):
    n = len(A)
    result = [[0]*n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += A[i][k] * B[k][j]
    return result

def power(matrix, n):
    if n == 1:
        return matrix
    if n % 2 == 0:
        half = power(matrix, n // 2)
        return multiply(half, half)
    else:
        return multiply(matrix, power(matrix, n - 1))
"""

        result = self.analyzer.analyze(code, "matrix_power.py")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(k\u00b3 log n)")
        self.assertEqual(result["space_complexity"], "O(k\u00b2)")
        self.assertEqual(self.analyzer.last_func_own_complexities["power"], "O(log n)")
        self.assertEqual(self.analyzer.last_func_complexities["power"], "O(k\u00b3 log n)")
        self.assertEqual(details["power"]["own_complexity"], "O(log n)")
        self.assertEqual(details["power"]["effective_complexity"], "O(k\u00b3 log n)")
        self.assertIn("Binary matrix exponentiation", details["power"]["reason"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertIn("Naive matrix multiplication core", result["issues"][0]["message"])

    def test_ai_function_text_cannot_override_analyzer_complexity_facts(self):
        details = [
            {
                "function": "power",
                "own_complexity": "O(log n)",
                "effective_complexity": "O(k\u00b3 log n)",
                "complexity": "O(k\u00b3 log n)",
                "reason": "Binary matrix exponentiation",
                "calls": [{"function": "multiply", "multiplier": "O(1)", "complexity": "O(k\u00b3)"}],
            }
        ]
        ai_items = [
            {
                "function": "power",
                "own_complexity": "O(1)",
                "effective_complexity": "O(n)",
                "complexity": "O(n)",
                "calls": [],
                "explanation": "AI wording only."
            }
        ]

        merged = _merge_ai_function_explanations(details, ai_items)

        self.assertEqual(merged[0]["own_complexity"], "O(log n)")
        self.assertEqual(merged[0]["effective_complexity"], "O(k\u00b3 log n)")
        self.assertEqual(merged[0]["complexity"], "O(k\u00b3 log n)")
        self.assertEqual(merged[0]["calls"], details[0]["calls"])
        self.assertEqual(merged[0]["explanation"], "AI wording only.")

    def test_strassen_matrix_multiplication_is_detected_without_screen_error(self):
        code = """import numpy as np

def split(matrix):
    row, col = matrix.shape
    r, c = row // 2, col // 2
    return matrix[:r, :c], matrix[:r, c:], matrix[r:, :c], matrix[r:, c:]

def strassen(A, B):
    if len(A) == 1:
        return A * B

    A11, A12, A21, A22 = split(A)
    B11, B12, B21, B22 = split(B)

    M1 = strassen(A11 + A22, B11 + B22)
    M2 = strassen(A21 + A22, B11)
    M3 = strassen(A11, B12 - B22)
    M4 = strassen(A22, B21 - B11)
    M5 = strassen(A11 + A12, B22)
    M6 = strassen(A21 - A11, B11 + B12)
    M7 = strassen(A12 - A22, B21 + B22)

    C11 = M1 + M4 - M5 + M7
    C12 = M3 + M5
    C21 = M2 + M4
    C22 = M1 - M2 + M3 + M6

    return np.vstack((np.hstack((C11, C12)),
                      np.hstack((C21, C22))))
"""

        result = self.analyzer.analyze(
            code,
            "strassen.py",
            {"A": [[1, 2], [3, 4]], "B": [[5, 6], [7, 8]]}
        )

        self.assertEqual(result["time_complexity"], "O(n^2.807)")
        self.assertEqual(result["space_complexity"], "O(n²)")
        self.assertIn("input_effect_analysis", result)
        self.assertEqual(self.analyzer.last_func_complexities["strassen"], "O(n^2.807)")


    def test_inner_square_bound_sums_to_cubic(self):
        code = """def example9(n):
    for i in range(n):
        for j in range(i*i):
            pass
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n³)")

    def test_direct_square_range_is_quadratic(self):
        code = """def example(n):
    for i in range(n*n):
        pass
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n²)")

    def test_exponent_range_is_cubic(self):
        code = """def example(n):
    for i in range(n**3):
        pass
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n³)")

    def test_two_half_recursive_calls_with_constant_body_is_linear(self):
        code = """def example6(n):
    if n <= 1:
        return
    example6(n//2)
    example6(n//2)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n)")

    def test_two_half_recursive_calls_with_linear_body_is_n_log_n(self):
        code = """def example(n):
    if n <= 1:
        return
    for i in range(n):
        print(i)
    example(n//2)
    example(n//2)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n log n)")

    def test_single_half_recursive_call_is_logarithmic(self):
        code = """def example(n):
    if n <= 1:
        return
    example(n//2)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(log n)")

    def test_single_decrement_recursive_call_is_linear(self):
        code = """def example(n):
    if n <= 1:
        return
    example(n - 1)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n)")

    def test_uneven_divide_recursion_uses_akra_bazzi(self):
        code = """def weird_recursion(n):
    if n <= 1:
        return 1
    return weird_recursion(n // 2) + weird_recursion(n // 3) + n
"""

        result = self.analyzer.analyze(code, "weird.py", {"n": 1024})

        self.assertEqual(result["time_complexity"], "O(n^0.788)")
        self.assertEqual(result["space_complexity"], "O(log n)")
        self.assertIn("Akra-Bazzi", result["time_complexity_reason"])

    def test_balanced_mid_partition_recursion_is_linear_not_exponential(self):
        code = """def tricky_bs(arr, l, r):
    if l > r:
        return 0

    mid = (l + r) // 2

    return tricky_bs(arr, l, mid-1) + tricky_bs(arr, mid+1, r)
"""

        time = self.analyzer.detect_time_complexity(code, "python")
        space = self.analyzer.detect_space_complexity(code, "python")

        self.assertEqual(time["complexity"], "O(n)")
        self.assertEqual(space, "O(log n)")

    def test_three_plain_recursive_calls_stay_exponential(self):
        code = """def example(n):
    if n <= 1:
        return
    example(n - 1)
    example(n - 1)
    example(n - 1)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(3^n)")

    def test_catastrophic_javascript_regex_is_exponential(self):
        code = r"""function js_5(str) {
    let count = 0;
    let temp = str;
    const regex = /^(a+)+b$/;
    while (temp.length > 0) {
        regex.test(temp);
        count++;
        temp = temp.slice(1);
    }
    return count;
}"""

        time = self.analyzer.detect_time_complexity(code, "javascript")
        space = self.analyzer.detect_space_complexity(code, "javascript")

        self.assertEqual(time["complexity"], "O(2^n)")
        self.assertEqual(space, "O(n)")

    def test_safe_javascript_regex_inside_loop_is_not_exponential(self):
        code = r"""function js_safe(str) {
    let count = 0;
    let temp = str;
    const regex = /^a+b$/;
    while (temp.length > 0) {
        regex.test(temp);
        count++;
        temp = temp.slice(1);
    }
    return count;
}"""

        result = self.analyzer.detect_time_complexity(code, "javascript")

        self.assertNotEqual(result["complexity"], "O(2^n)")

    def test_recursive_dfs_is_graph_linear_and_concrete_counts_input_graph(self):
        code = """def dfs(graph, node, visited):
    visited.add(node)
    for nei in graph[node]:
        if nei not in visited:
            dfs(graph, nei, visited)
"""

        time = self.analyzer.detect_time_complexity(code, "python")
        space = self.analyzer.detect_space_complexity(code, "python")
        result = self.analyzer.analyze(
            code,
            "graph.py",
            {
                "graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []},
                "node": "A",
                "visited": []
            }
        )
        concrete = result["concrete_analysis"]

        self.assertEqual(time["complexity"], "O(V + E)")
        self.assertEqual(result["time_complexity"], "O(V + E)")
        self.assertEqual(space, "O(V)")
        self.assertEqual(concrete["kind"], "dfs_exact")
        self.assertEqual(concrete["calls"], 4)
        self.assertEqual(concrete["edge_scans"], 4)
        self.assertEqual(concrete["symbolic_time_complexity"], "O(V + E)")

    def test_repeated_dfs_with_fresh_visited_repeats_graph_work(self):
        code = """def dfs(graph, node, visited):
    if node in visited:
        return
    visited.add(node)
    for neighbor in graph[node]:
        dfs(graph, neighbor, visited)

def run_all_nodes(graph):
    for node in graph:
        dfs(graph, node, set())
"""

        result = self.analyzer.analyze(code, "graph.py")

        self.assertEqual(result["time_complexity"], "O(V * (V + E))")
        self.assertEqual(result["space_complexity"], "O(V)")
        self.assertIn("fresh visited set", result["time_complexity_reason"])
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(V + E)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_javascript_generator_mixed_recurrence_is_exponential(self):
        code = r"""function* js_4_gen(n) {
    if (n <= 1) yield 1;
    else {
        yield* js_4_gen(n - 1);
        yield* js_4_gen(Math.floor(n / 2));
    }
}

function js_4(n) {
    return [...js_4_gen(n)].reduce((a, b) => a + b, 0);
}"""

        time = self.analyzer.detect_time_complexity(code, "javascript")
        space = self.analyzer.detect_space_complexity(code, "javascript")
        functions = self.analyzer._extract_all_function_complexities(code, "javascript")

        self.assertEqual(functions["js_4_gen"], "O(2^n)")
        self.assertEqual(functions["js_4"], "O(2^n)")
        self.assertEqual(time["complexity"], "O(2^n)")
        self.assertEqual(space, "O(2^n)")

    def test_java_mutual_recursion_with_sqrt_shrink_is_log_log(self):
        code = r"""public class Mutual {
    static int ping(int n) {
        if (n <= 0) return 0;
        return 1 + pong(n - 1);
    }

    static int pong(int n) {
        if (n <= 0) return 0;
        return 1 + ping((int)Math.floor(Math.sqrt(n)));
    }
}"""

        time = self.analyzer.detect_time_complexity(code, "java")
        space = self.analyzer.detect_space_complexity(code, "java")

        self.assertEqual(time["complexity"], "O(log log n)")
        self.assertEqual(space, "O(log log n)")

    def test_java_branching_substring_recursion_counts_copy_cost(self):
        code = r"""public int java_1(String s) {
    if (s.length() <= 1) return 1;

    int left = java_1(s.substring(0, s.length() - 1));
    int right = java_1(s.substring(1, s.length()));

    return left + right + s.length();
}"""

        time = self.analyzer.detect_time_complexity(code, "java")
        space = self.analyzer.detect_space_complexity(code, "java")

        self.assertEqual(time["complexity"], "O(n * 2^n)")
        self.assertEqual(space, "O(n²)")

    def test_cpp_lowbit_update_loop_is_logarithmic_per_outer_item(self):
        code = r"""int cpp_5(int n) {
    int res = 0;
    for (int i = 1; i <= n; i++) {
        int temp = i;
        while (temp <= n) {
            res++;
            temp += (temp & -temp);
        }
    }
    return res;
}"""

        time = self.analyzer.detect_time_complexity(code, "cpp")
        space = self.analyzer.detect_space_complexity(code, "cpp")

        self.assertEqual(time["complexity"], "O(n log n)")
        self.assertEqual(space, "O(1)")

    def test_bit_clear_loop_is_logarithmic_and_exact_for_input(self):
        code = """def bit_fun(n):
    count = 0
    while n > 0:
        n = n & (n - 1)
        count += 1
    return count
"""

        time = self.analyzer.detect_time_complexity(code, "python")
        space = self.analyzer.detect_space_complexity(code, "python")
        result = self.analyzer.analyze(code, "bits.py", {"n": 15})
        concrete = result["concrete_analysis"]

        self.assertEqual(time["complexity"], "O(log n)")
        self.assertEqual(space, "O(1)")
        self.assertEqual(concrete["kind"], "bit_clear_exact")
        self.assertEqual(concrete["return_value"], 4)
        self.assertEqual(concrete["time"], "4 loop iterations")
        self.assertEqual(concrete["symbolic_time_complexity"], "O(popcount(n)), worst-case O(log n)")

    def test_cpp_ackermann_recursion_is_detected(self):
        code = r"""int cpp_4(int m, int n) {
    if (m == 0) return n + 1;
    if (m > 0 && n == 0) return cpp_4(m - 1, 1);
    return cpp_4(m - 1, cpp_4(m, n - 1));
}"""

        time = self.analyzer.detect_time_complexity(code, "cpp")
        space = self.analyzer.detect_space_complexity(code, "cpp")

        self.assertEqual(time["complexity"], "O(A(m, n))")
        self.assertEqual(space, "O(A(m, n))")

    def test_ackermann_concrete_inputs_report_exact_cost(self):
        code = r"""int cpp_4(int m, int n) {
    if (m == 0) return n + 1;
    if (m > 0 && n == 0) return cpp_4(m - 1, 1);
    return cpp_4(m - 1, cpp_4(m, n - 1));
}"""

        result = self.analyzer.analyze(code, "sample.cpp", "m=2, n=2")
        concrete = result["concrete_analysis"]

        self.assertTrue(concrete["available"])
        self.assertEqual(concrete["return_value"], 7)
        self.assertEqual(concrete["calls"], 27)
        self.assertEqual(concrete["max_stack_depth"], 8)
        self.assertEqual(concrete["fixed_input_time_complexity"], "O(1)")
        self.assertEqual(concrete["fixed_input_space_complexity"], "O(1)")
        self.assertEqual(result["time_complexity"], "O(A(m, n))")


if __name__ == "__main__":
    unittest.main()
