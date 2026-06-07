import unittest
from unittest.mock import patch

from app.analyzer import CodeAnalyzer
from app.ai_explainer import (
    _build_ai_optimization_prompt,
    _build_ai_prompt,
    _expensive_function_targets,
    enhance_optimizations_with_ai,
    get_ai_explanation,
    get_function_level_explanations,
    _merge_ai_function_explanations,
    _merge_ai_optimization_suggestions,
    _validate_ai_rewrite_complexity,
)
from app.github_fetcher import (
    SUPPORTED_EXTENSIONS as GITHUB_SUPPORTED_EXTENSIONS,
    fetch_github_code,
    get_github_folders,
    parse_github_url_details,
)
from app.report_generator import generate_pdf_report
from app.routes import SUPPORTED_CODE_EXTENSIONS, _analyze_with_extras, _build_batch_summary, _should_skip_batch_path


class MockGithubResponse:
    def __init__(self, payload=None, text='', status_code=200):
        self._payload = payload
        self.text = text
        self.content = text.encode('utf-8')
        self.status_code = status_code

    def json(self):
        return self._payload


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

    def test_common_target_language_extensions_are_supported(self):
        cases = {
            "sample.py": "python",
            "sample.pyw": "python",
            "index.js": "javascript",
            "index.mjs": "javascript",
            "index.cjs": "javascript",
            "component.ts": "typescript",
            "component.tsx": "typescript",
            "module.mts": "typescript",
            "module.cts": "typescript",
            "Solution.java": "java",
            "solver.cpp": "cpp",
            "solver.cc": "cpp",
            "solver.cxx": "cpp",
            "solver.hpp": "cpp",
            "legacy.c": "c",
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(self.analyzer.detect_language("", filename), expected)

        for extension in (".cc", ".cxx", ".hpp", ".mjs", ".mts", ".pyw"):
            self.assertIn(extension, SUPPORTED_CODE_EXTENSIONS)
            self.assertIn(extension, GITHUB_SUPPORTED_EXTENSIONS)

    def test_github_tree_url_preserves_selected_folder(self):
        details = parse_github_url_details("https://github.com/acme/widgets/tree/main/backend/app")

        self.assertEqual(details["owner"], "acme")
        self.assertEqual(details["repo"], "widgets")
        self.assertEqual(details["ref"], "main")
        self.assertEqual(details["path"], "backend/app")

    @patch("app.github_fetcher.requests.get")
    def test_github_fetch_uses_selected_folder_and_branch(self, mock_get):
        mock_get.side_effect = [
            MockGithubResponse({
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "README.md", "size": 20},
                    {"type": "blob", "path": "backend/solver.py", "size": 80},
                    {"type": "blob", "path": "frontend/App.jsx", "size": 80},
                ],
            }),
            MockGithubResponse(text="def solve(n):\n    return n\n"),
        ]

        files = fetch_github_code(
            "https://github.com/acme/widgets",
            path="backend",
            ref="main",
        )

        self.assertEqual(files, [{
            "filename": "backend/solver.py",
            "code": "def solve(n):\n    return n\n",
        }])
        first_call = mock_get.call_args_list[0]
        second_call = mock_get.call_args_list[1]
        self.assertIn("/git/trees/main", first_call.args[0])
        self.assertEqual(first_call.kwargs["params"], {"recursive": "1"})
        self.assertIn("/main/backend/solver.py", second_call.args[0])

    @patch("app.github_fetcher.requests.get")
    def test_github_folder_listing_returns_selectable_directories(self, mock_get):
        mock_get.side_effect = [
            MockGithubResponse({"default_branch": "main"}),
            MockGithubResponse({
                "truncated": False,
                "tree": [
                    {"type": "tree", "path": "backend"},
                    {"type": "tree", "path": "backend/app"},
                    {"type": "tree", "path": "node_modules"},
                    {"type": "blob", "path": "frontend/src/App.jsx"},
                    {"type": "blob", "path": "backend/app/routes.py"},
                ],
            }),
        ]

        tree = get_github_folders("https://github.com/acme/widgets")

        self.assertEqual(
            [folder["path"] for folder in tree["folders"]],
            ["", "backend", "backend/app", "frontend", "frontend/src"],
        )
        self.assertEqual(tree["ref"], "main")
        self.assertEqual(tree["limits"]["max_files"], 20)

    def test_input_schema_is_included_in_analysis_result(self):
        code = """def two_sum(nums, target):
    return target in nums
"""

        result = self.analyzer.analyze(code, "sample.py", {"nums": [1, 2, 3], "target": 2})

        self.assertIn("input_schema", result)
        self.assertEqual(result["input_schema"]["function"], "two_sum")
        self.assertEqual(result["provided_inputs"]["target"], 2)
        self.assertIn("semantic_analysis", result)
        self.assertTrue(any(
            item["title"] == "Concrete inputs are examples"
            for item in result["semantic_analysis"]["items"]
        ))

    def test_semantic_analysis_flags_unknown_library_calls(self):
        code = """def run(data):
    return mystery_transform(data)
"""

        result = self.analyzer.analyze(code, "unknown.py")
        semantic = result["semantic_analysis"]

        self.assertEqual(result["time_complexity"], "O(unknown)")
        self.assertEqual(semantic["confidence"], "low")
        self.assertTrue(any(item["category"] == "libraries" and item["severity"] == "high" for item in semantic["items"]))
        self.assertIn("mystery_transform", " ".join(str(item.get("evidence", "")) for item in semantic["items"]))

    def test_semantic_analysis_flags_side_effects_and_input_mutation(self):
        side_effect_code = """function send(items) {
  console.log(items.length);
  return fetch('/api');
}
"""
        mutation_code = """#include <set>
using namespace std;
void multiErase(multiset<int>& s) {
    while (!s.empty()) {
        auto it = s.begin();
        s.erase(it);
    }
}
"""

        side_effect = self.analyzer.analyze(side_effect_code, "send.js")["semantic_analysis"]
        mutation = self.analyzer.analyze(mutation_code, "multiErase.cpp")["semantic_analysis"]

        self.assertTrue(any(item["title"] == "Output side effect" for item in side_effect["items"]))
        self.assertTrue(any(item["title"] == "Network side effect" for item in side_effect["items"]))
        self.assertTrue(any(item["title"] == "Function mutates input state" for item in mutation["items"]))

    def test_semantic_analysis_flags_runtime_models_for_streams_and_ordered_trees(self):
        stream_code = """import java.util.*;
public class Test {
    public static long nested(List<Integer> list) {
        return list.stream().flatMap(x -> list.stream().map(y -> x + y)).count();
    }
}
"""
        tree_code = """#include <set>
using namespace std;
void multiErase(multiset<int>& s) {
    while (!s.empty()) {
        auto it = s.begin();
        s.erase(it);
    }
}
"""

        stream = self.analyzer.analyze(stream_code, "Test.java")["semantic_analysis"]
        tree = self.analyzer.analyze(tree_code, "multiErase.cpp")["semantic_analysis"]

        self.assertTrue(any(item["title"] == "Stream pipeline laziness matters" for item in stream["items"]))
        self.assertTrue(any(item["title"] == "Ordered tree runtime model" for item in tree["items"]))

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

    def test_c_bitmask_subset_scan_is_n_times_two_power_n(self):
        code = """int subset(int n) {
    int total = 0;
    for (int mask = 0; mask < (1 << n); mask++) {
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) total++;
        }
    }
    return total;
}
"""

        result = self.analyzer.analyze(code, "subset.c")

        self.assertEqual(result["time_complexity"], "O(n * 2^n)")
        self.assertEqual(result["space_complexity"], "O(1)")
        self.assertIn("Bitmask subset enumeration", result["time_complexity_reason"])

    def test_branching_recursion_with_shared_array_push_has_exponential_space(self):
        code = """function grow(n, arr = []) {
    if (n <= 0) return arr.length;

    arr.push(n);

    return grow(n - 1, arr) + grow(n - 1, arr);
}
"""

        result = self.analyzer.analyze(code, "grow.js")

        self.assertEqual(result["time_complexity"], "O(2^n)")
        self.assertEqual(result["space_complexity"], "O(2^n)")
        self.assertIn("same mutable collection", result["space_complexity_reason"])
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "recursive_shared_collection_growth")

    def test_high_complexity_function_is_reported_as_hotspot(self):
        code = """function grow(n, arr = []) {
    if (n <= 0) return arr.length;

    arr.push(n);

    return grow(n - 1, arr) + grow(n - 1, arr);
}
"""

        result = self.analyzer.analyze(code, "grow.js")

        self.assertIn("hotspots", result)
        self.assertEqual(result["hotspots"][0]["function"], "grow")
        self.assertEqual(result["hotspots"][0]["complexity"], "O(2^n)")
        self.assertEqual(result["hotspots"][0]["line"], 1)
        self.assertIn("arr.push", result["hotspots"][0]["snippet"])

    def test_backtracking_pop_keeps_branching_path_space_linear(self):
        code = """function paths(n, path = []) {
    if (n <= 0) return 1;

    path.push(n);
    const total = paths(n - 1, path) + paths(n - 1, path);
    path.pop();
    return total;
}
"""

        space = self.analyzer.detect_space_complexity(code, "javascript")

        self.assertEqual(space, "O(n)")

    def test_python_implicit_iteration_patterns_are_not_constant(self):
        cases = [
            ("""def total(nums):
    return sum(nums)
""", "O(n)", "O(1)"),
            ("""def contains(nums, target):
    return target in nums
""", "O(n)", "O(1)"),
            ("""def double(nums):
    return [x * 2 for x in nums]
""", "O(n)", "O(n)"),
            ("""def pairs(n):
    return [(i, j) for i in range(n) for j in range(n)]
""", "O(n²)", "O(n²)"),
        ]

        for code, expected_time, expected_space in cases:
            with self.subTest(code=code):
                result = self.analyzer.analyze(code, "implicit.py")

                self.assertEqual(result["time_complexity"], expected_time)
                self.assertEqual(result["space_complexity"], expected_space)
                self.assertEqual(result["analysis_confidence"]["time"], "medium")

    def test_javascript_implicit_array_methods_are_not_constant(self):
        cases = [
            ("""function double(nums) {
    return nums.map(x => x * 2);
}
""", "O(n)", "O(n)"),
            ("""function total(nums) {
    return nums.reduce((a, b) => a + b, 0);
}
""", "O(n)", "O(1)"),
        ]

        for code, expected_time, expected_space in cases:
            with self.subTest(code=code):
                result = self.analyzer.analyze(code, "implicit.js")

                self.assertEqual(result["time_complexity"], expected_time)
                self.assertEqual(result["space_complexity"], expected_space)
                self.assertEqual(result["analysis_confidence"]["time"], "medium")

    def test_javascript_reduce_spread_accumulator_counts_quadratic_copy_work(self):
        code = """function reduceTrap(arr) {
    return arr.reduce((acc, x) => {
        return [...acc, x];
    }, []);
}
"""

        result = self.analyzer.analyze(code, "reduceTrap.js")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "reduce_accumulator_copy")
        self.assertEqual(result["overall_complexity"]["total_allocation"], "O(n²)")
        self.assertEqual(details["reduceTrap"]["own_complexity"], "O(n²)")
        self.assertIn("copies the growing accumulator", result["time_complexity_reason"])

    def test_route_marks_reduce_spread_issue_without_manual_rewrite(self):
        code = """function reduceTrap(arr) {
    return arr.reduce((acc, x) => {
        return [...acc, x];
    }, []);
}
"""

        def no_ai_rewrite(analysis_result, code_text, language):
            return []

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=no_ai_rewrite):
            result = _analyze_with_extras(code, "reduceTrap.js")

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertTrue(result["issues"])
        self.assertEqual(result["issues"][0]["message"], "reduce() copies the growing accumulator on every iteration")
        self.assertIn("ai_solution_status", result["issues"][0])
        self.assertFalse(result["ai_transformed_code"]["available"])
        self.assertEqual(result["optimizations"], [])

    def test_typescript_json_stringified_subarray_set_is_cubic(self):
        code = """function jsonTrap(arr: number[]) {
    const set = new Set<string>();

    for (let i = 0; i < arr.length; i++) {
        for (let j = i; j < arr.length; j++) {
            const sub = arr.slice(i, j);
            set.add(JSON.stringify(sub));
        }
    }
}
"""

        result = self.analyzer.analyze(code, "trap.ts")

        self.assertEqual(result["time_complexity"], self.analyzer._cubic())
        self.assertEqual(result["space_complexity"], self.analyzer._cubic())
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "materialized_subarray_serialization")
        self.assertEqual(result["overall_complexity"]["total_allocation"], self.analyzer._cubic())
        self.assertEqual(result["analysis_confidence"]["time"], "high")

    def test_unknown_library_call_gets_low_confidence_unknown_complexity(self):
        code = """def run(data):
    return mystery_transform(data)
"""

        result = self.analyzer.analyze(code, "unknown.py")

        self.assertEqual(result["time_complexity"], "O(unknown)")
        self.assertEqual(result["analysis_confidence"]["time"], "low")

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

    def test_geometric_prefix_with_log_inner_work_is_n_log_n(self):
        code = """def complex_function(arr):
    n = len(arr)
    count = 0
    i = 1
    while i < n:
        for j in range(i):
            k = 1
            while k < n:
                count += arr[j] * k
                k *= 2
        i *= 2
    return count
"""

        result = self.analyzer.analyze(code, "complex_prefix.py")

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(1)")

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

    def test_javascript_sort_inside_loop_uses_engine_safe_linear_auxiliary_space(self):
        code = """function sortLoop(arr) {
    for (let i = 0; i < arr.length; i++) {
        arr.sort();
    }
}
"""

        result = self.analyzer.analyze(code, "sortLoop.js")

        self.assertEqual(result["time_complexity"], "O(n² log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("Sorting detected: O(n² log n)", result["time_complexity_reason"])
        self.assertIn("linear auxiliary space", result["space_complexity_reason"])

    def test_sort_inside_loop_across_brace_languages_counts_loop_factor(self):
        expected = self.analyzer._tuple_to_string(('n2_log', 1))
        cases = [
            ("SortLoop.java", """import java.util.*;
class A {
    void f(int[] arr) {
        for (int i = 0; i < arr.length; i++) Arrays.sort(arr);
    }
}
""", "O(log n)"),
            ("sort_loop.cpp", r"""#include <algorithm>
#include <vector>
using namespace std;
void f(vector<int>& arr) { for (int i = 0; i < arr.size(); i++) sort(arr.begin(), arr.end()); }
""", "O(log n)"),
            ("sort_loop.js", """function f(arr) {
    const out = [];
    for (const x of arr) { out.push(x); out.sort((a, b) => a - b); }
    return out;
}
""", "O(n)"),
            ("sort_loop.ts", """function f(arr: number[]) {
    for (let i = 0; i < arr.length; i++) arr.sort((a, b) => a - b);
}
""", "O(n)"),
        ]

        for filename, code, expected_space in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["time_complexity"], expected)
                self.assertEqual(result["space_complexity"], expected_space)

    def test_sequence_membership_inside_loop_adds_hidden_linear_factor(self):
        code = """def f(arr):
    seen = []
    count = 0
    for x in arr:
        if x in seen:
            count += 1
        seen.append(x)
    return count
"""

        result = self.analyzer.analyze(code, "membership.py")

        self.assertEqual(result["time_complexity"], self.analyzer._quadratic())
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("Membership test over a sequence", result["time_complexity_reason"])

    def test_materialized_set_builtin_uses_linear_space(self):
        code = """def f(arr):
    s = set(arr)
    total = 0
    for x in arr:
        if x in s:
            total += 1
    return total
"""

        result = self.analyzer.analyze(code, "set_membership.py")

        self.assertEqual(result["time_complexity"], "O(n)")
        self.assertEqual(result["space_complexity"], "O(n)")

    def test_binary_search_patterns_are_logarithmic_across_languages(self):
        cases = [
            ("bs.py", """def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
"""),
            ("bs.js", """function bs(arr, target) {
    let lo = 0, hi = arr.length - 1;
    while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        if (arr[mid] === target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
"""),
            ("BS.java", """class BS {
    int bs(int[] arr, int target) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (arr[mid] == target) return mid;
            if (arr[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }
}
"""),
            ("bs.cpp", r"""#include <vector>
using namespace std;
int bs(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
"""),
        ]

        for filename, code in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                details = {item["function"]: item for item in result["function_complexity_details"]}
                self.assertEqual(result["time_complexity"], "O(log n)")
                self.assertEqual(result["space_complexity"], "O(1)")
                self.assertNotIn("mid", details)

    def test_tree_recursion_and_memoized_fibonacci_are_not_naive_exponential(self):
        tree = """def count(node):
    if node is None:
        return 0
    return 1 + count(node.left) + count(node.right)
"""
        fib = """from functools import lru_cache
@lru_cache(None)
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""

        tree_result = self.analyzer.analyze(tree, "tree.py")
        fib_result = self.analyzer.analyze(fib, "fib.py")

        self.assertEqual(tree_result["time_complexity"], "O(n)")
        self.assertEqual(tree_result["space_complexity"], "O(h)")
        self.assertIn("Tree traversal", tree_result["time_complexity_reason"])
        self.assertEqual(fib_result["time_complexity"], "O(n)")
        self.assertEqual(fib_result["space_complexity"], "O(n)")
        self.assertIn("Memoization", fib_result["time_complexity_reason"])

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

        call_graph = self.analyzer.call_graph_analyzer.get_call_chain_report(
            code,
            self.analyzer.last_func_complexities,
            "python",
            self.analyzer.last_func_own_complexities,
        )
        self.assertEqual(call_graph[0]["function"], "power")
        self.assertEqual(call_graph[0]["own_complexity"], "O(log n)")
        self.assertEqual(call_graph[0]["effective_complexity"], "O(k\u00b3 log n)")

        with patch("app.ai_explainer._call_ai_completion", return_value=None):
            explanations = get_function_level_explanations(
                self.analyzer.last_func_complexities,
                call_graph,
                "python",
                result["function_complexity_details"],
                code,
            )
        explanation_by_name = {item["function"]: item["explanation"] for item in explanations}
        self.assertIn("cubic helper", explanation_by_name["multiply"])
        self.assertIn("each recursive level", explanation_by_name["power"])

        with patch("app.ai_explainer._call_ai_completion", return_value=None):
            ai_explanation = get_ai_explanation(result, code, "python")
        self.assertIn("binary matrix exponentiation", ai_explanation["why_this_complexity"].lower())
        self.assertIn("multiply()", ai_explanation["why_this_complexity"])

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

    def test_ai_function_text_rejects_conflicting_big_o_words(self):
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
        ai_items = [{
            "function": "power",
            "explanation": "This function is O(n) because Grok recalculated it."
        }]

        merged = _merge_ai_function_explanations(details, ai_items)

        self.assertNotIn("Grok recalculated", merged[0]["explanation"])
        self.assertIn("own/control cost O(log n)", merged[0]["explanation"])

    def test_ai_top_explanation_rejects_conflicting_big_o_words(self):
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
    half = power(matrix, n // 2)
    return multiply(half, half)
"""
        result = self.analyzer.analyze(code, "matrix_power.py")
        bad_payload = (
            '{"why_this_complexity":"This is O(n) because I recalculated it.",'
            '"real_world_analogy":"bad",'
            '"performance_impact":"O(n) growth",'
            '"top_optimization":"invented"}'
        )

        with patch("app.ai_explainer._call_ai_completion", return_value=(bad_payload, "grok")):
            explanation = get_ai_explanation(result, code, "python")

        self.assertEqual(explanation["source"], "analyzer_fallback")
        self.assertTrue(explanation["ai_rejected"])
        self.assertEqual(explanation["detected_time_complexity"], result["time_complexity"])
        self.assertNotIn("recalculated", explanation["why_this_complexity"])

    def test_ai_optimization_suggestion_replaces_static_example_when_available(self):
        optimizations = [{
            "title": "Review Nested Loops - O(n²) may be reducible",
            "problem": "Nested linear loops perform pairwise or repeated work.",
            "solution": "Choose the optimization that matches the problem.",
            "complexity_before": "O(n²)",
            "complexity_after": "problem-dependent",
            "example": "// static generic strategy",
        }]
        ai_payload = {
            "optimizations": [{
                "index": 0,
                "available": True,
                "title": "Use a set for duplicate detection",
                "problem": "The function scans all pairs to find a duplicate.",
                "solution": "Track seen values in a set.",
                "complexity_before": "O(n²)",
                "complexity_after": "O(n)",
                "code": (
                    "function hasDuplicate(arr) {\n"
                    "  const seen = new Set();\n"
                    "  for (const value of arr) {\n"
                    "    if (seen.has(value)) return true;\n"
                    "    seen.add(value);\n"
                    "  }\n"
                    "  return false;\n"
                    "}"
                ),
                "notes": "Same boolean result with one pass.",
            }]
        }

        merged = _merge_ai_optimization_suggestions(optimizations, ai_payload, provider="groq")

        self.assertTrue(merged[0]["ai_generated"])
        self.assertEqual(merged[0]["source"], "groq")
        self.assertEqual(merged[0]["source_label"], "Groq")
        self.assertEqual(merged[0]["complexity_after"], "O(n)")
        self.assertIn("hasDuplicate", merged[0]["example"])
        self.assertEqual(merged[0]["analyzer_example"], "// static generic strategy")

    def test_ai_optimization_suggestion_appends_discovered_rewrite_without_analyzer_candidate(self):
        ai_payload = {
            "discovered_optimizations": [{
                "function": "hasDuplicate",
                "available": True,
                "title": "Use a set for duplicate detection",
                "problem": "The function compares every pair.",
                "solution": "Track values already seen.",
                "complexity_before": "O(n²)",
                "complexity_after": "O(n)",
                "code": "function hasDuplicate(arr) { return new Set(arr).size !== arr.length; }",
                "notes": "Same true/false result for duplicate detection.",
            }]
        }

        merged = _merge_ai_optimization_suggestions([], ai_payload, provider="groq")

        self.assertEqual(len(merged), 1)
        self.assertTrue(merged[0]["ai_generated"])
        self.assertTrue(merged[0]["ai_discovered"])
        self.assertEqual(merged[0]["source"], "groq")
        self.assertEqual(merged[0]["source_label"], "Groq")
        self.assertEqual(merged[0]["function"], "hasDuplicate")
        self.assertEqual(merged[0]["complexity_after"], "O(n)")

    def test_ai_discovery_prompt_sends_every_function_snippet(self):
        code = """function hasDuplicate(nums) {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] === nums[j]) return true;
        }
    }
    return false;
}

function alreadyCheap(nums) {
    return nums.length;
}
"""

        result = self.analyzer.analyze(code, "dupes.js")
        targets = _expensive_function_targets(result)
        prompt = _build_ai_optimization_prompt(result, code, "javascript", [], targets)

        self.assertTrue(any(target["function"] == "hasDuplicate" for target in targets))
        self.assertTrue(any(target["function"] == "alreadyCheap" for target in targets))
        duplicate_target = next(target for target in targets if target["function"] == "hasDuplicate")
        self.assertEqual(duplicate_target["effective_complexity"], "O(n²)")
        self.assertIn("snippet", duplicate_target)
        self.assertIn("if (nums[i] === nums[j]) return true;", duplicate_target["snippet"])
        self.assertIn("Independently inspect every function rewrite target", prompt)
        self.assertIn("ALL FUNCTIONS FOR GROQ REWRITE CHECK", prompt)
        self.assertIn('"function": "hasDuplicate"', prompt)
        self.assertIn('"function": "alreadyCheap"', prompt)
        self.assertIn('"snippet"', prompt)

    def test_ai_discovery_targets_known_lower_complexity_patterns(self):
        code = """memo = {}
def fibonacci(n):
    if n <= 1:
        return n
    if n in memo:
        return memo[n]
    memo[n] = fibonacci(n - 1) + fibonacci(n - 2)
    return memo[n]

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        if key not in self.cache:
            return -1
        self.order.remove(key)
        self.order.append(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)

def build_string(n):
    s = ""
    for i in range(n):
        s += str(i)
    return s

def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""

        result = self.analyzer.analyze(code, "sample.py")
        targets = _expensive_function_targets(result)
        by_name = {target["function"]: target for target in targets}

        self.assertIn("build_string", by_name)
        self.assertIn("fibonacci", by_name)
        self.assertIn("get", by_name)
        self.assertIn("put", by_name)
        self.assertIn("binary_search", by_name)
        self.assertEqual(by_name["build_string"]["rewrite_hint"]["kind"], "string_builder_join")
        self.assertEqual(by_name["fibonacci"]["rewrite_hint"]["kind"], "fibonacci_fast_doubling")
        self.assertEqual(by_name["get"]["rewrite_hint"]["kind"], "lru_ordered_dict")
        self.assertNotIn("rewrite_hint", by_name["binary_search"])

    def test_ordered_dict_lru_rewrite_validates_function_complexity(self):
        original = """class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        if key not in self.cache:
            return -1
        self.order.remove(key)
        self.order.append(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)
"""
        optimized = """from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value
"""

        get_validation = _validate_ai_rewrite_complexity(
            optimized,
            "python",
            "O(n)",
            original_code=original,
            required_function="get",
        )
        put_validation = _validate_ai_rewrite_complexity(
            optimized,
            "python",
            "O(n)",
            original_code=original,
            required_function="put",
        )

        self.assertTrue(get_validation["valid"])
        self.assertTrue(put_validation["valid"])
        self.assertEqual(get_validation["complexity"], "O(1)")
        self.assertEqual(put_validation["complexity"], "O(1)")

    def test_groq_discovery_accepts_verified_rewrites(self):
        code = """function hasDuplicate(nums) {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] === nums[j]) return true;
        }
    }
    return false;
}
"""

        result = self.analyzer.analyze(code, "dupes.js")
        groq_payload = """{"discovered_optimizations":[{
            "function":"hasDuplicate",
            "available":true,
            "title":"Use a set",
            "problem":"Nested duplicate scan",
            "solution":"Track seen values",
            "complexity_before":"O(n²)",
            "complexity_after":"O(n)",
            "code":"function hasDuplicate(nums) { return new Set(nums).size !== nums.length; }",
            "notes":"Same duplicate result."
        }]}"""

        with patch("app.ai_explainer._call_ai_completion", return_value=(groq_payload, "groq")):
            enhanced = enhance_optimizations_with_ai({**result, "optimizations": []}, code, "javascript")

        self.assertEqual(len(enhanced), 1)
        self.assertTrue(enhanced[0]["ai_generated"])
        self.assertEqual(enhanced[0]["source"], "groq")
        self.assertEqual(enhanced[0]["source_label"], "Groq")

    def test_route_hides_analyzer_fallback_optimizations_when_grok_returns_none(self):
        code = """public class Test {
    public static int tricky(int n) {
        if (n <= 1) return 1;
        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += tricky(n / 2);
        }
        return sum;
    }
}
"""

        seen_payload = {}

        def fallback_suggestions(analysis_result, code_text, language):
            seen_payload.update(analysis_result)
            return analysis_result.get("optimizations") or []

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=fallback_suggestions):
            result = _analyze_with_extras(code, "Test.java", {"n": 16})

        self.assertEqual(result["time_complexity"], "O(n^((log n + 1)/2))")
        self.assertEqual(seen_payload["optimizations"], [])
        self.assertFalse(seen_payload["transformed_code"]["available"])
        self.assertEqual(result["optimizations"], [])
        self.assertFalse(result["transformed_code"]["available"])
        self.assertFalse(result["ai_transformed_code"]["available"])
        self.assertEqual(result["ai_transformed_code"]["source"], "ai_discovery")

    def test_route_uses_primary_groq_rewrite_once(self):
        code = """public class Test {
    public static int tricky(int n) {
        if (n <= 1) return 1;
        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += tricky(n / 2);
        }
        return sum;
    }
}
"""
        grok_code = """public class Test {
    public static int tricky(int n) {
        if (n <= 1) return 1;
        return n * tricky(n / 2);
    }
}
"""

        def discovered_only(analysis_result, code_text, language):
            self.assertEqual(analysis_result["optimizations"], [])
            return [{
                "title": "Groq collapsed repeated recursive calls",
                "problem": "tricky repeats the same recursive call inside the loop.",
                "solution": "Call tricky(n / 2) once and multiply by n.",
                "complexity_before": "O(n^((log n + 1)/2))",
                "complexity_after": "O(log n)",
                "example": grok_code,
                "ai_generated": True,
                "ai_discovered": True,
                "source": "groq",
                "source_label": "Groq",
                "ai_note": "Groq discovered this rewrite from the expensive function target.",
            }]

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=discovered_only):
            result = _analyze_with_extras(code, "Test.java", {"n": 16})

        self.assertEqual(result["optimizations"], [])
        self.assertEqual(result["ai_transformed_code"]["source"], "groq")
        self.assertEqual(result["ai_transformed_code"]["source_label"], "Groq")
        self.assertEqual(result["ai_transformed_code"]["code"], grok_code)
        self.assertFalse(result["transformed_code"]["available"])

    def test_route_keeps_additional_distinct_groq_rewrites_only(self):
        code = """function a(n) {
    if (n <= 1) return 1;
    return a(n - 1) + a(n - 1);
}

function b(n) {
    let s = "";
    for (let i = 0; i < n; i++) s += i;
    return s;
}
"""
        first_code = """function a(n) {
    return Math.max(1, 2 ** n);
}
"""
        second_code = """function b(n) {
    const parts = [];
    for (let i = 0; i < n; i++) parts.push(String(i));
    return parts.join("");
}
"""

        def two_rewrites(analysis_result, code_text, language):
            return [
                {
                    "title": "Groq optimized a",
                    "problem": "a repeats recursive work.",
                    "solution": "Use direct computation.",
                    "complexity_before": "O(2^n)",
                    "complexity_after": "O(1)",
                    "example": first_code,
                    "ai_generated": True,
                    "ai_discovered": True,
                    "source": "groq",
                    "source_label": "Groq",
                },
                {
                    "title": "Groq optimized b",
                    "problem": "b repeatedly copies strings.",
                    "solution": "Collect parts and join once.",
                    "complexity_before": "O(n²)",
                    "complexity_after": "O(n)",
                    "example": second_code,
                    "ai_generated": True,
                    "ai_discovered": True,
                    "source": "groq",
                    "source_label": "Groq",
                },
                {
                    "title": "Duplicate Groq optimized a",
                    "problem": "same duplicate rewrite.",
                    "solution": "same duplicate rewrite.",
                    "complexity_before": "O(2^n)",
                    "complexity_after": "O(1)",
                    "example": first_code,
                    "ai_generated": True,
                    "ai_discovered": True,
                    "source": "groq",
                    "source_label": "Groq",
                },
            ]

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=two_rewrites):
            result = _analyze_with_extras(code, "two.js")

        self.assertEqual(result["ai_transformed_code"]["code"], first_code)
        self.assertEqual(len(result["optimizations"]), 1)
        self.assertEqual(result["optimizations"][0]["example"], second_code)

    def test_route_attaches_ai_solution_to_issue_card_payload(self):
        code = """function grow(n, arr = []) {
    if (n <= 0) return arr.length;

    arr.push(n);

    return grow(n - 1, arr) + grow(n - 1, arr);
}
"""
        grok_code = """function grow(n, arr = []) {
    const start = arr.length;
    const pushes = Math.max(0, (2 ** n) - 1);
    for (let i = 0; i < pushes; i++) arr.push(n - i);
    return 2 ** n * start + pushes * (pushes + 1);
}
"""

        def discovered_only(analysis_result, code_text, language):
            self.assertEqual(analysis_result["optimizations"], [])
            return [{
                "title": "Groq collapsed repeated recursion",
                "problem": "grow repeats the same recursive branch twice.",
                "solution": "Replace the exponential call tree with a direct counted update.",
                "complexity_before": "O(2^n)",
                "complexity_after": "O(n)",
                "example": grok_code,
                "ai_generated": True,
                "ai_discovered": True,
                "source": "groq",
                "source_label": "Groq",
                "function": "grow",
                "ai_note": "Groq returned a lower-complexity rewrite and CodeScope accepted it.",
            }]

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=discovered_only), \
             patch("app.routes.get_ai_explanation", return_value={
                 "available": True,
                 "why_this_complexity": "grow has two recursive calls per level.",
                 "real_world_analogy": "",
                 "performance_impact": "",
                 "top_optimization": "",
             }):
            result = _analyze_with_extras(code, "grow.js", {"n": 4})

        self.assertTrue(result["issues"])
        issue = result["issues"][0]
        self.assertEqual(issue["message"], "Exponential recursion (O(2^n))")
        self.assertIn("ai_solution", issue)
        self.assertEqual(issue["ai_solution"]["source"], "groq")
        self.assertEqual(issue["ai_solution"]["source_label"], "Groq")
        self.assertEqual(issue["ai_solution"]["code"], grok_code)
        self.assertEqual(issue["ai_solution"]["complexity_before"], "O(2^n)")
        self.assertEqual(issue["ai_solution"]["complexity_after"], "O(n)")
        self.assertEqual(result["ai_transformed_code"]["code"], grok_code)

    def test_ai_rewrite_validation_rejects_changed_public_signature(self):
        original = """function hasDuplicate(nums) {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] === nums[j]) return true;
        }
    }
    return false;
}
"""
        optimized = """function faster(values) {
    return new Set(values).size !== values.length;
}
"""

        validation = _validate_ai_rewrite_complexity(
            optimized,
            "javascript",
            "O(n²)",
            original_code=original,
        )

        self.assertFalse(validation["valid"])
        self.assertIn("hasDuplicate", validation["reason"])

    def test_ai_rewrite_validation_accepts_lower_complexity_same_signature(self):
        original = """function hasDuplicate(nums) {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] === nums[j]) return true;
        }
    }
    return false;
}
"""
        optimized = """function hasDuplicate(nums) {
    const seen = new Set();
    for (let i = 0; i < nums.length; i++) {
        if (seen.has(nums[i])) return true;
        seen.add(nums[i]);
    }
    return false;
}
"""

        validation = _validate_ai_rewrite_complexity(
            optimized,
            "javascript",
            "O(n²)",
            original_code=original,
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["complexity"], "O(n)")

    def test_python_ai_rewrite_semantic_probe_rejects_wrong_output(self):
        original = """def count_positive(nums):
    total = 0
    for x in nums:
        if x > 0:
            total += 1
    return total
"""
        optimized = """def count_positive(nums):
    return len(nums)
"""

        validation = _validate_ai_rewrite_complexity(
            optimized,
            "python",
            "O(n)",
            original_code=original,
        )

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["semantic_equivalence"]["status"], "failed")

    def test_python_ai_rewrite_semantic_probe_checks_matching_outputs(self):
        original = """def count_items(nums):
    total = 0
    for x in nums:
        total += 1
    return total
"""
        optimized = """def count_items(nums):
    return len(nums)
"""

        validation = _validate_ai_rewrite_complexity(
            optimized,
            "python",
            "O(n²)",
            original_code=original,
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["semantic_guard"]["semantic_equivalence"]["status"], "checked")

    def test_ai_optimization_suggestion_must_validate_lower_complexity(self):
        optimizations = [{
            "title": "Use a set for duplicate detection",
            "problem": "Nested pair scan.",
            "solution": "Track seen values.",
            "complexity_before": "O(n²)",
            "complexity_after": "O(n)",
            "example": "// analyzer target",
        }]
        ai_payload = {
            "optimizations": [{
                "index": 0,
                "available": True,
                "title": "Still nested",
                "problem": "Claims to optimize.",
                "solution": "But keeps nested loops.",
                "complexity_before": "O(n²)",
                "complexity_after": "O(n)",
                "code": """function hasDuplicate(nums) {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] === nums[j]) return true;
        }
    }
    return false;
}""",
                "notes": "Incorrectly claims lower complexity.",
            }]
        }

        merged = _merge_ai_optimization_suggestions(optimizations, ai_payload, language="javascript")

        self.assertFalse(merged[0].get("ai_generated"))
        self.assertTrue(merged[0].get("ai_reviewed"))
        self.assertIn("not lower", merged[0]["ai_note"])

    def test_dynamic_constructs_lower_confidence_even_with_loop_match(self):
        code = """def reflected_sum(obj, n):
    total = 0
    for i in range(n):
        total += getattr(obj, "value")
    return total
"""

        result = self.analyzer.analyze(code, "reflect.py")

        self.assertEqual(result["time_complexity"], "O(n)")
        self.assertEqual(result["analysis_confidence"]["time"], "medium")
        self.assertTrue(any("Dynamic attribute lookup" in note for note in result["analysis_confidence"]["notes"]))

    def test_batch_summary_surfaces_project_level_risks(self):
        results = [
            {
                "filename": "fast.py",
                "result": self.analyzer.analyze("def fast(n):\n    return n\n", "fast.py"),
            },
            {
                "filename": "slow.py",
                "result": self.analyzer.analyze("""def slow(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i + j
    return total
""", "slow.py"),
            },
            {
                "filename": "dynamic.py",
                "result": self.analyzer.analyze("""def dynamic(obj, n):
    for i in range(n):
        getattr(obj, "run")
    return n
""", "dynamic.py"),
            },
        ]

        summary = _build_batch_summary(results, "zip")

        self.assertEqual(summary["worst_time_complexity"], "O(n²)")
        self.assertGreaterEqual(summary["confidence_counts"]["medium"], 1)
        self.assertTrue(any(item["filename"] == "slow.py" for item in summary["high_complexity_files"]))

    def test_batch_summary_builds_cross_file_project_intelligence(self):
        source_files = [
            {
                "filename": "app/main.py",
                "code": """from services.slow import slow

def run(n):
    return slow(n)
""",
            },
            {
                "filename": "app/services/slow.py",
                "code": """def slow(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i + j
    return total
""",
            },
        ]
        results = [
            {
                "filename": item["filename"],
                "result": self.analyzer.analyze(item["code"], item["filename"]),
            }
            for item in source_files
        ]

        summary = _build_batch_summary(results, "github", source_files)
        project = summary["project_intelligence"]

        self.assertTrue(project["available"])
        self.assertEqual(project["file_count"], 2)
        self.assertTrue(any(
            edge["from"] == "app/main.py" and edge["to"] == "app/services/slow.py"
            for edge in project["dependency_edges"]
        ))
        self.assertTrue(any(call["symbol"] == "slow" for call in project["cross_file_calls"]))
        self.assertTrue(any(
            item["filename"] == "app/services/slow.py" and item["complexity"] == self.analyzer._quadratic()
            for item in project["bottlenecks"]
        ))
        self.assertTrue(any(
            path["entrypoint"] == "app/main.py" and path["bottleneck_file"] == "app/services/slow.py"
            for path in project["critical_paths"]
        ))

    def test_batch_zip_skips_vendor_and_generated_paths(self):
        self.assertTrue(_should_skip_batch_path("project/node_modules/pkg/index.js"))
        self.assertTrue(_should_skip_batch_path("project/dist/bundle.js"))
        self.assertTrue(_should_skip_batch_path("project/.hidden.py"))
        self.assertFalse(_should_skip_batch_path("project/src/index.ts"))

    def test_pdf_report_accepts_project_intelligence_summary(self):
        analysis_data = {
            "total_files": 1,
            "total_lines": 3,
            "total_issues": 0,
            "average_rating": 9,
            "project_summary": {
                "project_intelligence": {
                    "available": True,
                    "summary": "Resolved one dependency edge.",
                    "project_confidence": "high",
                    "dependency_edges": [{"from": "main.py", "to": "slow.py"}],
                    "cross_file_calls": [{"symbol": "slow"}],
                    "bottlenecks": [{
                        "filename": "slow.py",
                        "function": "slow",
                        "complexity": "O(n²)",
                        "called_by_count": 1,
                    }],
                    "critical_paths": [{
                        "entrypoint": "main.py",
                        "bottleneck_file": "slow.py",
                        "bottleneck_function": "slow",
                        "complexity": "O(n²)",
                        "path": ["main.py", "slow.py"],
                    }],
                    "cycles": [],
                    "limitations": ["Static project graph limit."],
                }
            },
            "files": [{
                "filename": "main.py",
                "result": self.analyzer.analyze("def main(n):\n    return n\n", "main.py"),
            }],
        }

        pdf = generate_pdf_report(analysis_data, "github")

        self.assertGreater(len(pdf), 1000)

    def test_union_find_structure_is_inverse_ackermann_without_name_hints(self):
        code = """parent = {}
rank = {}

def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(x, y):
    rootX = find(x)
    rootY = find(y)

    if rootX != rootY:
        if rank[rootX] > rank[rootY]:
            parent[rootY] = rootX
        elif rank[rootX] < rank[rootY]:
            parent[rootX] = rootY
        else:
            parent[rootY] = rootX
            rank[rootX] += 1
"""

        result = self.analyzer.analyze(code, "dsu.py")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(α(n))")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(self.analyzer.last_func_complexities["find"], "O(α(n))")
        self.assertEqual(self.analyzer.last_func_complexities["union"], "O(α(n))")
        self.assertEqual(details["find"]["own_complexity"], "O(α(n))")
        self.assertEqual(details["union"]["effective_complexity"], "O(α(n))")
        self.assertIn("path compression", result["time_complexity_reason"].lower())
        self.assertIn("amortized_analysis", result)
        self.assertEqual(result["amortized_analysis"]["amortized_per_operation"], "O(α(n))")

    def test_immutable_string_concat_inside_loop_is_quadratic(self):
        code = """def build_string(n):
    s = ""
    for i in range(n):
        s += str(i)
    return s
"""

        result = self.analyzer.analyze(code, "string_build.py")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], self.analyzer._quadratic())
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "immutable_string_concat_loop")
        self.assertEqual(result["memory_allocation_analysis"]["peak_live_auxiliary_space"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["total_allocated_space"], self.analyzer._quadratic())
        self.assertEqual(result["overall_complexity"]["total_allocation"], self.analyzer._quadratic())
        self.assertIn("Immutable string concatenation", result["time_complexity_reason"])
        self.assertEqual(details["build_string"]["own_complexity"], self.analyzer._quadratic())
        self.assertTrue(result["issues"])
        self.assertIn("immutable string", result["issues"][0]["message"])
        self.assertTrue(result["optimizations"])
        self.assertEqual(len(result["optimizations"]), 1)
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_recursive_resort_merge_is_n_log_squared(self):
        code = """def tricky_merge_sort(arr):
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = tricky_merge_sort(arr[:mid])
    right = tricky_merge_sort(arr[mid:])

    return sorted(left + right)
"""

        result = self.analyzer.analyze(code, "tricky_merge.py")
        details = {item["function"]: item for item in result["function_complexity_details"]}
        expected_time = self.analyzer._tuple_to_string(('n_log2', 1))

        self.assertEqual(result["time_complexity"], expected_time)
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "recursive_resort_merge_copy")
        self.assertEqual(result["memory_allocation_analysis"]["peak_live_auxiliary_space"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["total_allocated_space"], "O(n log n)")
        self.assertEqual(result["overall_complexity"]["total_allocation"], "O(n log n)")
        self.assertIn("sorted(left + right)", result["space_complexity_reason"])
        self.assertIn("sorted(left + right)", result["time_complexity_reason"])
        self.assertEqual(details["tricky_merge_sort"]["own_complexity"], expected_time)
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n log n)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_cpp_vector_front_insert_inside_loop_is_quadratic(self):
        code = r"""#include <vector>
using namespace std;

void trickyInsert(int n) {
    vector<int> v;
    for (int i = 0; i < n; i++) {
        v.insert(v.begin(), i);
    }
}
"""

        result = self.analyzer.analyze(code, "tricky.cpp")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("front insertion", result["time_complexity_reason"].lower())
        self.assertEqual(details["trickyInsert"]["own_complexity"], "O(n²)")
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n)")
        self.assertTrue(result["transformed_code"]["available"])

        compact = "void f(int n){ vector<int> v; for(int i=0;i<n;i++){ v.insert(v.begin(), i); } }"
        compact_result = self.analyzer.analyze(compact, "compact.cpp")
        self.assertEqual(compact_result["time_complexity"], "O(n²)")
        self.assertEqual(compact_result["space_complexity"], "O(n)")

    def test_cpp_common_extensions_are_analyzed_as_cpp(self):
        code = r"""#include <vector>
using namespace std;

void fillVector(int n) {
    vector<int> v;
    for (int i = 0; i < n; i++) {
        v.push_back(i);
    }
}
"""

        for filename in ("fill.cc", "fill.cxx", "fill.hpp"):
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["language"], "cpp")
                self.assertEqual(result["time_complexity"], "O(n)")
                self.assertEqual(result["space_complexity"], "O(n)")

        compact = "void f(int n) { vector<int> v; for (int i = 0; i < n; i++) v.push_back(i); }"
        compact_result = self.analyzer.analyze(compact, "compact.cc")
        self.assertEqual(compact_result["language"], "cpp")
        self.assertEqual(compact_result["time_complexity"], "O(n)")
        self.assertEqual(compact_result["space_complexity"], "O(n)")

    def test_front_insert_shift_patterns_across_supported_languages(self):
        cases = [
            ("python", "front.py", """def build(n):
    arr = []
    for i in range(n):
        arr.insert(0, i)
    return arr
"""),
            ("javascript", "front.js", """function build(n) {
    const arr = [];
    for (let i = 0; i < n; i++) {
        arr.unshift(i);
    }
    return arr;
}
"""),
            ("java", "Front.java", """import java.util.*;
class Front {
    public void build(int n) {
        ArrayList<Integer> arr = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            arr.add(0, i);
        }
    }
}
"""),
        ]

        for language, filename, code in cases:
            with self.subTest(language=language):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["language"], language)
                self.assertEqual(result["time_complexity"], "O(n²)")
                self.assertEqual(result["space_complexity"], "O(n)")
                self.assertIn("front insertion", result["time_complexity_reason"].lower())

    def test_typescript_is_first_class_for_schema_and_analysis(self):
        code = """function twoSum(nums: number[], target: number): number {
    for (let i = 0; i < nums.length; i++) {
        for (let j = i + 1; j < nums.length; j++) {
            if (nums[i] + nums[j] === target) return i;
        }
    }
    return -1;
}
"""

        result = self.analyzer.analyze(code, "solver.ts")
        schema = result["input_schema"]

        self.assertEqual(result["language"], "typescript")
        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(schema["language"], "typescript")
        self.assertEqual(schema["function"], "twoSum")
        self.assertEqual(schema["parameters"][0]["name"], "nums")
        self.assertEqual(schema["parameters"][0]["kind"], "array")
        self.assertEqual(schema["parameters"][1]["name"], "target")
        self.assertIn(schema["parameters"][1]["kind"], ("integer", "number"))

    def test_typescript_nested_key_pair_count_gets_specific_rewrite(self):
        code = """function keyTrap(obj: Record<string, number>) {
    let count = 0;
    for (let key in obj) {
        for (let inner in obj) {
            count++;
        }
    }
    return count;
"""

        result = self.analyzer.analyze(code, "keyTrap.ts")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["language"], "typescript")
        self.assertEqual(result["time_complexity"], "O(n\u00b2)")
        self.assertEqual(result["space_complexity"], "O(1)")
        self.assertIn("count every pair of keys", result["time_complexity_reason"])
        self.assertIn("keyTrap", details)
        self.assertIn("count every pair of keys", details["keyTrap"]["reason"])
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n)")
        self.assertIn("keyCount * keyCount", result["optimizations"][0]["example"])
        self.assertTrue(result["transformed_code"]["available"])
        self.assertIn("for (const key in obj)", result["transformed_code"]["code"])

    def test_javascript_and_typescript_arrow_function_bodies_are_analyzed(self):
        cases = [
            ("arrow.js", """const count = (n) => {
    let total = 0;
    for (let i = 0; i < n; i++) {
        total++;
    }
    return total;
};
""", "javascript"),
            ("arrow.ts", """const count = (n: number): number => {
    let total = 0;
    for (let i = 0; i < n; i++) {
        total++;
    }
    return total;
};
""", "typescript"),
        ]

        for filename, code, language in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                details = {item["function"]: item for item in result["function_complexity_details"]}

                self.assertEqual(result["language"], language)
                self.assertEqual(result["time_complexity"], "O(n)")
                self.assertEqual(result["input_schema"]["function"], "count")
                self.assertIn("count", details)
                self.assertEqual(details["count"]["own_complexity"], "O(n)")

    def test_typescript_recursive_half_slice_counts_copy_work(self):
        code = """function recursiveSlice(arr: number[]): number {
    if (arr.length <= 1) return 0;

    const mid = Math.floor(arr.length / 2);
    return recursiveSlice(arr.slice(0, mid)) +
           recursiveSlice(arr.slice(mid));
}
"""

        result = self.analyzer.analyze(code, "recursiveSlice.ts")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["language"], "typescript")
        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n log n)")
        self.assertEqual(result["overall_complexity"]["time"], "O(n log n)")
        self.assertEqual(result["overall_complexity"]["space"], "O(n log n)")
        self.assertEqual(result["overall_complexity"]["peak_space"], "O(n)")
        self.assertEqual(result["overall_complexity"]["total_allocation"], "O(n log n)")
        self.assertEqual(
            result["overall_complexity"]["headline"],
            "O(n log n) time, O(n log n) space"
        )
        self.assertIn("Space complexity is reported as O(n log n)", result["overall_complexity"]["memory_model"])
        self.assertIn("Total allocated slice memory", result["space_complexity_reason"])
        self.assertEqual(result["memory_allocation_analysis"]["peak_live_auxiliary_space"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["total_allocated_space"], "O(n log n)")
        self.assertIn("copied slices", result["time_complexity_reason"])
        self.assertIn("recursiveSlice", details)
        self.assertEqual(details["recursiveSlice"]["own_complexity"], "O(n log n)")
        self.assertIn("copied slices", details["recursiveSlice"]["reason"])
        self.assertTrue(any("slice/copy" in issue["message"] for issue in result["issues"]))
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_grok_prompt_uses_total_headline_and_peak_allocation_contract(self):
        code = """function recursiveSlice(arr: number[]): number {
    if (arr.length <= 1) return 0;
    const mid = Math.floor(arr.length / 2);
    return recursiveSlice(arr.slice(0, mid)) + recursiveSlice(arr.slice(mid));
}
"""
        result = self.analyzer.analyze(code, "recursiveSlice.ts")
        prompt = _build_ai_prompt(result, code, "typescript")

        self.assertIn("Total Complexity Headline", prompt)
        self.assertIn(result["overall_complexity"]["headline"], prompt)
        self.assertIn("Do not call total allocation \"peak space\"", prompt)
        self.assertIn("For every field, mention at least one concrete code cue", prompt)

    def test_typescript_memoized_recursive_slice_keys_count_stored_key_space(self):
        code = """const memo: Record<string, number> = {};

function hard(arr: number[]): number {
    const key = arr.join(",");
    if (memo[key]) return memo[key];

    if (arr.length <= 1) return 1;

    const mid = Math.floor(arr.length / 2);

    return memo[key] =
        hard(arr.slice(0, mid)) +
        hard(arr.slice(mid));
}
"""

        result = self.analyzer.analyze(code, "hard.ts")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n log n)")
        self.assertEqual(result["overall_complexity"]["peak_space"], "O(n log n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "memoized_recursive_slice_keys")
        self.assertIn("serialized keys", result["space_complexity_reason"])
        self.assertIn("materialized memo keys", result["time_complexity_reason"])
        self.assertEqual(details["hard"]["own_complexity"], "O(n log n)")
        self.assertTrue(any("memo table" in issue["message"] for issue in result["issues"]))

    def test_ordered_map_access_inside_nested_loop_adds_log_factor(self):
        code = r"""#include <map>
using namespace std;

void mapLoop(int n) {
    map<int, int> m;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            m[i * n + j]++;
        }
    }
}
"""

        result = self.analyzer.analyze(code, "map_loop.cpp")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n² log n)")
        self.assertEqual(result["space_complexity"], "O(n²)")
        self.assertIn("ordered map", result["time_complexity_reason"].lower())
        self.assertEqual(details["mapLoop"]["own_complexity"], "O(n² log n)")
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(n²)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_java_treemap_access_inside_loop_adds_log_factor(self):
        code = """import java.util.*;
class Example {
    public void mapLoop(int n) {
        TreeMap<Integer, Integer> m = new TreeMap<>();
        for (int i = 0; i < n; i++) {
            m.put(i, m.getOrDefault(i, 0) + 1);
        }
    }
}
"""

        result = self.analyzer.analyze(code, "Example.java")

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("tree lookup", result["time_complexity_reason"].lower())

    def test_cpp_multiset_drain_loop_counts_tree_erase_and_container_space(self):
        code = """#include <set>
using namespace std;

void multiErase(multiset<int>& s) {
    while (!s.empty()) {
        auto it = s.begin();
        s.erase(it);
    }
}
"""

        result = self.analyzer.analyze(code, "multiErase.cpp")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "ordered_tree_drain")
        self.assertEqual(result["memory_allocation_analysis"]["auxiliary_space"], "O(1)")
        self.assertIn("ordered tree container", result["time_complexity_reason"])
        self.assertIn("O(1) extra auxiliary", result["space_complexity_reason"])
        self.assertEqual(details["multiErase"]["own_complexity"], "O(n log n)")

    def test_java_treeset_drain_loop_counts_tree_remove_and_container_space(self):
        code = """import java.util.*;
class Example {
    void drain(TreeSet<Integer> set) {
        while (!set.isEmpty()) {
            set.remove(set.first());
        }
    }
}
"""

        result = self.analyzer.analyze(code, "Example.java")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "ordered_tree_drain")
        self.assertEqual(details["drain"]["own_complexity"], "O(n log n)")

    def test_java_nested_stream_flatmap_count_is_quadratic_and_lazy_space(self):
        code = """import java.util.*;

public class Test {
    public static long nested(List<Integer> list) {
        return list.stream()
            .flatMap(x -> list.stream().map(y -> x + y))
            .count();
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "java_nested_stream_pipeline")
        self.assertEqual(result["memory_allocation_analysis"]["auxiliary_space"], "O(1)")
        self.assertIn("Nested Java Stream pipeline", result["time_complexity_reason"])
        self.assertIn("count() consumes", result["space_complexity_reason"])
        self.assertEqual(details["nested"]["own_complexity"], "O(n²)")

    def test_java_nested_stream_collect_materializes_quadratic_output(self):
        code = """import java.util.*;

public class Test {
    public static List<Integer> pairs(List<Integer> list) {
        return list.stream()
            .flatMap(x -> list.stream().map(y -> x + y))
            .collect(java.util.stream.Collectors.toList());
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java")

        self.assertEqual(result["time_complexity"], "O(n²)")
        self.assertEqual(result["space_complexity"], "O(n²)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "java_nested_stream_pipeline")
        self.assertEqual(result["memory_allocation_analysis"]["auxiliary_space"], "O(n²)")

    def test_java_stream_sorted_pipeline_is_n_log_n(self):
        code = """import java.util.*;

public class Test {
    public static long sortedCount(List<Integer> list) {
        return list.stream().sorted().count();
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java")

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "java_stream_sorted")

    def test_java_treemap_update_inside_linear_recursion_adds_log_factor(self):
        code = """import java.util.*;

public class Test {
    public static void recurse(int n, TreeMap<Integer, Integer> map) {
        if (n <= 0) return;

        map.put(n, n);
        recurse(n - 1, map);
        map.remove(n);
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java", {"n": 10})
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("Recursive ordered map/set update", result["time_complexity_reason"])
        self.assertIn("one or more TreeMap/tree-map updates", result["time_complexity_reason"])
        self.assertIn("one inserted entry per active level", result["space_complexity_reason"])
        self.assertEqual(details["recurse"]["own_complexity"], "O(n log n)")
        self.assertIn("TreeMap/tree-map update", details["recurse"]["reason"])

    def test_route_hides_manual_suggestions_for_treemap_recursion(self):
        code = """import java.util.*;

public class Test {
    public static void recurse(int n, TreeMap<Integer, Integer> map) {
        if (n <= 0) return;

        map.put(n, n);
        recurse(n - 1, map);
        map.remove(n);
    }
}
"""

        def no_grok_rewrite(analysis_result, code_text, language):
            return []

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=no_grok_rewrite):
            result = _analyze_with_extras(code, "Test.java", {"n": 10})

        self.assertEqual(result["time_complexity"], "O(n log n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertEqual(result["optimizations"], [])
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(result["ai_explanation"]["top_optimization"], "")
        self.assertFalse(result["transformed_code"]["available"])
        self.assertFalse(result["ai_transformed_code"]["available"])

    def test_route_strips_nested_loop_static_advice_and_marks_missing_ai_solution(self):
        code = """function jsonTrap(arr: number[]) {
    const set = new Set<string>();

    for (let i = 0; i < arr.length; i++) {
        for (let j = i; j < arr.length; j++) {
            const sub = arr.slice(i, j);
            set.add(JSON.stringify(sub));
        }
    }
}
"""

        def no_ai_rewrite(analysis_result, code_text, language):
            return []

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=no_ai_rewrite):
            result = _analyze_with_extras(code, "jsonTrap.ts")

        self.assertEqual(result["time_complexity"], "O(n³)")
        self.assertTrue(result["issues"])
        issue = result["issues"][0]
        self.assertEqual(issue["message"], "Nested linear loops")
        self.assertIn("ai_solution_status", issue)
        self.assertFalse(result["ai_transformed_code"]["available"])

    def test_route_strips_repeated_dfs_static_advice_and_keeps_ai_status(self):
        code = """import java.util.*;

public class Test {
    static void dfs(int node, List<List<Integer>> g, boolean[] vis) {
        if (vis[node]) return;
        vis[node] = true;

        for (int nei : g.get(node)) {
            dfs(nei, g, vis);
        }
    }

    static void run(List<List<Integer>> g, int n) {
        for (int i = 0; i < n; i++) {
            dfs(i, g, new boolean[n]);
        }
    }
}
"""

        def no_ai_rewrite(analysis_result, code_text, language):
            return []

        with patch("app.routes.enhance_optimizations_with_ai", side_effect=no_ai_rewrite):
            result = _analyze_with_extras(code, "Test.java")

        self.assertEqual(result["time_complexity"], "O(V * (V + E))")
        self.assertEqual(result["space_complexity"], "O(V)")
        self.assertTrue(result["issues"])
        issue = result["issues"][0]
        self.assertEqual(issue["message"], "Repeated DFS from All Nodes (O(V * (V + E)))")
        self.assertIn("ai_solution_status", issue)
        self.assertFalse(result["ai_transformed_code"]["available"])

    def test_java_hashmap_loop_reports_average_and_collision_nuance(self):
        code = """import java.util.*;

public class Test {
    public static void collide(int n) {
        Map<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < n; i++) {
            map.put(i * 16, i); // can cause clustering
        }
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n)")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("Hash table access", result["time_complexity_reason"])
        self.assertIn("average/amortized", result["time_complexity_reason"])
        self.assertIn("treeifies", result["time_complexity_reason"])
        self.assertEqual(result["amortized_analysis"]["pattern"], "hash_table_access")
        self.assertEqual(result["amortized_analysis"]["amortized_per_operation"], "O(1)")
        self.assertEqual(result["amortized_analysis"]["per_operation_worst"], "O(log n)")
        self.assertEqual(result["amortized_analysis"]["worst_total_for_n_ops"], "O(n log n)")
        self.assertIn("collide", details)
        self.assertIn("Hash table access", details["collide"]["reason"])
        self.assertTrue(any("power-of-two" in issue["message"] for issue in result["issues"]))

    def test_cpp_unordered_map_collision_attack_reports_average_and_worst(self):
        code = r"""#include <unordered_map>
using namespace std;

void collisionAttack(int n) {
    unordered_map<int, int> m;
    for (int i = 0; i < n; i++) {
        m[i * 1000003] = i; // crafted keys
    }
}
"""

        result = self.analyzer.analyze(code, "collision.cpp", {"n": 100})
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n) average, O(n²) worst")
        self.assertEqual(result["space_complexity"], "O(n)")
        self.assertIn("Collision-heavy worst-case total time is O(n²)", result["time_complexity_reason"])
        self.assertEqual(result["amortized_analysis"]["total_for_n_ops"], "O(n)")
        self.assertEqual(result["amortized_analysis"]["worst_total_for_n_ops"], "O(n²)")
        self.assertIn("crafted/adversarial", result["issues"][0]["message"])
        self.assertEqual(details["collisionAttack"]["own_complexity"], "O(n) average, O(n²) worst")

    def test_nested_hash_and_object_growth_counts_quadratic_space(self):
        cases = [
            ("dict_growth.py", """def f(n):
    d = {}
    for i in range(n):
        for j in range(n):
            d[(i, j)] = i + j
    return d
"""),
            ("object_growth.js", """function f(n) {
    const obj = {};
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) obj[i + ',' + j] = i + j;
    }
    return obj;
}
"""),
            ("map_growth.ts", """function f(n: number): Map<string, number> {
    const m = new Map<string, number>();
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) m.set(`${i},${j}`, i + j);
    }
    return m;
}
"""),
            ("HashGrowth.java", """import java.util.*;
class A {
    Map<String, Integer> f(int n) {
        Map<String, Integer> m = new HashMap<>();
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) m.put(i + "," + j, i + j);
        }
        return m;
    }
}
"""),
            ("unordered_growth.cpp", r"""#include <string>
#include <unordered_map>
using namespace std;
void f(int n) {
    unordered_map<string, int> m;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) m[to_string(i) + "," + to_string(j)] = i + j;
    }
}
"""),
        ]

        for filename, code in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["time_complexity"], self.analyzer._quadratic())
                self.assertEqual(result["space_complexity"], self.analyzer._quadratic())

    def test_cpp_two_dimensional_vector_allocation_is_quadratic(self):
        code = r"""#include <vector>
using namespace std;

void f(int n) {
    vector<vector<int>> grid(n, vector<int>(n));
}
"""

        result = self.analyzer.analyze(code, "grid.cpp")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], self.analyzer._quadratic())
        self.assertEqual(result["space_complexity"], self.analyzer._quadratic())
        self.assertIn("f", details)
        self.assertNotIn("grid", details)

    def test_java_and_cpp_linear_membership_scans_inside_loop_are_quadratic(self):
        cases = [
            ("Contains.java", """import java.util.*;
class A {
    int f(List<Integer> a, List<Integer> b) {
        int c = 0;
        for (int x : a) {
            if (b.contains(x)) c++;
        }
        return c;
    }
}
"""),
            ("find.cpp", r"""#include <algorithm>
#include <vector>
using namespace std;
int f(vector<int>& a, vector<int>& b) {
    int c = 0;
    for (int x : a) {
        if (find(b.begin(), b.end(), x) != b.end()) c++;
    }
    return c;
}
"""),
        ]

        for filename, code in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["time_complexity"], self.analyzer._quadratic())
                self.assertEqual(result["space_complexity"], "O(1)")

    def test_priority_queue_push_loop_is_n_log_n_and_linear_space(self):
        cases = [
            ("PQ.java", """import java.util.*;
class A {
    void f(int n) {
        PriorityQueue<Integer> pq = new PriorityQueue<>();
        for (int i = 0; i < n; i++) pq.offer(i);
    }
}
"""),
            ("pq.cpp", r"""#include <queue>
using namespace std;
void f(int n) {
    priority_queue<int> pq;
    for (int i = 0; i < n; i++) pq.push(i);
}
"""),
        ]

        for filename, code in cases:
            with self.subTest(filename=filename):
                result = self.analyzer.analyze(code, filename)
                self.assertEqual(result["time_complexity"], "O(n log n)")
                self.assertEqual(result["space_complexity"], "O(n)")

    def test_cpp_vector_string_memo_recursion_reports_conservative_average_and_collision_worst(self):
        code = r"""#include <bits/stdc++.h>
using namespace std;

int nightmare(vector<int> v, unordered_map<string, int>& memo) {
    if (v.size() <= 1) return 1;
    string key = "";
    for (int x : v) key += to_string(x) + ",";
    if (memo.count(key)) return memo[key];
    int mid = v.size() / 2;
    vector<int> left(v.begin(), v.begin() + mid);
    vector<int> right(v.begin() + mid, v.end());
    return memo[key] = nightmare(left, memo) + nightmare(right, memo);
}
"""

        result = self.analyzer.analyze(code, "nightmare.cpp")
        details = {item["function"]: item for item in result["function_complexity_details"]}
        expected = f"{self.analyzer._quadratic()} average, {self.analyzer._cubic()} worst"

        self.assertEqual(result["time_complexity"], expected)
        self.assertEqual(result["space_complexity"], self.analyzer._quadratic())
        self.assertIn("nightmare", details)
        self.assertNotIn("left", details)
        self.assertNotIn("right", details)
        self.assertEqual(details["nightmare"]["own_complexity"], expected)
        self.assertIn("string-key memoization", details["nightmare"]["reason"])
        self.assertNotIn("scalar subproblem", details["nightmare"]["reason"])
        self.assertIn("string-key memoization", result["time_complexity_reason"])

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

    def test_looped_half_recursion_is_quasi_polynomial_and_rewritable(self):
        code = """public class Test {
    public static int tricky(int n) {
        if (n <= 1) return 1;

        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += tricky(n / 2);
        }
        return sum;
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java", {"n": 16})
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n^((log n + 1)/2))")
        self.assertEqual(result["space_complexity"], "O(log n)")
        self.assertIn("T(n)=n*T(n/2)+O(n)", result["time_complexity_reason"])
        self.assertEqual(details["tricky"]["own_complexity"], "O(n^((log n + 1)/2))")
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(log n)")
        self.assertIn("return n * tricky(n / 2);", result["optimizations"][0]["example"])
        self.assertTrue(result["transformed_code"]["available"])
        self.assertIn("time_formula", result["input_effect_analysis"])

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
        self.assertEqual(result["recurrence_analysis"]["method"], "Akra-Bazzi")
        self.assertEqual(result["recurrence_analysis"]["division_factors"], [2, 3])
        self.assertAlmostEqual(result["recurrence_analysis"]["akra_bazzi_exponent"], 0.7879, places=3)

    def test_typescript_mixed_halving_and_quarter_recursion_uses_akra_bazzi(self):
        code = """function insane(n: number): number {
    if (n <= 1) return 1;

    return insane(Math.floor(n / 2)) +
           insane(Math.floor(n / 2)) +
           insane(Math.floor(n / 4));
}
"""

        result = self.analyzer.analyze(code, "insane.ts")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(n^1.272)")
        self.assertEqual(result["space_complexity"], "O(log n)")
        self.assertEqual(result["recurrence_analysis"]["method"], "Akra-Bazzi")
        self.assertEqual(result["recurrence_analysis"]["division_factors"], [2, 2, 4])
        self.assertAlmostEqual(result["recurrence_analysis"]["akra_bazzi_exponent"], 1.2716, places=3)
        self.assertEqual(details["insane"]["own_complexity"], "O(n^1.272)")
        self.assertIn("T(n/4)", result["time_complexity_reason"])

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

    def test_edmonds_karp_known_algorithm_detection_does_not_backtrack(self):
        code = """from collections import deque

def bfs(capacity, source, sink, parent):
    visited = [False] * len(capacity)
    queue = deque([source])
    visited[source] = True
    while queue:
        u = queue.popleft()
        for v, cap in enumerate(capacity[u]):
            if not visited[v] and cap > 0:
                queue.append(v)
                visited[v] = True
                parent[v] = u
                if v == sink:
                    return True
    return False

def edmonds_karp(capacity, source, sink):
    n = len(capacity)
    residual_cap = [[cap for cap in row] for row in capacity]
    parent = [-1] * n
    max_flow = 0
    while bfs(residual_cap, source, sink, parent):
        path_flow = float('Inf')
        s = sink
        while s != source:
            path_flow = min(path_flow, residual_cap[parent[s]][s])
            s = parent[s]
        max_flow += path_flow
        v = sink
        while v != source:
            u = parent[v]
            residual_cap[u][v] -= path_flow
            residual_cap[v][u] += path_flow
            v = parent[v]
    return max_flow
"""

        known = self.analyzer.detect_known_algorithm(code)
        result = self.analyzer.analyze(code, "flow.py")
        functions = [item["function"] for item in result["function_complexity_details"]]

        self.assertFalse(known["detected"])
        self.assertEqual(result["time_complexity"], "O(V E\u00b2)")
        self.assertEqual(result["space_complexity"], "O(V + E)")
        self.assertEqual(functions, ["bfs", "edmonds_karp"])

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
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "repeated_dfs_fresh_visited")
        self.assertEqual(result["overall_complexity"]["total_allocation"], "O(V²)")
        self.assertEqual(result["analysis_confidence"]["time"], "high")
        self.assertIn("fresh visited set", result["time_complexity_reason"])
        self.assertEqual(result["optimizations"][0]["complexity_after"], "O(V + E)")
        self.assertTrue(result["transformed_code"]["available"])

    def test_java_repeated_dfs_with_fresh_boolean_visited_repeats_graph_work(self):
        code = """import java.util.*;

public class Test {
    static void dfs(int node, List<List<Integer>> g, boolean[] vis) {
        if (vis[node]) return;
        vis[node] = true;

        for (int nei : g.get(node)) {
            dfs(nei, g, vis);
        }
    }

    static void run(List<List<Integer>> g, int n) {
        for (int i = 0; i < n; i++) {
            dfs(i, g, new boolean[n]);
        }
    }
}
"""

        result = self.analyzer.analyze(code, "Test.java")
        details = {item["function"]: item for item in result["function_complexity_details"]}

        self.assertEqual(result["time_complexity"], "O(V * (V + E))")
        self.assertEqual(result["space_complexity"], "O(V)")
        self.assertEqual(result["memory_allocation_analysis"]["pattern"], "repeated_dfs_fresh_visited")
        self.assertEqual(result["overall_complexity"]["total_allocation"], "O(V²)")
        self.assertEqual(details["dfs"]["own_complexity"], "O(V + E)")
        self.assertEqual(details["run"]["effective_complexity"], "O(V * (V + E))")
        self.assertEqual(details["run"]["calls"][0]["multiplier"], "O(V)")
        self.assertIn("fresh visited array/set", details["run"]["reason"])

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

    def test_c_mixed_decrement_and_halving_recursion_is_exponential_upper_bound(self):
        code = r"""int fun1(int n) {
    if (n <= 1) return 1;
    return fun1(n / 2) + fun1(n - 1);
}"""

        result = self.analyzer.analyze(code, "fun1.c")

        self.assertEqual(result["time_complexity"], "O(2^n)")
        self.assertIn("T(n)=T(n-1)+T(n/2)", result["time_complexity_reason"])

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

    def test_java_permutation_backtracking_without_storing_results_is_factorial_time_linear_space(self):
        code = """import java.util.*;
public class Perm {
    static void backtrack(List<Integer> nums, List<Integer> path, boolean[] used) {
        if (path.size() == nums.size()) return;
        for (int i = 0; i < nums.size(); i++) {
            if (!used[i]) {
                used[i] = true;
                path.add(nums.get(i));
                backtrack(nums, path, used);
                path.remove(path.size() - 1);
                used[i] = false;
            }
        }
    }
}
"""

        result = self.analyzer.analyze(code, "Perm.java")

        self.assertEqual(result["time_complexity"], "O(n * n!)")
        self.assertEqual(result["space_complexity"], "O(n)")

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

        self.assertEqual(time["complexity"], "O(popcount(n)), worst-case O(log n)")
        self.assertEqual(result["time_complexity"], "O(popcount(n)), worst-case O(log n)")
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
