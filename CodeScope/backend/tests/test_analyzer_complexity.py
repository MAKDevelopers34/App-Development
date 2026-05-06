import unittest

from app.analyzer import CodeAnalyzer


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

    def test_regular_nested_loops_stay_quadratic(self):
        code = """def example(n):
    for i in range(n):
        for j in range(n):
            print(i, j)
"""

        result = self.analyzer.detect_time_complexity(code, "python")

        self.assertEqual(result["complexity"], "O(n²)")


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
