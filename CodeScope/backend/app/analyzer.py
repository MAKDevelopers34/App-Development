import ast
import re
import math
from collections import defaultdict, deque


# ─────────────────────────────────────────────────────────────────────────────
# CALL GRAPH ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class CallGraphAnalyzer:
    """
    Tracks which functions call which other functions
    and chains their complexities together.
    """

    def __init__(self):
        self.call_graph = defaultdict(set)
        self.func_complexities = {}

    def build_call_graph(self, code, language):
        self.call_graph = defaultdict(set)
        lines = code.split('\n')
        current_func = None

        for line in lines:
            stripped = line.strip()
            func_def = re.match(
                r'(?:def\s+|function\s*\*?\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?'
                r'(?:void|int|long|double|float|boolean|bool|char|String|'
                r'List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|'
                r'Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|'
                r'vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+)(\w+)\s*\(',
                stripped
            )
            if func_def:
                current_func = func_def.group(1)
                self.call_graph[current_func]

            if current_func:
                calls = re.findall(r'\b(\w+)\s*\(', stripped)
                for call in calls:
                    if call != current_func and call not in [
                        'if', 'for', 'while', 'print', 'return',
                        'len', 'range', 'int', 'str', 'list',
                        'dict', 'set', 'tuple', 'sorted', 'type',
                        'isinstance', 'append', 'push', 'pop',
                        'console', 'Math', 'Array', 'Object'
                    ]:
                        self.call_graph[current_func].add(call)

        return self.call_graph

    def compute_chained_complexity(self, func_name, complexities, visited=None):
        if visited is None:
            visited = set()
        if func_name in visited:
            return complexities.get(func_name, 'O(1)')
        visited.add(func_name)
        own = complexities.get(func_name, 'O(1)')
        worst = own
        for called_func in self.call_graph.get(func_name, set()):
            if called_func in complexities:
                child = self.compute_chained_complexity(called_func, complexities, visited)
                worst = self._worse_of(worst, child)
        return worst

    def _worse_of(self, a, b):
        rank = {
            'O(1)': 0, 'O(α(n))': 0.05, 'O(log log n)': 0.5, 'O(log n)': 1,
            'O(log² n)': 2, 'O(log³ n)': 2.2, 'O(√n)': 2.5,
            'O(n)': 3, 'O(n log log n)': 3.5, 'O(n log n)': 4, 'O(n log² n)': 5,
            'O(n^1.585)': 5.5,
            'O(n²)': 6, 'O(n² log n)': 7, 'O(n^2.807)': 7.5, 'O(n³)': 8,
            'O(n³ log n)': 8.2,
            'O((log n)!)': 8.5, 'O(n^((log n + 1)/2))': 8.6, 'O(n^log n)': 8.7,
            'O(φⁿ)': 8.9,
            'O(2ⁿ)': 9, 'O(2^n)': 9, 'O(n * 2^n)': 9.2, 'O(3ⁿ)': 10, 'O(3^n)': 10,
            'O(n!)': 11, 'O(n * n!)': 11.5,
            'O(A(m, n))': 12,
            'O((V + E) log V)': 4, 'O(V + E)': 3,
            'O(V × E)': 6, 'O(V * (V + E))': 7.5, 'O(V E²)': 7, 'O(V³)': 8,
        }
        return a if rank.get(a, 3) >= rank.get(b, 3) else b

    def get_call_chain_report(self, code, func_complexities, language, own_complexities=None):
        self.build_call_graph(code, language)
        own_complexities = own_complexities or func_complexities
        report = []
        for func, calls in self.call_graph.items():
            if not calls:
                continue
            own = own_complexities.get(func, func_complexities.get(func, 'O(1)'))
            chained = func_complexities.get(func, own)
            if chained != own:
                call_summaries = [
                    f"{called}() at {func_complexities.get(called, own_complexities.get(called, 'O(1)'))}"
                    for called in sorted(calls)
                    if called in func_complexities or called in own_complexities
                ]
                chain_path = self._find_chain_path(func, func_complexities, chained)
                if chain_path == func and call_summaries:
                    chain_path = f"{func} -> " + ', '.join(summary.split(' at ', 1)[0] for summary in call_summaries)
                helper_text = f" It calls {', '.join(call_summaries)}." if call_summaries else ''
                report.append({
                    'function': func,
                    'own_complexity': own,
                    'effective_complexity': chained,
                    'chain': chain_path,
                    'message': (
                        f"'{func}' has own/control complexity {own}; helper calls make "
                        f"'{chain_path}' which is {chained} — "
                        f"effective complexity is {chained}.{helper_text}"
                    )
                })
        return report

    def _find_chain_path(self, func, complexities, target_complexity):
        visited = set()
        queue = deque([(func, [func])])
        while queue:
            current, path = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if complexities.get(current) == target_complexity and current != func:
                return ' → '.join(path)
            for called in self.call_graph.get(current, set()):
                if called not in visited:
                    queue.append((called, path + [called]))
        return func


# ─────────────────────────────────────────────────────────────────────────────
# MASTER THEOREM ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class MasterTheoremEngine:
    """
    Proper 3-case Master Theorem + extended case for log-multiplied f(n).
    T(n) = a*T(n/b) + f(n)
    """

    def solve(self, a, b, f_type, f_power=1):
        """
        a       = number of subproblems
        b       = factor by which problem shrinks
        f_type  = 'const'|'log'|'sqrt'|'n'|'n_log'|'n2_log'|'n3_log'
        f_power = exponent on n for polynomial f(n)
        Returns (complexity_string, theorem_case, reason)
        """
        if a <= 0 or b <= 1:
            return 'O(f(n))', 0, 'degenerate recurrence'

        log_b_a = math.log(a, b)
        f_degree = self._f_degree(f_type, f_power)
        eps = 0.001

        # Case 1: f(n) = O(n^(log_b_a - ε))  →  T(n) = Θ(n^log_b_a)
        if f_degree < log_b_a - eps:
            return self._fmt_poly(log_b_a), 1, (
                f'Master Theorem Case 1: log_{b}({a})≈{log_b_a:.4f}, '
                f'f(n)=O(n^{f_degree:.3f}) is polynomially smaller → T(n)=Θ(n^{log_b_a:.4f})'
            )

        # Case 2 extended: f(n) = Θ(n^log_b_a * log^k n)
        if abs(f_degree - log_b_a) <= eps:
            if f_type in ('n_log', 'n2_log', 'n3_log', 'log'):
                return self._fmt_poly_log2(log_b_a), 2, (
                    f'Master Theorem Case 2 (extended): f(n)=Θ(n^{log_b_a:.3f} log n) → T(n)=Θ(n^{log_b_a:.3f} log² n)'
                )
            return self._fmt_poly_log(log_b_a), 2, (
                f'Master Theorem Case 2: log_{b}({a})≈{log_b_a:.4f}, '
                f'f(n)=Θ(n^{log_b_a:.4f}) → T(n)=Θ(n^{log_b_a:.4f} log n)'
            )

        # Case 3: f(n) = Ω(n^(log_b_a + ε))  →  T(n) = Θ(f(n))
        if f_degree > log_b_a + eps:
            return self._fmt_f(f_type, f_power), 3, (
                f'Master Theorem Case 3: log_{b}({a})≈{log_b_a:.4f}, '
                f'f(n)=Ω(n^{f_degree:.3f}) is polynomially larger → T(n)=Θ(f(n))'
            )

        return self._fmt_f(f_type, f_power), 0, 'borderline — no clean Master Theorem classification'

    def _f_degree(self, f_type, f_power):
        mapping = {
            'const': 0, 'log': 0.001,
            'sqrt': 0.5,
            'n': float(f_power),
            'n_log': float(f_power) + 0.0001,
            'n2_log': 2.0001, 'n3_log': 3.0001,
        }
        return mapping.get(f_type, float(f_power))

    def _fmt_poly(self, exp):
        exp_r = round(exp, 4)
        if abs(exp_r - round(exp_r)) < 0.001:
            ei = round(exp_r)
            if ei == 0: return 'O(1)'
            if ei == 1: return 'O(n)'
            if ei == 2: return 'O(n²)'
            if ei == 3: return 'O(n³)'
            return f'O(n^{ei})'
        s = f'{exp_r:.3f}'.rstrip('0').rstrip('.')
        return f'O(n^{s})'

    def _fmt_poly_log(self, exp):
        base = self._fmt_poly(exp)
        if base == 'O(1)': return 'O(log n)'
        if base == 'O(n)': return 'O(n log n)'
        if base == 'O(n²)': return 'O(n² log n)'
        if base == 'O(n³)': return 'O(n³ log n)'
        return base.rstrip(')') + ' log n)'

    def _fmt_poly_log2(self, exp):
        base = self._fmt_poly(exp)
        if base == 'O(1)': return 'O(log² n)'
        if base == 'O(n)': return 'O(n log² n)'
        return base.rstrip(')') + ' log² n)'

    def _fmt_f(self, f_type, f_power):
        mapping = {
            'const': 'O(1)', 'log': 'O(log n)', 'sqrt': 'O(√n)',
            'n': {1: 'O(n)', 2: 'O(n²)', 3: 'O(n³)'}.get(f_power, f'O(n^{f_power})'),
            'n_log': 'O(n log n)', 'n2_log': 'O(n² log n)', 'n3_log': 'O(n³ log n)',
        }
        return mapping.get(f_type, f'O(n^{f_power})')


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CODE ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class CodeAnalyzer:
    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'c']
        self.call_graph_analyzer = CallGraphAnalyzer()
        self.master_theorem = MasterTheoremEngine()
        self.last_func_complexities = {}
        self.last_func_own_complexities = {}
        self.last_func_complexity_details = {}
        self._python_function_cache = {}
        self._python_function_node_cache = {}
        self._function_body_cache = {}
        self._function_line_cache = {}
        self._function_snippet_cache = {}
        self._call_context_cache = {}
        self._repeated_fresh_search_cache = {}
        self._function_special_cache = {}
        self._compact_ws_cache = {}

    def _function_def_regex(self):
        return (
            r'(?:def\s+|function\s*\*?\s+|(?:const|let|var)\s+|'
            r'(?:(?:public|private|protected)\s+)?(?:static\s+)?'
            r'(?:void|int|long|double|float|boolean|bool|char|String|'
            r'List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|'
            r'Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|'
            r'vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+)'
            r'(\w+)\s*(?:=\s*)?\('
        )

    def _function_names(self, code, language=None):
        if language == 'python':
            names = []
            seen = set()
            for node in self._python_function_nodes(code):
                if node.name not in seen:
                    seen.add(node.name)
                    names.append(node.name)
            return names

        names = []
        seen = set()
        for match in re.finditer(self._function_def_regex(), code):
            name = match.group(1)
            if self._is_non_function_signature_match(code, match, language):
                continue
            if name not in seen:
                seen.add(name)
                names.append(name)
        for item in self._javascript_synthetic_functions(code, language):
            name = item.get('name')
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return names

    def _javascript_synthetic_functions(self, code, language=None):
        if not self._is_javascript_like(language):
            return []

        text = str(code or '')
        if not text:
            return []

        patterns = [
            re.compile(
                r'\.addEventListener\s*\(\s*([\'"])(?P<event>[^\'"]+)\1\s*,\s*'
                r'(?P<prefix>function\s*(?:[A-Za-z_$][\w$]*)?\s*\([^)]*\)\s*\{)',
                re.MULTILINE,
            ),
            re.compile(
                r'\.addEventListener\s*\(\s*([\'"])(?P<event>[^\'"]+)\1\s*,\s*'
                r'(?P<prefix>(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{)',
                re.MULTILINE,
            ),
        ]

        items = []
        used = set()
        for pattern in patterns:
            for match in pattern.finditer(text):
                open_brace = text.find('{', match.start('prefix'), match.end('prefix'))
                if open_brace < 0:
                    continue
                close_brace = self._matching_brace_index(text, open_brace)
                if close_brace < 0:
                    continue

                start = text.rfind('\n', 0, match.start()) + 1
                end = close_brace + 1
                while end < len(text) and text[end].isspace():
                    end += 1
                while end < len(text) and text[end] in ');':
                    end += 1

                event = re.sub(r'\W+', '_', match.group('event').strip().lower()).strip('_') or 'event'
                base_name = f'{event}_handler'
                name = base_name
                suffix = 2
                while name in used:
                    name = f'{base_name}_{suffix}'
                    suffix += 1
                used.add(name)

                items.append({
                    'name': name,
                    'line': text.count('\n', 0, start) + 1,
                    'snippet': text[start:end].strip(),
                    'body': self._brace_code_to_indented_lines(text[open_brace + 1:close_brace]),
                })

        return items

    def _javascript_synthetic_function(self, code, func_name, language=None):
        for item in self._javascript_synthetic_functions(code, language):
            if item.get('name') == func_name:
                return item
        return None

    def _matching_brace_index(self, code, open_brace):
        if open_brace < 0 or open_brace >= len(code) or code[open_brace] != '{':
            return -1
        depth = 0
        quote = None
        escape = False
        for index in range(open_brace, len(code)):
            char = code[index]
            if quote:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == quote:
                    quote = None
                continue
            if char in ('"', "'", '`'):
                quote = char
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return index
        return -1

    def _python_function_nodes(self, code):
        text = str(code or '')
        if text in self._python_function_cache:
            return self._python_function_cache[text]

        try:
            tree = ast.parse(text)
        except SyntaxError:
            self._python_function_cache[text] = []
            return []
        nodes = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self._python_function_cache[text] = sorted(
            nodes,
            key=lambda node: (getattr(node, 'lineno', 0), getattr(node, 'col_offset', 0))
        )
        return self._python_function_cache[text]

    def _python_function_node(self, code, func_name, line=None):
        cache_key = (str(code or ''), str(func_name or ''), int(line or 0))
        if cache_key in self._python_function_node_cache:
            return self._python_function_node_cache[cache_key]

        candidates = [
            node for node in self._python_function_nodes(code)
            if node.name == func_name
        ]
        if not candidates:
            self._python_function_node_cache[cache_key] = None
            return None
        if line:
            for node in candidates:
                if getattr(node, 'lineno', 0) == line:
                    self._python_function_node_cache[cache_key] = node
                    return node
        self._python_function_node_cache[cache_key] = candidates[0]
        return candidates[0]

    def _python_function_source(self, code, node, include_header=True):
        if not node:
            return ''
        lines = str(code or '').split('\n')
        start_line = max(1, getattr(node, 'lineno', 1))
        end_line = max(start_line, getattr(node, 'end_lineno', start_line))
        if include_header:
            return '\n'.join(lines[start_line - 1:end_line]).strip()

        if not getattr(node, 'body', None):
            return ''
        body_start = max(1, getattr(node.body[0], 'lineno', start_line))
        if body_start == start_line:
            header_line = lines[start_line - 1] if start_line - 1 < len(lines) else ''
            colon_index = header_line.find(':')
            return header_line[colon_index + 1:].strip() if colon_index >= 0 else ''
        return '\n'.join(lines[body_start - 1:end_line]).strip()

    def _class_names(self, code, language=None):
        patterns = []
        if language in (None, 'python', 'unknown'):
            patterns.append(r'^\s*class\s+([A-Za-z_]\w*)\b')
        if language in (None, 'javascript', 'typescript', 'java', 'cpp', 'c', 'unknown'):
            patterns.append(r'^\s*(?:export\s+)?class\s+([A-Za-z_]\w*)\b')

        names = []
        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def _strip_string_literals(self, code):
        return re.sub(
            r'(?s)(?:[rubfRUBF]{0,3}"""(?:\\.|(?!""").)*"""|'
            r"[rubfRUBF]{0,3}'''(?:\\.|(?!''').)*'''|"
            r'[rubfRUBF]{0,3}"(?:\\.|[^"\\])*"|'
            r"[rubfRUBF]{0,3}'(?:\\.|[^'\\])*')",
            '""',
            str(code or ''),
        )

    def _compact_ws(self, code):
        text = str(code or '')
        if text not in self._compact_ws_cache:
            self._compact_ws_cache[text] = re.sub(r'\s+', ' ', text)
        return self._compact_ws_cache[text]

    def _has_explicit_loop_statement(self, code):
        return any(re.match(r'\s*(?:for|while)\b', line) for line in str(code or '').splitlines())

    def _mask_known_call_names(self, code, names):
        masked = str(code or '')
        for name in sorted((names or []), key=len, reverse=True):
            if not name:
                continue
            masked = re.sub(rf'\b{re.escape(name)}\s*(?=\()', 'local_call', masked)
        return masked

    def _is_non_function_signature_match(self, code, match, language=None):
        language = language or 'unknown'
        line_start = code.rfind('\n', 0, match.start()) + 1
        line_end = code.find('\n', match.start())
        if line_end == -1:
            line_end = len(code)
        line = code[line_start:line_end].strip()
        if language in ('cpp', 'c', 'java', 'unknown'):
            if '=' in match.group(0):
                return True
            after_signature = self._next_nonspace_after_matching_paren(code, match.end() - 1)
            if after_signature == ';' and '{' in code[line_start:match.start()]:
                return True
            if ';' in line and '{' not in line and '=>' not in line:
                return True
        return False

    def _next_nonspace_after_matching_paren(self, code, open_index):
        if open_index < 0 or open_index >= len(code) or code[open_index] != '(':
            return ''
        depth = 0
        for index in range(open_index, len(code)):
            char = code[index]
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    next_index = index + 1
                    while next_index < len(code) and code[next_index].isspace():
                        next_index += 1
                    return code[next_index] if next_index < len(code) else ''
        return ''

    def _is_javascript_like(self, language):
        return language in ('javascript', 'typescript')

    def detect_language(self, code, filename=None):
        if filename:
            ext = filename.split('.')[-1].lower()
            lang_map = {
                'py': 'python', 'pyw': 'python',
                'js': 'javascript', 'jsx': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
                'ts': 'typescript', 'tsx': 'typescript', 'mts': 'typescript', 'cts': 'typescript',
                'java': 'java',
                'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'c++': 'cpp',
                'hpp': 'cpp', 'hh': 'cpp', 'hxx': 'cpp', 'ipp': 'cpp',
                'c': 'c', 'h': 'c'
            }
            detected = lang_map.get(ext)
            if detected:
                return detected
        return self._detect_language_from_content(code)

    def _detect_language_from_content(self, code):
        text = str(code or '')
        if not text.strip():
            return 'unknown'

        if re.search(r'^\s*(?:from\s+[\w.]+\s+import|import\s+[\w., ]+)\b', text, re.MULTILINE):
            if re.search(r'^\s*(?:async\s+)?def\s+\w+\s*\([^)]*\)\s*:', text, re.MULTILINE):
                return 'python'
        if re.search(r'^\s*(?:async\s+)?def\s+\w+\s*\([^)]*\)\s*:', text, re.MULTILINE):
            return 'python'
        if re.search(r'^\s*class\s+\w+(?:\([^)]*\))?\s*:', text, re.MULTILINE):
            return 'python'
        if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', text):
            return 'python'

        if re.search(r'\bpublic\s+class\s+\w+|\bSystem\.out\.println\s*\(|\bpublic\s+static\s+void\s+main\s*\(', text):
            return 'java'
        if re.search(r'^\s*#\s*include\b|\bstd::|\bcout\s*<<|\bint\s+main\s*\(', text, re.MULTILINE):
            return 'cpp'
        if re.search(r'\binterface\s+\w+|\btype\s+\w+\s*=|:\s*(?:string|number|boolean|Array<|[A-Z]\w*(?:\[\])?)\s*[=,)]', text):
            return 'typescript'
        if re.search(r'\bfunction\s+\w+\s*\(|(?:const|let|var)\s+\w+\s*=\s*(?:\([^)]*\)|\w+)\s*=>|\bconsole\.log\s*\(', text):
            return 'javascript'

        return 'unknown'

    def analyze(self, code, filename=None, concrete_inputs=None):
        self._function_body_cache = {}
        self._function_line_cache = {}
        self._function_snippet_cache = {}
        self._call_context_cache = {}
        self._repeated_fresh_search_cache = {}
        self._function_special_cache = {}
        self._compact_ws_cache = {}
        language = self.detect_language(code, filename)
        input_schema = self.infer_input_schema(code, language)
        self.last_func_complexities = self._extract_all_function_complexities(code, language)
        self.last_func_complexity_details = self._build_function_complexity_details(
            code, language, self.last_func_own_complexities, self.last_func_complexities
        )
        time_result = self.detect_time_complexity(code, language)
        if self.last_func_complexities:
            function_worst = self._max_complexity(self.last_func_complexities.values())
            current_rank = self._complexity_rank(self._parse_complexity_string(time_result['complexity']))
            function_rank = self._complexity_rank(self._parse_complexity_string(function_worst))
            if (
                function_rank > current_rank or
                (
                    function_rank == current_rank and
                    self._has_contextual_complexity_label(function_worst) and
                    function_worst != time_result['complexity']
                )
            ):
                detail_reason = ''
                for item in self.last_func_complexity_details.values():
                    if item.get('effective_complexity') == function_worst:
                        detail_reason = item.get('reason', '')
                        break
                reason_suffix = f" | Function/call-chain analysis: {function_worst}"
                if detail_reason:
                    reason_suffix += f" ({detail_reason})"
                time_result = {
                    **time_result,
                    'complexity': function_worst,
                    'reason': f"{time_result['reason']}{reason_suffix}"
                }
        space = self.detect_space_complexity(code, language)
        if self.last_func_complexity_details:
            function_spaces = [
                item.get('effective_space_complexity') or item.get('space_complexity')
                for item in self.last_func_complexity_details.values()
                if item.get('effective_space_complexity') or item.get('space_complexity')
            ]
            if function_spaces:
                function_worst_space = self._max_complexity(function_spaces)
                current_space_rank = self._complexity_rank(self._parse_complexity_string(space))
                function_space_rank = self._complexity_rank(self._parse_complexity_string(function_worst_space))
                if function_space_rank > current_space_rank:
                    space = function_worst_space
        memory_analysis = self.detect_memory_allocation_complexity(code, language, space, time_result)
        space_reason = self.explain_space_complexity(code, language, space, memory_analysis)
        issues = self.detect_issues(code, language)
        optimizations = self.generate_optimizations(code, language, time_result)
        transformed = self.generate_transformed_code(code, language, time_result)
        concrete = self.detect_concrete_analysis(code, language, concrete_inputs)
        input_effect = self.estimate_input_effect(
            code, language, concrete_inputs, input_schema,
            time_result['complexity'], space
        )
        amortized = self.explain_amortized_complexity(code, language)
        recurrence_analysis = self._build_recurrence_analysis(time_result)
        semantic_analysis = self.analyze_semantic_assumptions(
            code, language, input_schema, concrete_inputs, time_result, memory_analysis
        )

        result = {
            'language': language,
            'time_complexity': time_result['complexity'],
            'time_complexity_reason': time_result['reason'],
            'space_complexity': space,
            'space_complexity_reason': space_reason,
            'issues': issues,
            'suggestions': [],
            'optimizations': optimizations,
            'transformed_code': transformed,
            'rating': 0,
            'lines_of_code': len(code.strip().split('\n')),
            'input_schema': input_schema,
            'function_complexity_details': list(self.last_func_complexity_details.values()),
            'memory_allocation_analysis': memory_analysis,
            'analysis_confidence': self._analysis_confidence_summary(code, language, time_result),
            'semantic_analysis': semantic_analysis,
            'overall_complexity': self.build_overall_complexity_summary(
                time_result['complexity'], space, memory_analysis
            ),
            'hotspots': self._build_hotspots(self.last_func_complexity_details),
        }
        if recurrence_analysis:
            result['recurrence_analysis'] = recurrence_analysis
        if concrete_inputs:
            result['provided_inputs'] = concrete_inputs
        if input_effect:
            result['input_effect_analysis'] = input_effect
        if concrete:
            result['concrete_analysis'] = concrete
        else:
            fixed_entrypoint = self._detect_fixed_entrypoint_literal_analysis(
                code,
                language,
                result['time_complexity'],
                result['space_complexity'],
            )
            if fixed_entrypoint:
                result['concrete_analysis'] = fixed_entrypoint
                self._apply_fixed_entrypoint_overall(result, fixed_entrypoint)
        if amortized:
            result['amortized_analysis'] = amortized
        result['suggestions'] = self.generate_suggestions(result)
        result['rating'] = self.calculate_rating(result)
        return result

    # ─────────────────────────────────────────────
    # INPUT SCHEMA INFERENCE
    # ─────────────────────────────────────────────

    def infer_input_schema(self, code, language=None):
        language = language or self.detect_language(code)
        signature = self._primary_function_signature(code, language)
        if not signature:
            return {
                'available': False, 'language': language,
                'function': None, 'parameters': [],
                'reason': 'No function parameters detected'
            }
        parameters = []
        for param in signature['params']:
            name = param.get('name', '')
            if name in ('self', 'cls') or not name:
                continue
            inferred = self._infer_parameter_kind(param, code)
            parameters.append({
                'name': name,
                'declared_type': param.get('declared_type', ''),
                'kind': inferred['kind'],
                'placeholder': inferred['placeholder'],
                'example': inferred['example'],
            })
        return {
            'available': bool(parameters),
            'language': language,
            'function': signature['name'],
            'parameters': parameters,
            'example': ', '.join(f"{p['name']}={p['example']}" for p in parameters),
            'reason': 'Detected from function signature'
        }

    def _primary_function_signature(self, code, language):
        if language == 'python':
            try:
                tree = ast.parse(code)
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        return {
                            'name': node.name,
                            'params': [self._python_ast_param(arg) for arg in node.args.args]
                        }
            except SyntaxError:
                pass
            match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
            if match:
                return {
                    'name': match.group(1),
                    'params': self._parse_signature_params(match.group(2), language)
                }
            return None

        if self._is_javascript_like(language):
            patterns = [
                r'function\s*\*?\s+(\w+)\s*\(([^)]*)\)',
                r'(?:const|let|var)\s+(\w+)\s*=\s*\(([^)]*)\)\s*(?::\s*[\w<>\[\], |]+)?\s*=>',
                r'(?:const|let|var)\s+(\w+)\s*=\s*([A-Za-z_]\w*)\s*=>',
            ]
            for pattern in patterns:
                match = re.search(pattern, code)
                if match:
                    return {
                        'name': match.group(1),
                        'params': self._parse_signature_params(match.group(2), language)
                    }
            return None

        match = re.search(
            r'(?:public|private|protected)?\s*(?:static\s+)?'
            r'(?:[\w:<>\[\], ?&*]+\s+)'
            r'(\w+)\s*\(([^)]*)\)', code
        )
        if match:
            name = match.group(1)
            if name in ('if', 'for', 'while', 'switch', 'catch'):
                return None
            return {
                'name': name,
                'params': self._parse_signature_params(match.group(2), language)
            }
        return None

    def _python_ast_param(self, arg):
        declared = ''
        if arg.annotation:
            try:
                declared = ast.unparse(arg.annotation)
            except Exception:
                declared = ''
        return {'name': arg.arg, 'declared_type': declared}

    def _parse_signature_params(self, raw_params, language):
        params = []
        for raw in self._split_params(raw_params):
            original = raw.strip()
            if not original:
                continue
            cleaned = re.sub(r'=.*$', '', original).strip()
            if not cleaned:
                continue
            if language == 'python':
                name_part = cleaned.split(':', 1)[0].strip()
                declared = cleaned.split(':', 1)[1].strip() if ':' in cleaned else ''
                name = re.sub(r'^[*]+', '', name_part).strip()
                params.append({'name': name, 'declared_type': declared})
                continue
            if language == 'typescript' and ':' in cleaned:
                name_part, declared = cleaned.split(':', 1)
                name = re.sub(r'^[*]+', '', name_part).strip()
                params.append({'name': name, 'declared_type': declared.strip()})
                continue
            tokens = cleaned.replace('&', ' ').replace('*', ' ').split()
            if not tokens:
                continue
            name = tokens[-1].replace('[]', '').strip()
            declared = cleaned[:cleaned.rfind(tokens[-1])].strip() if len(tokens) > 1 else ''
            array_suffix = re.search(r'(\w+)\s*\[\s*\]$', cleaned)
            if array_suffix:
                name = array_suffix.group(1)
                declared = cleaned[:array_suffix.start(1)].strip() + '[]'
            params.append({'name': name, 'declared_type': declared})
        return params

    def _split_params(self, raw_params):
        params, current = [], []
        depth = 0
        pairs = {'<': '>', '[': ']', '(': ')', '{': '}'}
        closers = set(pairs.values())
        for char in raw_params:
            if char in pairs:
                depth += 1
            elif char in closers and depth > 0:
                depth -= 1
            if char == ',' and depth == 0:
                params.append(''.join(current))
                current = []
            else:
                current.append(char)
        if current:
            params.append(''.join(current))
        return params

    def _infer_parameter_kind(self, param, code):
        name = param.get('name', '')
        declared = (param.get('declared_type') or '').lower()
        lname = name.lower()
        combined = f'{declared} {lname}'
        if any(token in combined for token in ['bool', 'boolean', 'flag', 'is_', 'has_', 'can_']):
            return {'kind': 'boolean', 'placeholder': 'true', 'example': 'true'}
        if any(token in combined for token in ['list', 'array', 'vector', '[]', 'tuple', 'set']) or lname in {
            'arr', 'nums', 'numbers', 'items', 'values', 'list', 'array', 'visited', 'seen'
        }:
            return {'kind': 'array', 'placeholder': '[1, 2, 3]', 'example': '[1, 2, 3]'}
        if any(token in combined for token in ['dict', 'map', 'object', 'graph', 'adj']):
            return {'kind': 'object', 'placeholder': '{"a": [1, 2]}', 'example': '{"a": [1, 2]}'}
        if any(token in combined for token in ['str', 'string', 'char']) or lname in {'s', 'text', 'word', 'pattern'}:
            return {'kind': 'string', 'placeholder': 'hello', 'example': '"hello"'}
        if any(token in combined for token in ['float', 'double', 'decimal']):
            return {'kind': 'number', 'placeholder': '3.14', 'example': '3.14'}
        if (
            any(token in combined for token in ['int', 'long', 'size_t', 'short']) or
            lname in {'n', 'm', 'k', 'i', 'j', 'target', 'size', 'length', 'count', 'limit'}
        ):
            return {'kind': 'integer', 'placeholder': '10', 'example': '10'}
        return {'kind': 'string', 'placeholder': 'value', 'example': '"value"'}

    # ─────────────────────────────────────────────
    # INPUT EFFECT ESTIMATION
    # ─────────────────────────────────────────────

    def estimate_input_effect(self, code, language, concrete_inputs, input_schema, time_complexity, space_complexity):
        if concrete_inputs in (None, '', {}, []):
            return None
        sizes = self._extract_input_sizes(concrete_inputs, input_schema)
        if not sizes.get('dimensions') and not sizes.get('graph'):
            return {
                'available': False,
                'kind': 'input_effect_estimate',
                'reason': 'No usable size (n, array length, string length, V, or E) could be inferred.'
            }
        time_estimate = self._estimate_complexity_units(time_complexity, sizes)
        space_estimate = self._estimate_complexity_units(space_complexity, sizes)
        dominant_n = self._dominant_input_size(sizes)
        return {
            'available': bool(time_estimate.get('available')),
            'kind': 'input_effect_estimate',
            'input_sizes': sizes,
            'dominant_size': dominant_n,
            'time_complexity': time_complexity,
            'space_complexity': space_complexity,
            'estimated_time_units': time_estimate.get('display'),
            'estimated_space_units': space_estimate.get('display'),
            'time_formula': time_estimate.get('formula'),
            'space_formula': space_estimate.get('formula'),
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'reason': (
                'Inputs used to estimate workload from detected Big-O. '
                'For fixed values the run is finite/O(1).'
            )
        }

    def _extract_input_sizes(self, concrete_inputs, input_schema=None):
        dimensions = {}
        value_inputs = {}
        graph = {}

        def add_dimension(name, value):
            parsed = self._positive_number(value)
            if parsed is not None:
                dimensions[name] = parsed

        def visit(name, value):
            lname = str(name or 'input').lower()
            if isinstance(value, dict):
                graph_info = self._graph_size_from_value(value)
                if graph_info and (lname in {'graph', 'adj', 'adjacency'} or self._looks_like_graph_value(value)):
                    graph.update(graph_info)
                    dimensions[name or 'graph'] = graph_info['V']
                    return
                dimensions[name or 'object'] = max(1, len(value))
                for child_name, child_value in value.items():
                    if isinstance(child_value, (list, tuple, set, dict, str)):
                        visit(child_name, child_value)
                return
            if isinstance(value, (list, tuple, set)):
                dimensions[name or 'array'] = len(value)
                return
            if isinstance(value, str):
                stripped = value.strip()
                number = self._positive_number(stripped)
                if number is not None:
                    if self._is_size_name(lname):
                        add_dimension(name, number)
                    else:
                        value_inputs[name] = number
                else:
                    dimensions[name or 'string'] = len(value)
                return
            if self._is_size_name(lname):
                add_dimension(name, value)
            else:
                parsed = self._positive_number(value)
                if parsed is not None:
                    value_inputs[name] = parsed

        if isinstance(concrete_inputs, dict):
            schema_func = (input_schema or {}).get('function')
            data = concrete_inputs.get(schema_func) if schema_func and isinstance(concrete_inputs.get(schema_func), dict) else concrete_inputs
            for key, value in data.items():
                visit(key, value)
        elif isinstance(concrete_inputs, (list, tuple)):
            for index, value in enumerate(concrete_inputs):
                visit(f'arg{index + 1}', value)
        elif isinstance(concrete_inputs, str):
            named = re.findall(r'\b([A-Za-z_]\w*)\s*[:=]\s*([^,]+)', concrete_inputs)
            if named:
                for key, raw in named:
                    visit(key, raw.strip())
            else:
                numbers = re.findall(r'-?\d+(?:\.\d+)?', concrete_inputs)
                for index, value in enumerate(numbers):
                    visit('n' if index == 0 else f'arg{index + 1}', value)

        if not dimensions and value_inputs:
            best_name, best_value = max(value_inputs.items(), key=lambda item: item[1])
            dimensions[best_name] = best_value

        return {'dimensions': dimensions, 'value_inputs': value_inputs, 'graph': graph}

    def _is_size_name(self, name):
        return str(name or '').lower() in {
            'n', 'm', 'k', 'v', 'e', 'q', 'rows', 'cols', 'row', 'col',
            'size', 'length', 'len', 'limit', 'capacity', 'vertices', 'edges',
            'height', 'width', 'depth'
        }

    def _positive_number(self, value):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed < 0:
            return None
        if parsed.is_integer():
            return int(parsed)
        return parsed

    def _looks_like_graph_value(self, value):
        if not isinstance(value, dict) or not value:
            return False
        return all(isinstance(v, (list, tuple, set)) for v in value.values())

    def _graph_size_from_value(self, value):
        if isinstance(value, dict) and self._looks_like_graph_value(value):
            return {'V': len(value), 'E': sum(len(neighbors) for neighbors in value.values())}
        if isinstance(value, list) and all(isinstance(v, (list, tuple, set)) for v in value):
            return {'V': len(value), 'E': sum(len(neighbors) for neighbors in value)}
        return None

    def _dominant_input_size(self, sizes):
        graph = sizes.get('graph') or {}
        if graph:
            return max(1, graph.get('V', 1), graph.get('E', 1))
        dims = sizes.get('dimensions') or {}
        if not dims:
            return 1
        return max(max(dims.values()), 1)

    def _named_or_ranked_size(self, sizes, names, rank):
        dims = sizes.get('dimensions') or {}
        for name in names:
            if name in dims:
                return max(1, dims[name])
        ordered = sorted(dims.values(), reverse=True)
        if len(ordered) > rank:
            return max(1, ordered[rank])
        return self._dominant_input_size(sizes)

    def _estimate_complexity_units(self, complexity, sizes):
        text = self._normalized_complexity_text(complexity)
        graph = sizes.get('graph') or {}
        n = max(1, self._dominant_input_size(sizes))
        m = max(1, self._named_or_ranked_size(sizes, {'m', 'cols', 'width'}, 1))
        log_n = max(1, math.log2(max(2, n)))
        log_log_n = max(1, math.log2(max(2, log_n)))

        if graph:
            v = max(1, graph.get('V', n))
            e = max(0, graph.get('E', 0))
            log_v = max(1, math.log2(max(2, v)))
            if text == 'O(V)':
                return self._estimate_payload(v, f'V = {v}')
            if text == 'O(E)':
                return self._estimate_payload(e, f'E = {e}')
            if text == 'O(V + E)':
                return self._estimate_payload(v + e, f'V + E = {v} + {e}')
            if text == 'O((V + E) log V)':
                return self._estimate_payload((v + e) * log_v, f'(V+E)logV = ({v}+{e})*log2({v})')
            if text == 'O(V x E)':
                return self._estimate_payload(v * e, f'V*E = {v}*{e}')
            if text in ('O(V * (V + E))', 'O(V x (V + E))'):
                return self._estimate_payload(v * (v + e), f'V*(V+E) = {v}*({v}+{e})')
            if text == 'O(V^2)':
                return self._estimate_payload(v ** 2, f'V^2 = {v}^2')
            if text == 'O(V^3)':
                return self._estimate_payload(v ** 3, f'V^3 = {v}^3')
            if text == 'O(V E^2)':
                return self._estimate_payload(v * (e ** 2), f'V*E^2 = {v}*{e}^2')

        if 'n^2.807' in text or '2.807' in text:
            return self._estimate_payload(n ** 2.807, f'n^2.807 ≈ {n}^2.807')
        fractional = re.fullmatch(r'O\(n\^([0-9]+(?:\.[0-9]+)?)\)', text)
        if fractional:
            exponent = float(fractional.group(1))
            return self._estimate_payload(n ** exponent, f'{n}^{exponent:g}')

        formulas = [
            ('O(1)', 1, '1'),
            ('O(alpha(n))', 1, 'α(n) ≈ 1 (inverse Ackermann)'),
            ('O(log log n)', log_log_n, f'log2(log2({n}))'),
            ('O(log n)', log_n, f'log2({n})'),
            ('O(log^2 n)', log_n ** 2, f'log2({n})^2'),
            ('O(log^3 n)', log_n ** 3, f'log2({n})^3'),
            ('O(log^4 n)', log_n ** 4, f'log2({n})^4'),
            ('O(sqrt(n))', math.sqrt(n), f'sqrt({n})'),
            ('O(n)', n, f'n = {n}'),
            ('O(n log log n)', n * log_log_n, f'{n}*log2(log2({n}))'),
            ('O(n log n)', n * log_n, f'{n}*log2({n})'),
            ('O(n log^2 n)', n * (log_n ** 2), f'{n}*log2({n})^2'),
            ('O(n^2)', n ** 2, f'{n}^2'),
            ('O(n x m)', n * m, f'{n}*{m}'),
            ('O(n^2 log n)', (n ** 2) * log_n, f'{n}^2*log2({n})'),
            ('O(n^3)', n ** 3, f'{n}^3'),
            ('O(n^3 log n)', (n ** 3) * log_n, f'{n}^3*log2({n})'),
            ('O(k^3 log n)', (n ** 3) * log_n, f'k^3*log2(n) using dominant size {n}'),
        ]
        for expected, value, formula in formulas:
            if text == expected:
                return self._estimate_payload(value, formula)

        if text == 'O(2^n)':
            return self._estimate_payload(self._safe_power(2, n), f'2^{n}')
        if text == 'O(n * 2^n)':
            return self._estimate_payload(self._safe_scaled_power(n, 2, n), f'{n}*2^{n}')
        if text == 'O(3^n)':
            return self._estimate_payload(self._safe_power(3, n), f'3^{n}')
        if text == 'O(n!)':
            return self._estimate_payload(self._safe_factorial(n), f'{n}!')
        if text == 'O(n * n!)':
            return self._estimate_payload(self._safe_scaled_factorial(n), f'{n}*{n}!')
        if text == 'O(A(m, n))':
            return {'available': False, 'display': 'Ackermann grows too fast for a broad estimate', 'formula': 'A(m, n)'}
        if 'phi' in text or 'φ' in text:
            phi = (1 + math.sqrt(5)) / 2
            return self._estimate_payload(self._safe_power_float(phi, n), f'φ^{n} ≈ 1.618^{n}')

        return {'available': False, 'display': 'No broad estimator for this complexity yet', 'formula': text}

    def _normalized_complexity_text(self, complexity):
        return (
            str(complexity or '')
            .replace('²', '^2').replace('³', '^3')
            .replace('ⁿ', '^n').replace('×', 'x')
            .replace('√n', 'sqrt(n)').replace('log²', 'log^2')
            .replace('log³', 'log^3')
            .replace('α(n)', 'alpha(n)')
        )

    def _safe_power(self, base, exponent, cap=60):
        exponent = int(exponent)
        if exponent > cap:
            return f'>{base}^{cap}'
        return base ** exponent

    def _safe_power_float(self, base, exponent, cap=60):
        exponent = int(exponent)
        if exponent > cap:
            return f'>{base:.3f}^{cap}'
        return base ** exponent

    def _safe_scaled_power(self, multiplier, base, exponent, cap=60):
        exponent = int(exponent)
        if exponent > cap:
            return f'>{self._format_estimate_number(multiplier)}*{base}^{cap}'
        return multiplier * (base ** exponent)

    def _safe_factorial(self, n, cap=25):
        n = int(n)
        if n > cap:
            return f'>{cap}!'
        return math.factorial(n)

    def _safe_scaled_factorial(self, n, cap=25):
        n = int(n)
        if n > cap:
            return f'>{self._format_estimate_number(n)}*{cap}!'
        return n * math.factorial(n)

    def _estimate_payload(self, value, formula):
        if isinstance(value, str):
            return {'available': True, 'display': value, 'formula': formula}
        return {'available': True, 'display': self._format_estimate_number(value), 'formula': formula}

    def _format_estimate_number(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if numeric < 1000:
            return str(int(numeric)) if float(numeric).is_integer() else f'{numeric:.2f}'
        if numeric < 1_000_000:
            return f'{numeric:,.0f}'
        return f'{numeric:.2e}'

    # ─────────────────────────────────────────────
    # PER-FUNCTION COMPLEXITY EXTRACTION
    # ─────────────────────────────────────────────

    def _function_special_time_result(self, name, body, full_code, language):
        cache_key = (str(name or ''), str(body or ''), str(full_code or ''), str(language or ''))
        if cache_key in self._function_special_cache:
            return self._function_special_cache[cache_key]

        result = self._function_special_time_result_uncached(name, body, full_code, language)
        self._function_special_cache[cache_key] = result
        return result

    def _function_special_time_result_uncached(self, name, body, full_code, language):
        if self._looks_like_union_find(full_code) and name in ('find', 'union'):
            return {'complexity': self._alpha(), 'reason': 'path compression and union by rank'}
        if re.search(r'parent\s*\[[^\]]+\]\s*=\s*find\s*\(\s*parent\s*\[', body):
            return {'complexity': self._alpha(), 'reason': 'path compression'}
        if self._looks_like_residual_matrix_bfs(name, body, full_code, language):
            return {
                'complexity': 'O(V^2)',
                'reason': 'Adjacency-matrix BFS may visit V vertices and scans a full V-capacity row for each vertex'
            }
        if self._looks_like_edmonds_karp_matrix_driver(name, body, full_code, language):
            return {
                'complexity': 'O(V E²)',
                'reason': 'Edmonds-Karp performs O(VE) augmentations; each BFS over the residual network gives O(E), so total time is O(V E²)'
            }
        if self._looks_like_graph_dfs_function(name, body, full_code, language):
            return {
                'complexity': 'O(V + E)',
                'reason': 'DFS graph traversal visits reachable vertices once and scans outgoing edges with a shared visited structure'
            }
        if self._looks_like_ordered_dict_constant_method(name, body, full_code, language):
            return {
                'complexity': 'O(1)',
                'reason': 'OrderedDict recency operations use hash-table lookup plus linked-order updates'
            }
        if self._looks_like_huffman_heap_driver(body, full_code):
            return {
                'complexity': 'O(n log n)',
                'reason': 'Huffman coding builds a min-heap and repeatedly extracts/merges nodes, so heap work is O(n log n)'
            }
        dynamic_execution = self.detect_dynamic_execution_complexity(body, language)
        if dynamic_execution.get('detected'):
            return dynamic_execution
        file_io = self.detect_file_io_complexity(body, language)
        if file_io.get('detected'):
            return file_io
        binary_search = self.detect_binary_search_pattern(body, language)
        if binary_search.get('detected'):
            return binary_search
        if self._looks_like_structural_tree_recursion(name, body):
            return {'complexity': 'O(n)', 'reason': 'Tree traversal visits each node once'}
        if self._looks_like_cpp_vector_string_memo_recursion(name, body, full_code):
            return {
                'complexity': f'{self._quadratic()} average, {self._cubic()} worst',
                'reason': (
                    'C++ recursive vector split with string-key memoization: vector copies and '
                    'serialized key construction are conservatively counted as quadratic on average; '
                    'unordered_map collision chains can add another factor.'
                )
            }
        if self._looks_like_memoized_scalar_recursion(name, body, full_code):
            return {'complexity': 'O(n)', 'reason': 'Memoization/cache computes each scalar subproblem once'}
        if self._looks_like_looped_halving_recursion(name, body):
            return {
                'complexity': 'O(n^((log n + 1)/2))',
                'reason': 'T(n)=n*T(n/2)+O(n) solves to Θ(n^((log n + 1)/2))'
            }
        if self._looks_like_bit_clear_loop(body):
            return {
                'complexity': 'O(popcount(n)), worst-case O(log n)',
                'reason': 'The loop uses n = n & (n - 1), clearing exactly one set bit per iteration'
            }
        if self._looks_like_binary_choice_backtracking(name, body):
            if self._backtracking_materializes_results(body):
                return {
                    'complexity': 'O(n * 2^n)',
                    'reason': 'Binary include/exclude backtracking visits 2^n states and copies length-n subsets into the result'
                }
            return {
                'complexity': 'O(2^n)',
                'reason': 'Binary include/exclude backtracking explores both choices at each input position'
            }
        if self._looks_like_recursive_resort_merge(name, body):
            return {'complexity': self._tuple_to_string(('n_log2', 1)), 'reason': 'sorted(left + right) at each merge'}
        if self._looks_like_memoized_recursive_slice_keys(name, body):
            return {'complexity': 'O(n log n)', 'reason': 'materialized memo keys and copied slices'}
        if self._looks_like_recursive_slice_partition(name, body):
            return {'complexity': 'O(n log n)', 'reason': 'copied slices at each recursion level'}
        if self.detect_recursive_ordered_map_access(full_code, language).get('detected') and re.search(rf'\b{name}\s*\([^)]*(?:-\s*1|\+\s*1)', body):
            return {'complexity': 'O(n log n)', 'reason': 'TreeMap/tree-map update in linear recursion'}
        line = self._find_function_line(full_code, name, language)
        function_context = self._function_snippet(full_code, line, language, max_lines=30)
        ordered_tree_drain = self.detect_ordered_tree_drain(function_context or body, language)
        if ordered_tree_drain.get('detected'):
            return ordered_tree_drain
        for detector in (
            self.detect_ordered_map_access,
            self.detect_ordered_tree_drain,
            self.detect_hash_table_access,
            self.detect_dynamic_execution_complexity,
            self.detect_binary_search_pattern,
            self.detect_sqrt_iteration_complexity,
            self.detect_priority_queue_operations,
            self.detect_linear_front_insert,
            self.detect_immutable_string_concat,
            self.detect_linear_membership_scan,
            self.detect_bulk_allocation_complexity,
            self.detect_nested_key_count,
            self.detect_materialized_subarray_serialization,
            self.detect_bitmask_subset_enumeration,
            self.detect_reduce_accumulator_copy,
            self.detect_java_stream_pipeline,
            self.detect_file_io_complexity,
            self.detect_implicit_iteration_complexity,
        ):
            detected = detector(body, language)
            if detected.get('detected'):
                return detected
        return None

    def _looks_like_residual_matrix_bfs(self, name, body, full_code, language):
        if language != 'python':
            return False
        compact = self._compact_ws(body)
        has_bfs_context = re.search(r'\bbfs\b|breadth.?first', str(name or ''), re.IGNORECASE) or re.search(
            r'\b(?:deque|queue|popleft)\b', compact, re.IGNORECASE
        )
        has_queue_loop = bool(re.search(r'\bwhile\s+\w*queue\w*\s*:', body))
        scans_range_row = bool(re.search(r'\bfor\s+\w+\s+in\s+range\s*\(\s*\w+\s*\)\s*:', body))
        scans_enumerated_row = bool(re.search(
            r'\bfor\s+\w+\s*,\s*\w+\s+in\s+enumerate\s*\(\s*\w+\s*\[\s*\w+\s*\]\s*\)\s*:',
            body
        ))
        reads_matrix_capacity = bool(re.search(
            r'\b\w+\s*\[\s*\w+\s*\]\s*\[\s*\w+\s*\]\s*(?:>|!=|>=)\s*0',
            body
        ))
        has_flow_names = bool(re.search(r'\b(?:residual|capacity|cap|sink|source|parent)\b', compact, re.IGNORECASE))
        return has_bfs_context and has_queue_loop and has_flow_names and (
            reads_matrix_capacity or scans_enumerated_row
        ) and (scans_range_row or scans_enumerated_row)

    def _looks_like_edmonds_karp_matrix_driver(self, name, body, full_code, language):
        if language != 'python':
            return False
        compact = self._compact_ws(body)
        named_like_flow = bool(re.search(r'edmonds|karp|max_?flow|ford', str(name or ''), re.IGNORECASE))
        calls_bfs_in_augment_loop = bool(re.search(r'\bwhile\s+bfs\s*\(', body))
        has_flow_state = bool(re.search(r'\b(?:residual|capacity|max_flow|path_flow|parent)\b', compact, re.IGNORECASE))
        has_reverse_update = bool(re.search(
            r'\b\w+\s*\[\s*\w+\s*\]\s*\[\s*\w+\s*\]\s*\+=\s*(?:path_flow|flow)',
            body
        ))
        has_matrix_residual = bool(re.search(
            r'\b\w+\s*=\s*\[\s*\[.*?\bfor\b.*?\]\s*\bfor\b',
            compact
        )) or bool(re.search(r'\b\w+\s*\[\s*\w+\s*\]\s*\[\s*\w+\s*\]', body))
        return (
            calls_bfs_in_augment_loop and
            has_flow_state and
            has_reverse_update and
            has_matrix_residual and
            (named_like_flow or re.search(r'edmonds|karp|max.?flow', full_code, re.IGNORECASE))
        )

    def _function_special_space_complexity(self, name, body, full_code, language):
        if self._looks_like_edmonds_karp_matrix_driver(name, body, full_code, language):
            return 'O(V^2)'
        if self._looks_like_residual_matrix_bfs(name, body, full_code, language):
            return 'O(V)'
        if self._looks_like_huffman_heap_driver(body, full_code):
            return 'O(n)'
        if self._looks_like_binary_choice_backtracking(name, body):
            return 'O(n * 2^n)' if self._backtracking_materializes_results(body) else 'O(n)'
        return None

    def detect_dynamic_execution_complexity(self, code, language):
        if language != 'python':
            return {'detected': False}
        compact = self._compact_ws(code)
        if not re.search(r'\b(?:compile|eval|exec)\s*\(', compact):
            return {'detected': False}
        return {
            'detected': True,
            'complexity': 'O(n)',
            'space': 'O(n)' if re.search(r'\bcompile\s*\(', compact) else 'O(1)',
            'reason': 'Dynamic code compilation/execution scans the supplied source string; n is the source/input size.',
        }

    def detect_sqrt_iteration_complexity(self, code, language):
        if language != 'python':
            return {'detected': False}
        compact = self._compact_ws(code)
        if re.search(r'\brange\s*\([^)]*(?:math\.)?sqrt\s*\(', compact):
            return {
                'detected': True,
                'complexity': 'O(√n)',
                'space': 'O(1)',
                'reason': 'Loop bound uses sqrt(n), so the loop performs O(√n) iterations.',
            }
        return {'detected': False}

    def detect_file_io_complexity(self, code, language):
        compact = self._compact_ws(code)
        if not compact:
            return {'detected': False}

        reads_whole_file = bool(re.search(
            r'\.\s*(?:read|readlines)\s*\(\s*\)|\bread_text\s*\(|\breadFile(?:Sync)?\s*\(',
            compact,
            re.IGNORECASE,
        ))
        writes_content = bool(re.search(
            r'\.\s*(?:write|writelines)\s*\(|\bwrite_text\s*\(|\bwriteFile(?:Sync)?\s*\(',
            compact,
            re.IGNORECASE,
        ))

        if reads_whole_file:
            return {
                'detected': True,
                'complexity': 'O(n)',
                'space': 'O(n)',
                'reason': 'Reads the file contents into memory; n is the number of bytes/characters read from the file.',
            }

        if writes_content:
            return {
                'detected': True,
                'complexity': 'O(n)',
                'space': 'O(1)',
                'reason': 'Writes the provided content to storage; n is the number of bytes/characters written.',
            }

        opens_file = bool(re.search(r'\bopen\s*\(|\bFileInputStream\s*\(|\bFileOutputStream\s*\(', compact))
        exists_check = bool(re.search(r'\b(?:os\.path\.)?exists\s*\(|\bPath\s*\([^)]*\)\.exists\s*\(', compact))
        if opens_file or exists_check:
            return {
                'detected': True,
                'complexity': 'O(1)',
                'space': 'O(1)',
                'reason': 'File open/existence checks are modeled as constant setup work; bulk read/write payload cost is counted separately when visible.',
            }

        return {'detected': False}

    def _looks_like_ordered_dict_constant_method(self, name, body, full_code, language):
        if language != 'python' or 'OrderedDict' not in full_code:
            return False

        if re.search(r'\bOrderedDict\s*\(', body) and not re.search(r'\b(?:for|while)\b', body):
            return True

        ordered_attrs = set(re.findall(r'\b(self\.\w+)\s*=\s*OrderedDict\s*\(', full_code))
        if not ordered_attrs:
            return False

        for attr in ordered_attrs:
            escaped = re.escape(attr)
            if not re.search(escaped, body):
                continue
            if re.search(rf'{escaped}\.move_to_end\s*\(', body):
                return True
            if re.search(rf'{escaped}\.popitem\s*\(', body):
                return True
            if re.search(rf'\b\w+\s+(?:not\s+)?in\s+{escaped}\b', body) and name in ('get', 'put', '__contains__'):
                return True

        return False

    def _extract_function_own_complexities(self, code, language):
        complexities = {}
        func_names = self._function_names(code, language)
        file_local_callables = set(func_names) | set(self._class_names(code, language))

        for name in func_names:
            body = self._extract_function_body(code, name, language)
            if body:
                special_result = self._function_special_time_result(name, body, code, language)
                if special_result:
                    complexities[name] = special_result['complexity']
                    continue
                recursion_result = self._detect_body_recursion_complexity(name, body)
                if recursion_result:
                    complexities[name] = recursion_result['complexity']
                else:
                    time_result = self.detect_time_complexity(
                        body,
                        language,
                        extra_known_defs=file_local_callables,
                    )
                    complexities[name] = time_result['complexity']

        return complexities

    def _extract_all_function_complexities(self, code, language):
        func_names = self._function_names(code, language)
        complexities = self._extract_function_own_complexities(code, language)
        self.last_func_own_complexities = dict(complexities)

        known_functions = set(complexities)
        bodies = {
            name: self._extract_function_body(code, name, language)
            for name in func_names
            if name in known_functions
        }
        call_contexts = {}
        for name, body in bodies.items():
            target_names = set(known_functions)
            target_names.discard(name)
            call_contexts[name] = self._call_loop_contexts(body, target_names, current_func=name)

        def call_cost(callee, multiplier):
            callee_complexity = complexities.get(callee, 'O(1)')
            if multiplier == 'O(1)':
                return callee_complexity
            return self._tuple_to_string(self._multiply_complexity(
                self._parse_complexity_string(multiplier),
                self._parse_complexity_string(callee_complexity)
            ))

        def effective_for(name):
            own = complexities.get(name, 'O(1)')
            combined_inputs = [own]
            for callee, multiplier in call_contexts.get(name, []):
                if callee in complexities:
                    combined_inputs.append(call_cost(callee, multiplier))
            return self._max_complexity(combined_inputs)

        complexities = {
            name: effective_for(name)
            for name in func_names
            if name in complexities
        }

        self._apply_function_effective_overrides(code, language, complexities)
        return complexities

    def _apply_function_effective_overrides(self, code, language, complexities):
        repeated_dfs = self._repeated_fresh_graph_search_info(code, 'dfs')
        if repeated_dfs:
            callee = repeated_dfs.get('callee')
            caller = repeated_dfs.get('caller')
            if callee in complexities:
                complexities[callee] = 'O(V + E)'
            if caller in complexities:
                complexities[caller] = 'O(V * (V + E))'

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_matrix_power_recursion(name, body, complexities):
                complexities[name] = 'O(k³ log n)'

    def _build_function_complexity_details(self, code, language, own_complexities, effective_complexities):
        pending = {}
        own_space_complexities = {}
        repeated_dfs = self._repeated_fresh_graph_search_info(code, 'dfs')
        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            own = own_complexities.get(name, 'O(1)')
            effective = effective_complexities.get(name, own)
            reason = self._function_complexity_reason(name, body, own, effective, effective_complexities, code, language)
            calls = self._function_call_summaries(body, effective_complexities, current_func=name)
            if repeated_dfs and name == repeated_dfs.get('caller'):
                calls = [{
                    'function': repeated_dfs.get('callee', 'dfs'),
                    'multiplier': 'O(V)',
                    'complexity': 'O(V + E)',
                }]
            line = self._find_function_line(code, name, language)
            snippet = self._function_snippet(code, line, language)
            space_subject = snippet or body
            own_space = (
                self._function_special_space_complexity(name, body, code, language) or
                (self._detect_function_space_complexity(space_subject, language) if space_subject else 'O(1)')
            )
            own_space_complexities[name] = own_space
            pending[name] = {
                'function': name,
                'own_complexity': own,
                'effective_complexity': effective,
                'complexity': effective,
                'reason': reason,
                'calls': calls,
                'line': line,
                'snippet': snippet,
                'own_space_complexity': own_space,
                'space_complexity': own_space,
            }

        effective_space_cache = {}
        visiting = set()

        def effective_space_for(name):
            if name in effective_space_cache:
                return effective_space_cache[name]
            own_space = own_space_complexities.get(name, 'O(1)')
            if name in visiting:
                return own_space
            visiting.add(name)
            values = [own_space]
            for call in pending.get(name, {}).get('calls') or []:
                callee = call.get('function')
                if callee in pending:
                    values.append(effective_space_for(callee))
            visiting.discard(name)
            effective_space_cache[name] = self._max_complexity(values)
            return effective_space_cache[name]

        details = {}
        for name, detail in pending.items():
            effective_space = effective_space_for(name)
            details[name] = {
                **detail,
                'effective_space_complexity': effective_space,
                'space_complexity': effective_space,
            }
        return details

    def _detect_function_space_complexity(self, code, language):
        saved_complexities = dict(getattr(self, 'last_func_complexities', {}) or {})
        saved_own_complexities = dict(getattr(self, 'last_func_own_complexities', {}) or {})
        saved_details = dict(getattr(self, 'last_func_complexity_details', {}) or {})
        try:
            return self.detect_space_complexity(code, language)
        finally:
            self.last_func_complexities = saved_complexities
            self.last_func_own_complexities = saved_own_complexities
            self.last_func_complexity_details = saved_details

    def _find_function_line(self, code, func_name, language):
        cache_key = (str(code or ''), str(func_name or ''), str(language or ''))
        if cache_key in self._function_line_cache:
            return self._function_line_cache[cache_key]

        line_number = 1
        if language == 'python':
            node = self._python_function_node(code, func_name)
            if node:
                line_number = getattr(node, 'lineno', 1)
                self._function_line_cache[cache_key] = line_number
                return line_number

        synthetic = self._javascript_synthetic_function(code, func_name, language)
        if synthetic:
            line_number = synthetic.get('line') or 1
            self._function_line_cache[cache_key] = line_number
            return line_number

        for line_number, line in enumerate(code.splitlines(), 1):
            for match in re.finditer(self._function_def_regex(), line):
                if match.group(1) == func_name:
                    self._function_line_cache[cache_key] = line_number
                    return line_number
            if self._is_javascript_like(language) and re.search(
                rf'\b(?:const|let|var)\s+{re.escape(func_name)}\s*=',
                line
            ):
                self._function_line_cache[cache_key] = line_number
                return line_number
        self._function_line_cache[cache_key] = 1
        return 1

    def _function_snippet(self, code, start_line, language=None, max_lines=None):
        cache_key = (str(code or ''), int(start_line or 1), str(language or ''), max_lines)
        if cache_key in self._function_snippet_cache:
            return self._function_snippet_cache[cache_key]

        snippet = ''
        if language == 'python':
            for node in self._python_function_nodes(code):
                if getattr(node, 'lineno', 0) == start_line:
                    snippet = self._python_function_source(code, node, include_header=True)
                    if snippet:
                        if max_lines is None:
                            self._function_snippet_cache[cache_key] = snippet
                            return snippet
                        snippet = '\n'.join(snippet.splitlines()[:max_lines]).strip()
                        self._function_snippet_cache[cache_key] = snippet
                        return snippet

        if self._is_javascript_like(language):
            for item in self._javascript_synthetic_functions(code, language):
                if item.get('line') == start_line and item.get('snippet'):
                    snippet = item['snippet']
                    if max_lines is not None:
                        snippet = '\n'.join(snippet.splitlines()[:max_lines]).strip()
                    self._function_snippet_cache[cache_key] = snippet
                    return snippet

        lines = code.splitlines()
        if not lines:
            return ''
        start = max(0, (start_line or 1) - 1)
        end = self._function_snippet_end(lines, start, language, max_lines)
        snippet = '\n'.join(lines[start:end]).strip()
        self._function_snippet_cache[cache_key] = snippet
        return snippet

    def _function_snippet_end(self, lines, start, language=None, max_lines=None):
        hard_end = len(lines) if max_lines is None else min(len(lines), start + max_lines)
        if start >= len(lines):
            return hard_end

        if language == 'python' or self._line_starts_python_block(lines[start]):
            base_indent = self._line_indent(lines[start])
            seen_body = False
            for index in range(start + 1, hard_end):
                line = lines[index]
                text = line.strip()
                if not text:
                    continue
                if seen_body and self._line_indent(line) <= base_indent and self._line_starts_python_section_boundary(line):
                    return index
                if (
                    self._line_indent(line) <= base_indent and
                    self._line_starts_python_block(line)
                ):
                    return index
                if self._line_indent(line) > base_indent:
                    seen_body = True
            return hard_end

        if language in ('java', 'cpp', 'c', 'javascript', 'typescript') or self._line_starts_function(lines[start], language):
            depth = 0
            seen_open = False
            for index in range(start, hard_end):
                line = lines[index]
                if '{' in line:
                    seen_open = True
                depth += line.count('{') - line.count('}')
                if seen_open and depth <= 0:
                    return index + 1

            if not seen_open:
                for index in range(start + 1, hard_end):
                    if self._line_starts_function(lines[index], language):
                        return index
                    if ';' in lines[index]:
                        return index + 1

        return hard_end

    def _line_indent(self, line):
        expanded = line.expandtabs(4)
        return len(expanded) - len(expanded.lstrip())

    def _line_starts_function(self, line, language=None):
        stripped = line.strip()
        if not stripped:
            return False
        if language == 'python' or self._line_starts_python_block(line):
            return self._line_starts_python_block(line)
        return bool(re.match(self._function_def_regex(), stripped))

    def _line_starts_python_block(self, line):
        stripped = line.strip()
        return stripped.startswith(('def ', 'async def ', 'class '))

    def _line_starts_python_section_boundary(self, line):
        stripped = line.strip()
        if not stripped.startswith('#'):
            return False
        marker = stripped.lstrip('#').strip()
        if not marker:
            return False
        if set(marker) <= {'=', '-', '_', '*'}:
            return True
        return marker.isupper() or marker.endswith(('FUNCTIONS', 'DEMO FUNCTIONS', 'MAIN MENU'))

    def _build_hotspots(self, details):
        if isinstance(details, dict):
            detail_items = details.values()
        else:
            detail_items = details or []

        hotspots = []
        linear_rank = self._complexity_rank(self._parse_complexity_string('O(n)'))
        for detail in detail_items:
            complexity = detail.get('effective_complexity') or detail.get('complexity') or 'O(1)'
            rank = self._complexity_rank(self._parse_complexity_string(complexity))
            if 'unknown' not in str(complexity).lower() and rank <= linear_rank:
                continue
            hotspots.append({
                'function': detail.get('function') or 'anonymous',
                'line': detail.get('line') or 1,
                'complexity': complexity,
                'space_complexity': detail.get('effective_space_complexity') or detail.get('space_complexity') or 'O(1)',
                'own_space_complexity': detail.get('own_space_complexity') or detail.get('space_complexity') or 'O(1)',
                'effective_space_complexity': detail.get('effective_space_complexity') or detail.get('space_complexity') or 'O(1)',
                'reason': detail.get('reason') or 'This function dominates the detected complexity.',
                'snippet': detail.get('snippet') or '',
                '_rank': rank,
            })

        hotspots.sort(key=lambda item: item['_rank'], reverse=True)
        for item in hotspots:
            item.pop('_rank', None)
        return hotspots[:10]

    def _function_call_summaries(self, body, effective_complexities, current_func=None):
        summaries = []
        seen = set()
        matrix_power_context = bool(
            current_func and
            self._looks_like_matrix_power_recursion(current_func, body, effective_complexities)
        )
        for callee, multiplier in self._call_loop_contexts(body, set(effective_complexities), current_func):
            if callee == current_func:
                continue
            key = (callee, multiplier)
            if key in seen:
                continue
            seen.add(key)
            callee_complexity = effective_complexities.get(callee, 'O(1)')
            if matrix_power_context and callee_complexity in ('O(n³)', 'O(n^3)'):
                callee_complexity = 'O(k³)'
            summaries.append({
                'function': callee,
                'multiplier': multiplier,
                'complexity': callee_complexity,
            })
        return summaries

    def _function_complexity_reason(self, name, body, own, effective, effective_complexities, full_code='', language='typescript'):
        repeated_dfs = self._repeated_fresh_graph_search_info(full_code or body, 'dfs')
        if repeated_dfs and name == repeated_dfs.get('caller'):
            return (
                'The outer loop creates a fresh visited array/set for each start vertex, '
                'so DFS can rescan up to V vertices and E edges for every start.'
            )
        special = self._function_special_time_result(name, body, full_code or body, language or 'typescript')
        if special:
            if 'DFS graph traversal' in special.get('reason', ''):
                return special['reason']
            if 'front insertion' in special.get('reason', '').lower():
                return 'Front insertion shifts existing elements on each loop iteration.'
            if 'Immutable string concatenation' in special.get('reason', ''):
                return special['reason']
            if 'count every pair of keys' in special.get('reason', ''):
                return 'Nested loops count every pair of keys.'
            if 'Hash table access' in special.get('reason', ''):
                return special['reason']
            if 'Ordered map' in special.get('reason', '') or 'TreeMap' in special.get('reason', ''):
                return special['reason']
            if 'copied slices' in special.get('reason', '') or 'materialized memo keys' in special.get('reason', ''):
                return special['reason']
            if 'sorted(left + right)' in special.get('reason', ''):
                return special['reason']
            if 'T(n)=n*T(n/2)+O(n)' in special.get('reason', ''):
                return special['reason']
            return special.get('reason', 'Matched a specialized function-level complexity pattern.')
        if own == 'O(n log n)' and re.search(r'\.(?:put|remove|insert|erase)\s*\(', body) and re.search(rf'\b{name}\s*\(', body):
            return 'Recursive ordered map/set update: one or more TreeMap/tree-map updates cost O(log n) at each recursion level.'
        if self._looks_like_matrix_power_recursion(name, body, effective_complexities):
            return (
                'Binary matrix exponentiation: the exponent reaches the base case in O(log n) '
                'recursive levels. Each level performs one matrix multiplication costing O(k³), '
                'so the effective function cost is O(k³ log n).'
            )
        if self._looks_like_naive_matrix_multiplication(body):
            return (
                'Naive square matrix multiplication: three nested loops fill the k×k result, '
                'and each cell computes a length-k dot product, giving O(k³) arithmetic work.'
            )
        if own != effective:
            return (
                f'Own work is {own}, but calls to helper functions raise the effective cost to {effective}.'
            )
        recursion = self._detect_body_recursion_complexity(name, body)
        if recursion:
            return recursion.get('reason', f'Recursive function with {effective} effective complexity.')
        loops = self.extract_loop_tree(body, 'unknown')
        loop_complexity = self.compute_loop_complexity(loops)
        if loop_complexity:
            return f'Loop structure in this function contributes {loop_complexity} work.'
        return f'No input-sized loops or recursive expansion were found, so this function is {effective}.'

    # ─────────────────────────────────────────────
    # RECURSION COMPLEXITY DETECTION
    # ─────────────────────────────────────────────

    def _detect_body_recursion_complexity(self, func_name, body):
        direct_calls = len(re.findall(rf'\b{func_name}\s*\(', body))
        yield_calls = len(re.findall(rf'yield\s*\*\s*{func_name}\s*\(', body))
        call_count = direct_calls + yield_calls
        if call_count == 0:
            return None

        is_generator = bool(re.search(r'yield\s*\*', body))
        has_memo = bool(re.search(
            r'memo|cache|@lru_cache|@cache|memoize|functools\.cache|'
            r'dp\s*=\s*\{|dp\s*=\s*\[',
            body, re.IGNORECASE
        ))
        has_halving = bool(re.search(
            r'\/\s*2|>>\s*1|mid\s*=|Math\.floor\s*\(\s*\w+\s*\/\s*2', body
        ))
        has_thirding = bool(re.search(r'\/\s*3\b|\/\s*3\.0\b', body))
        has_ackermann = self._has_ackermann_recursion(func_name, body)
        has_decrement = self._has_recursive_decrement_call(func_name, body)
        has_halving_call = bool(re.search(
            rf'\b{func_name}\s*\([^)]*(?:\/\s*2|Math\.floor|>>\s*1)', body
        ))
        has_balanced_partition = self._has_balanced_partition_recursion(func_name, body)
        has_shrinking_substring = self._has_recursive_shrinking_substring_calls(func_name, body)
        loop_complexity = self.compute_loop_complexity(self.extract_loop_tree(body, 'unknown'))
        body_work = loop_complexity or 'O(1)'
        is_tail = self._is_tail_recursive(func_name, body)

        if self._looks_like_strassen_recursion(func_name, body, call_count):
            return {
                'complexity': 'O(n^2.807)',
                'reason': "Strassen recurrence T(n)=7T(n/2)+O(n^2) -> O(n^log2 7) ~= O(n^2.807)"
            }

        if re.search(r'parent\s*\[[^\]]+\]\s*=\s*find\s*\(\s*parent\s*\[', body):
            return {
                'complexity': self._alpha(),
                'reason': 'Union-Find find with path compression has amortized inverse-Ackermann cost'
            }

        if self._looks_like_looped_halving_recursion(func_name, body):
            return {
                'complexity': 'O(n^((log n + 1)/2))',
                'reason': (
                    'Looped halving recursion T(n)=n*T(n/2)+O(n): level products '
                    '1·n·(n/2)·(n/4)... give quasi-polynomial Θ(n^((log n + 1)/2))'
                )
            }

        if self._looks_like_binary_choice_backtracking(func_name, body):
            if self._backtracking_materializes_results(body):
                return {
                    'complexity': 'O(n * 2^n)',
                    'reason': 'Binary include/exclude backtracking visits 2^n states and copies each stored subset'
                }
            return {
                'complexity': 'O(2^n)',
                'reason': 'Binary include/exclude backtracking explores both choices at every position'
            }

        if self._looks_like_recursive_resort_merge(func_name, body):
            return {
                'complexity': self._tuple_to_string(('n_log2', 1)),
                'reason': 'Recursive merge calls sorted(left + right), adding a sort at each merge level'
            }

        if self._looks_like_memoized_recursive_slice_keys(func_name, body):
            return {
                'complexity': 'O(n log n)',
                'reason': 'Memoized recursive slicing still pays O(n log n) for materialized memo keys and copied slices'
            }

        if self._looks_like_recursive_slice_partition(func_name, body):
            return {
                'complexity': 'O(n log n)',
                'reason': 'Divide-and-conquer recursion copies slices at each level, giving O(n log n) copied slices'
            }

        if has_memo:
            if has_halving:
                return {'complexity': 'O(log n)', 'reason': 'Memoized recursion with halving — O(log n) unique states'}
            return {'complexity': 'O(n)', 'reason': 'Memoized recursion — O(n) unique subproblems'}

        if has_ackermann:
            return {'complexity': 'O(A(m, n))', 'reason': 'Ackermann-style nested recursion'}

        uneven = self._analyze_uneven_divide_recursion(func_name, body, call_count, body_work)
        if uneven:
            return uneven

        # T(n) = T(n-1) + O(body_work) with non-trivial body
        if call_count == 1 and has_decrement and body_work not in ('O(1)', 'O(log n)'):
            result = self._multiply_and_format('O(n)', body_work)
            return {
                'complexity': result,
                'reason': f'Linear recursion T(n)=T(n-1)+{body_work} → {result}'
            }

        # T(n) = T(n/3) → O(log n) base 3
        if call_count == 1 and has_thirding and not has_halving and body_work == 'O(1)':
            return {'complexity': 'O(log n)', 'reason': 'Single recursive call with /3 shrinking — O(log₃ n)=O(log n)'}

        # T(n) = T(n/2) + O(n) → O(n) [Master Case 3]
        if call_count == 1 and has_halving and body_work == 'O(n)':
            return {'complexity': 'O(n)', 'reason': 'T(n)=T(n/2)+O(n) — Master Theorem Case 3 → O(n)'}

        if self._looks_like_binary_exponentiation_recursion(func_name, body):
            return {
                'complexity': 'O(log n)',
                'reason': 'Binary exponentiation recursion: only one branch runs per call, and the exponent halves after at most two steps'
            }

        # T(n) = 2T(n/2) + O(n) → O(n log n) [Merge Sort]
        if call_count >= 2 and has_decrement and has_halving_call:
            return {
                'complexity': 'O(2^n)',
                'reason': 'Mixed recurrence T(n)=T(n-1)+T(n/2): T(n-1) branch dominates -> O(2^n)'
            }

        if call_count == 2 and has_halving and body_work == 'O(n)':
            mt, _, reason = self.master_theorem.solve(2, 2, 'n', 1)
            return {'complexity': mt, 'reason': f'Merge-sort recurrence: {reason}'}

        # T(n) = 2T(n/2) + O(1) → O(n) [Master Case 1]
        if call_count == 2 and has_halving and body_work == 'O(1)':
            mt, _, reason = self.master_theorem.solve(2, 2, 'const', 0)
            return {'complexity': mt, 'reason': f'Binary divide-and-conquer: {reason}'}

        # T(n) = 4T(n/2) + O(n) → O(n²) [Master Case 1]
        if call_count == 4 and has_halving and body_work == 'O(n)':
            mt, _, reason = self.master_theorem.solve(4, 2, 'n', 1)
            return {'complexity': mt, 'reason': f'4-way D&C: {reason}'}

        recursive_multiplier = self._recursive_call_multiplier(func_name, body)

        if recursive_multiplier == 'O(log n)' and has_halving:
            complexity = body_work if body_work != 'O(1)' else 'O(log² n)'
            return {
                'complexity': complexity,
                'reason': f'Log-loop of T(n/2) calls: converges — dominated by body work {body_work}'
            }

        if call_count >= 2 and has_decrement and has_halving_call:
            return {
                'complexity': 'O(2^n)',
                'reason': 'Mixed recurrence T(n)=T(n-1)+T(n/2): T(n-1) branch dominates → O(2^n)'
            }

        if is_generator and call_count == 2 and has_decrement and has_halving_call:
            return {
                'complexity': 'O(2^n)',
                'reason': 'Generator recursion T(n)=T(n-1)+T(n/2) is exponential'
            }

        if has_shrinking_substring and call_count >= 2:
            return {
                'complexity': 'O(n * 2^n)',
                'reason': 'Branching on length-(n-1) substrings: T(n)=2T(n-1)+O(n)'
            }

        if call_count >= 2 and has_balanced_partition:
            ft, fp = self._body_work_to_ft_fp(body_work)
            mt, _, reason = self.master_theorem.solve(call_count, 2, ft, fp)
            return {'complexity': mt, 'reason': f'Balanced partition: {reason}'}

        if call_count == 1 and has_halving:
            complexity = self._max_complexity(['O(log n)', loop_complexity])
            return {'complexity': complexity, 'reason': 'Single recursive call with halving + body work'}

        if call_count == 1 and is_tail:
            return {
                'complexity': self._max_complexity(['O(n)', body_work]),
                'reason': 'Tail-recursive: O(n) calls, body work per call'
            }

        if call_count == 1:
            complexity = self._max_complexity(['O(n)', loop_complexity])
            return {'complexity': complexity, 'reason': 'Single recursive call per level + body work'}

        # Fibonacci: T(n) = T(n-1) + T(n-2)
        if call_count == 2 and has_decrement and not has_halving:
            fib_like = bool(re.search(
                rf'\b{func_name}\s*\(\s*\w+\s*-\s*1\s*\).*\b{func_name}\s*\(\s*\w+\s*-\s*2\s*\)',
                body, re.DOTALL
            )) or bool(re.search(
                rf'\b{func_name}\s*\(\s*\w+\s*-\s*2\s*\).*\b{func_name}\s*\(\s*\w+\s*-\s*1\s*\)',
                body, re.DOTALL
            ))
            if fib_like:
                return {
                    'complexity': 'O(φⁿ)',
                    'reason': 'Fibonacci recurrence T(n)=T(n-1)+T(n-2) → O(φⁿ)≈O(1.618ⁿ), bounded by O(2^n)'
                }
            return {
                'complexity': 'O(2^n)',
                'reason': f'Two recursive calls with linear decrement: T(n)=2T(n-1)+{body_work} → O(2^n)'
            }

        if call_count == 3 and has_decrement and not has_halving:
            return {'complexity': 'O(3^n)', 'reason': 'Three recursive calls with linear decrement → O(3^n)'}

        if call_count >= 2 and has_halving:
            ft, fp = self._body_work_to_ft_fp(body_work)
            # Strassen: 7T(n/2)+O(n²)
            if call_count == 7 and body_work in ('O(n²)', 'O(n^2)'):
                return {'complexity': 'O(n^2.807)', 'reason': "Strassen's 7T(n/2)+O(n²) → O(n^log₂7) ≈ O(n^2.807)"}
            # Karatsuba: 3T(n/2)+O(n)
            if call_count == 3 and body_work == 'O(n)':
                return {'complexity': 'O(n^1.585)', 'reason': 'Karatsuba 3T(n/2)+O(n) → O(n^log₂3)≈O(n^1.585)'}
            mt, _, reason = self.master_theorem.solve(call_count, 2, ft, fp)
            return {'complexity': mt, 'reason': f'T(n)={call_count}T(n/2)+{body_work} → {mt} ({reason})'}

        return {
            'complexity': f'O({call_count}^n)',
            'reason': f'{call_count} recursive calls per level without halving or memoisation'
        }

    def _analyze_uneven_divide_recursion(self, func_name, body, call_count, body_work):
        factors = self._recursive_division_factors(func_name, body)
        if len(factors) < 2 or len(factors) != call_count:
            return None
        if len(set(round(f, 6) for f in factors)) == 1:
            return None

        p = self._solve_akra_bazzi_exponent(factors)
        f_type, f_power = self._body_work_to_ft_fp(body_work)
        body_degree = self._body_work_degree(f_type, f_power)
        eps = 0.01

        if body_degree > p + eps:
            complexity = self._tuple_to_string((f_type, f_power))
        elif abs(body_degree - p) <= eps:
            complexity = self._format_fractional_power(p).replace(')', ' log n)')
        else:
            complexity = self._format_fractional_power(p)

        factor_text = ', '.join(self._format_number(f) for f in factors)
        recurrence = (
            'T(n) = ' +
            ' + '.join(f'T(n/{self._format_number(f)})' for f in factors) +
            f' + {body_work}'
        )
        return {
            'complexity': complexity,
            'reason': (
                f'Uneven divide-and-conquer solved by Akra-Bazzi: '
                f'T(n) = ' + ' + '.join(f'T(n/{self._format_number(f)})' for f in factors) +
                f' + {body_work}. Solve sum(1/b^p)=1 for b=[{factor_text}], p≈{p:.4f} → {complexity}'
            ),
            'recurrence_analysis': {
                'method': 'Akra-Bazzi',
                'recurrence': recurrence,
                'division_factors': [
                    int(f) if float(f).is_integer() else f
                    for f in factors
                ],
                'branch_count': call_count,
                'body_work': body_work,
                'akra_bazzi_exponent': round(p, 4),
                'complexity': complexity,
                'dominant_term': complexity,
                'equation': 'sum(1 / b_i^p) = 1',
                'reason': (
                    f'Uneven recursive branches shrink by [{factor_text}], so Master Theorem does not apply directly; '
                    f'Akra-Bazzi gives p≈{p:.4f}.'
                ),
            }
        }

    def _recursive_division_factors(self, func_name, body):
        factors = []
        for args in self._recursive_call_argument_lists(func_name, body):
            first_arg = args.split(',', 1)[0].strip()
            factor = self._division_factor_from_expr(first_arg)
            if factor:
                factors.append(factor)
        return factors

    def _recursive_call_argument_lists(self, func_name, body):
        args_list = []
        pattern = re.compile(rf'\b{re.escape(func_name)}\s*\(')
        for match in pattern.finditer(body):
            start = match.end()
            depth = 1
            index = start
            quote = None
            escape = False
            while index < len(body):
                char = body[index]
                if quote:
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == quote:
                        quote = None
                elif char in ('"', "'", '`'):
                    quote = char
                elif char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        args_list.append(body[start:index])
                        break
                index += 1
        return args_list

    def _division_factor_from_expr(self, expr):
        shift = re.search(r'>>\s*(\d+)', expr)
        if shift:
            return float(2 ** int(shift.group(1)))

        div = re.search(r'(?://|/)\s*(\d+(?:\.\d+)?)', expr)
        if div:
            value = float(div.group(1))
            return value if value > 1 else None

        floor_div = re.search(r'Math\.floor\s*\([^)]*/\s*(\d+(?:\.\d+)?)\s*\)', expr)
        if floor_div:
            value = float(floor_div.group(1))
            return value if value > 1 else None

        return None

    def _solve_akra_bazzi_exponent(self, factors):
        low, high = 0.0, 10.0
        for _ in range(80):
            mid = (low + high) / 2
            total = sum(f ** (-mid) for f in factors)
            if total > 1:
                low = mid
            else:
                high = mid
        return (low + high) / 2

    def _body_work_degree(self, f_type, f_power):
        return {
            'const': 0.0, 'log': 0.001, 'log2': 0.002, 'log3': 0.003,
            'sqrt': 0.5, 'n': float(f_power),
            'n_log': 1.001, 'n_log2': 1.002,
            'n2_log': 2.001, 'n3_log': 3.001,
        }.get(f_type, float(f_power) if isinstance(f_power, (int, float)) else 1.0)

    def _format_fractional_power(self, exponent):
        rounded = round(exponent, 3)
        if abs(rounded - 1) < 0.001:
            return 'O(n)'
        if abs(rounded - 2) < 0.001:
            return 'O(n²)'
        if abs(rounded - 3) < 0.001:
            return 'O(n³)'
        return f'O(n^{rounded:.3f})'

    def _format_number(self, value):
        return str(int(value)) if float(value).is_integer() else f'{value:g}'

    def _looks_like_strassen_recursion(self, func_name, body, call_count):
        if call_count != 7:
            return False
        m_assigns = len(re.findall(r'\bM[1-7]\s*=', body))
        matrix_combine = bool(re.search(r'vstack|hstack|concatenate|C11|C12|C21|C22', body))
        split_quadrants = bool(re.search(r'\bsplit\s*\(|A11|A12|A21|A22|B11|B12|B21|B22', body))
        return 'strassen' in func_name.lower() or (m_assigns >= 7 and matrix_combine and split_quadrants)

    def _body_work_to_ft_fp(self, body_work):
        mapping = {
            'O(1)': ('const', 0), 'O(log n)': ('log', 1),
            'O(n)': ('n', 1), 'O(n log n)': ('n_log', 1),
            'O(n²)': ('n', 2), 'O(n^2)': ('n', 2),
            'O(n² log n)': ('n2_log', 1), 'O(n³)': ('n', 3),
        }
        return mapping.get(body_work, ('n', 1))

    def _is_tail_recursive(self, func_name, body):
        for line in body.split('\n'):
            stripped = line.strip()
            if re.search(rf'\breturn\s+{func_name}\s*\(', stripped):
                return True
        return False

    def _multiply_and_format(self, a, b):
        return self._tuple_to_string(self._multiply_complexity(
            self._parse_complexity_string(a),
            self._parse_complexity_string(b)
        ))

    def _has_ackermann_recursion(self, func_name, body):
        nested_call = re.search(rf'\b{func_name}\s*\([^;\n]*\b{func_name}\s*\(', body)
        if not nested_call:
            return False
        has_first = bool(re.search(rf'\b{func_name}\s*\(\s*\w+\s*-\s*1\s*,', body))
        has_second = bool(re.search(rf'\b{func_name}\s*\(\s*\w+\s*,\s*\w+\s*-\s*1\s*\)', body))
        return has_first and has_second

    def _has_recursive_decrement_call(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(([^)]*)\)', body)
        for args in calls:
            if re.search(r'\b\w+\s*-\s*[12]\b|\b\w+\s*--|--\s*\w+', args):
                return True
        return False

    def _has_balanced_partition_recursion(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(([^)]*)\)', body)
        if len(calls) < 2:
            return False
        has_mid = bool(re.search(
            r'\bmid\s*=\s*\(?\s*\w+\s*\+\s*\w+\s*\)?\s*(?://|/|>>)\s*2|'
            r'\bmid\s*=\s*\w+\s*\+\s*\(?\s*\w+\s*-\s*\w+\s*\)?\s*(?://|/)\s*2|'
            r'\bmid\s*=\s*Math\.floor\s*\(', body
        ))
        uses_left = any(re.search(r'\bmid\s*-\s*1\b|,\s*mid\s*[),]', c) for c in calls)
        uses_right = any(re.search(r'\bmid\s*\+\s*1\b|\bmid\s*,', c) for c in calls)
        direct_halves = sum(1 for c in calls if re.search(r'//\s*2|/\s*2|>>\s*1|Math\.floor', c))
        return (has_mid and uses_left and uses_right) or direct_halves >= 2

    def _has_recursive_shrinking_substring_calls(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(', body)
        if len(calls) < 2:
            return False
        substring_shrink = bool(re.search(
            r'\.substring\s*\([^;\n]*(?:length\s*\(\)\s*-\s*1|,\s*[^)]*length\s*\(\s*\))', body
        ))
        slicing_shrink = bool(re.search(
            r'\[[^:\]]*(?::\s*-1|1\s*:|:\s*len\s*\([^)]*\)\s*-\s*1)', body
        ))
        return substring_shrink or slicing_shrink

    # ─────────────────────────────────────────────
    # CONCRETE ANALYSIS
    # ─────────────────────────────────────────────

    def detect_concrete_analysis(self, code, language, concrete_inputs=None):
        dfs = self._find_dfs_function(code, language)
        if dfs:
            graph_inputs = self._parse_graph_concrete_inputs(concrete_inputs, dfs)
            if graph_inputs:
                return self._concrete_dfs_analysis(dfs, graph_inputs)

        bit_clear = self._find_bit_clear_function(code, language)
        if bit_clear:
            value = self._parse_single_concrete_input(concrete_inputs, bit_clear['name'], bit_clear['param'])
            if value is None:
                value = self._find_literal_single_call_value(code, bit_clear['name'])
            if value is not None:
                return self._concrete_bit_clear_analysis(bit_clear, value)

        ackermann = self._find_ackermann_function(code, language)
        if not ackermann:
            return None
        values = self._parse_concrete_input_values(concrete_inputs, ackermann['name'], ackermann['params'])
        if values is None:
            values = self._find_literal_call_values(code, ackermann['name'])
        if values is None:
            return None
        m, n = values
        exact = self._simulate_ackermann(m, n)
        if not exact['available']:
            return exact
        param_a = ackermann['params'][0] if len(ackermann['params']) > 0 else 'm'
        param_b = ackermann['params'][1] if len(ackermann['params']) > 1 else 'n'
        return {
            'available': True, 'kind': 'ackermann_exact',
            'function': ackermann['name'],
            'inputs': {param_a: m, param_b: n},
            'return_value': exact['return_value'],
            'calls': exact['calls'], 'max_stack_depth': exact['max_stack_depth'],
            'time': f"{exact['calls']} function calls",
            'space': f"{exact['max_stack_depth']} stack frames",
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': 'O(A(m, n))',
            'symbolic_space_complexity': 'O(A(m, n))',
            'reason': 'Exact concrete-input simulation for fixed Ackermann inputs'
        }

    def _detect_fixed_entrypoint_literal_analysis(self, code, language, scalable_time, scalable_space):
        if language not in ('python', 'java', 'cpp', 'c', 'javascript', 'typescript'):
            return None
        if self._has_runtime_input_source(code):
            return None

        entrypoint = self._entrypoint_function_name(code, language)
        if not entrypoint:
            return None

        line = self._find_function_line(code, entrypoint, language)
        snippet = self._function_snippet(code, line, language, max_lines=80) or self._extract_function_body(code, entrypoint, language)
        literal_inputs = self._literal_entrypoint_inputs(snippet)
        if not literal_inputs:
            return None

        max_items = max(item.get('size', 0) for item in literal_inputs)
        return {
            'available': True,
            'kind': 'fixed_entrypoint_literals',
            'entrypoint': entrypoint,
            'inputs': {item['name']: item['size'] for item in literal_inputs if item.get('name')},
            'input_count': max_items,
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': scalable_time,
            'symbolic_space_complexity': scalable_space,
            'reason': (
                f'The submitted {entrypoint}() uses literal in-code data and no runtime input source, '
                'so this exact run is constant-size. CodeScope still reports scalable Big-O separately.'
            ),
        }

    def _apply_fixed_entrypoint_overall(self, result, concrete):
        overall = dict(result.get('overall_complexity') or {})
        scalable_time = concrete.get('symbolic_time_complexity') or result.get('time_complexity') or overall.get('time') or 'O(1)'
        scalable_space = concrete.get('symbolic_space_complexity') or result.get('space_complexity') or overall.get('space') or 'O(1)'
        current_time = concrete.get('fixed_input_time_complexity') or 'O(1)'
        current_space = concrete.get('fixed_input_space_complexity') or 'O(1)'
        overall.update({
            'time': current_time,
            'space': current_space,
            'current_run_time': current_time,
            'current_run_space': current_space,
            'scalable_time': scalable_time,
            'scalable_space': scalable_space,
            'headline': (
                f'{current_time} current run, {current_space} current space; '
                f'{scalable_time} scalable time, {scalable_space} scalable space'
            ),
        })
        result['overall_complexity'] = overall

    def _entrypoint_function_name(self, code, language):
        names = set(self._function_names(code, language))
        if language == 'python':
            if 'main' in names and re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', code):
                return 'main'
            return None
        if language in ('java', 'cpp', 'c') and 'main' in names:
            return 'main'
        if language in ('javascript', 'typescript') and 'main' in names and re.search(r'\bmain\s*\(\s*\)', code):
            return 'main'
        return None

    def _has_runtime_input_source(self, code):
        return bool(re.search(
            r'\binput\s*\(|\bsys\.stdin\b|\bstdin\b|\bScanner\s*\(|\bBufferedReader\s*\(|'
            r'\bcin\s*>>|\bscanf\s*\(|\bfgets\s*\(|\breadline\s*\(|\bprocess\.argv\b|'
            r'\bargv\b|\bprompt\s*\(',
            code,
            re.IGNORECASE
        ))

    def _literal_entrypoint_inputs(self, snippet):
        items = []
        seen = set()
        for pattern in (
            r'\b(?:vector|array|List|ArrayList|int\[\]|char\[\]|String\[\])[\w<>\[\],\s*&*]*\s+([A-Za-z_]\w*)\s*(?:=|\{)\s*\{([^{};]+)\}',
            r'\b([A-Za-z_]\w*)\s*=\s*\[([^\]\n]+)\]',
            r'\b([A-Za-z_]\w*)\s*=\s*\(([^)\n]+)\)',
            r'\b([A-Za-z_]\w*)\s*=\s*\{([^{}\n:]+)\}',
        ):
            for name, values in re.findall(pattern, snippet, re.MULTILINE):
                size = self._count_literal_items(values)
                key = (name, size)
                if size > 0 and key not in seen:
                    seen.add(key)
                    items.append({'name': name, 'size': size})
        return items

    def _count_literal_items(self, values):
        text = str(values or '').strip()
        if not text:
            return 0
        parts = []
        depth = 0
        quote = ''
        current = []
        for char in text:
            if quote:
                current.append(char)
                if char == quote:
                    quote = ''
                continue
            if char in ('"', "'"):
                quote = char
                current.append(char)
                continue
            if char in '([{':
                depth += 1
            elif char in ')]}' and depth > 0:
                depth -= 1
            if char == ',' and depth == 0:
                item = ''.join(current).strip()
                if item:
                    parts.append(item)
                current = []
            else:
                current.append(char)
        last = ''.join(current).strip()
        if last:
            parts.append(last)
        return len([part for part in parts if part and part not in ('...',)])

    def _find_dfs_function(self, code, language):
        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if not body:
                continue
            adjacency_loop = re.search(r'for\s+(\w+)\s+in\s+(\w+)\s*\[\s*(\w+)\s*\]', body)
            visited_add = re.search(r'(\w+)\.add\s*\(\s*(\w+)\s*\)', body)
            recursive_neighbor_call = bool(re.search(
                rf'\b{name}\s*\([^)]*\b{adjacency_loop.group(1)}\b[^)]*\)', body
            )) if adjacency_loop else False
            visited_guard = bool(re.search(
                r'if\s+\w+\s+not\s+in\s+\w+|if\s*\(\s*!\s*\w+\.has\s*\(', body
            ))
            if adjacency_loop and visited_add and recursive_neighbor_call and visited_guard:
                return {
                    'name': name,
                    'graph_param': adjacency_loop.group(2),
                    'node_param': visited_add.group(2),
                    'visited_param': visited_add.group(1),
                    'neighbor_var': adjacency_loop.group(1),
                    'params': self._function_param_names(code, name),
                }
        return None

    def _parse_graph_concrete_inputs(self, concrete_inputs, dfs):
        if concrete_inputs is None:
            return None
        data = concrete_inputs
        if isinstance(data, dict) and dfs['name'] in data and isinstance(data[dfs['name']], dict):
            data = data[dfs['name']]
        if not isinstance(data, dict):
            return None
        graph = data.get(dfs['graph_param']) or data.get('graph') or data.get('adj')
        node = data.get(dfs['node_param'])
        if node is None:
            node = data.get('node') or data.get('start') or data.get('source')
        visited = data.get(dfs['visited_param'], data.get('visited', []))
        if graph is None or node is None:
            return None
        if not isinstance(graph, (dict, list)):
            return None
        if visited is None:
            visited = []
        if isinstance(visited, (str, int, float, bool)):
            visited = [visited]
        if not isinstance(visited, (list, tuple, set)):
            visited = []
        return {'graph': graph, 'node': node, 'visited': visited}

    def _concrete_dfs_analysis(self, dfs, graph_inputs, limit=100_000):
        graph = graph_inputs['graph']
        start = graph_inputs['node']
        initial_visited = set(graph_inputs.get('visited') or [])
        visited = set(initial_visited)
        calls = 0
        edge_scans = 0
        max_depth = 0

        def graph_get(g, key):
            candidates = [key, str(key)]
            try:
                candidates.append(int(key))
            except (TypeError, ValueError):
                pass
            if isinstance(g, dict):
                for candidate in candidates:
                    if candidate in g:
                        return g[candidate] or []
                return []
            idx = None
            for candidate in candidates:
                if isinstance(candidate, int):
                    idx = candidate
                    break
            if idx is None or idx < 0 or idx >= len(g):
                return []
            return g[idx] or []

        def dfs_visit(node, depth):
            nonlocal calls, edge_scans, max_depth
            calls += 1
            if calls > limit or edge_scans > limit:
                raise RuntimeError('graph traversal limit exceeded')
            max_depth = max(max_depth, depth)
            visited.add(node)
            neighbors = graph_get(graph, node)
            for neighbor in neighbors:
                edge_scans += 1
                if neighbor not in visited:
                    dfs_visit(neighbor, depth + 1)

        try:
            dfs_visit(start, 1)
        except RuntimeError:
            return {
                'available': False, 'kind': 'dfs_exact',
                'function': dfs['name'],
                'reason': f'Concrete DFS exceeds safe simulation limit of {limit} steps'
            }
        return {
            'available': True, 'kind': 'dfs_exact',
            'function': dfs['name'],
            'inputs': {
                dfs['node_param']: start,
                dfs['visited_param']: list(initial_visited),
                'graph_vertices': len(graph),
            },
            'return_value': None,
            'calls': calls, 'max_stack_depth': max_depth,
            'reachable_vertices': len(visited - initial_visited),
            'edge_scans': edge_scans,
            'time': f"{calls} node visits, {edge_scans} adjacency checks",
            'space': f"{len(visited)} visited nodes, max recursion depth {max_depth}",
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': 'O(V + E)',
            'symbolic_space_complexity': 'O(V)',
            'reason': 'Exact concrete DFS simulation for the provided graph and start node'
        }

    def _find_bit_clear_function(self, code, language):
        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if not body:
                continue
            match = self._bit_clear_loop_match(body)
            if match:
                return {'name': name, 'param': match.group(1)}
        return None

    def _looks_like_bit_clear_loop(self, body):
        return bool(self._bit_clear_loop_match(body))

    def _bit_clear_loop_match(self, body):
        return re.search(
            r'while\s*\(?\s*(\w+)\s*>\s*0\s*\)?:?'
            r'(?:(?!\n\s*(?:def|function|public|private|protected)\b).)*?'
            r'(?:\b\1\s*=\s*\1\s*&\s*\(?\s*\1\s*-\s*1\s*\)?|\b\1\s*&=\s*\(?\s*\1\s*-\s*1\s*\)?)',
            body, re.IGNORECASE | re.DOTALL
        )

    def _parse_single_concrete_input(self, concrete_inputs, func_name, param):
        if concrete_inputs is None:
            return None
        if isinstance(concrete_inputs, (list, tuple)) and concrete_inputs:
            return self._one_int(concrete_inputs[0])
        if isinstance(concrete_inputs, dict):
            scoped = concrete_inputs.get(func_name)
            if scoped is not None:
                parsed = self._parse_single_concrete_input(scoped, func_name, param)
                if parsed is not None:
                    return parsed
            if param in concrete_inputs:
                return self._one_int(concrete_inputs[param])
            if 'n' in concrete_inputs:
                return self._one_int(concrete_inputs['n'])
            values = list(concrete_inputs.values())
            if values:
                return self._one_int(values[0])
        if isinstance(concrete_inputs, str):
            call_match = re.search(rf'\b{func_name}\s*\(\s*(-?\d+)\s*\)', concrete_inputs)
            if call_match:
                return self._one_int(call_match.group(1))
            named = dict(re.findall(r'\b([A-Za-z_]\w*)\s*[:=]\s*(-?\d+)', concrete_inputs))
            if param in named:
                return self._one_int(named[param])
            numbers = re.findall(r'-?\d+', concrete_inputs)
            if numbers:
                return self._one_int(numbers[0])
        return None

    def _find_literal_single_call_value(self, code, func_name):
        match = re.search(rf'\b{func_name}\s*\(\s*(-?\d+)\s*\)', code)
        return self._one_int(match.group(1)) if match else None

    def _one_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _concrete_bit_clear_analysis(self, bit_clear, value):
        iterations = bin(value).count('1') if value > 0 else 0
        return {
            'available': True, 'kind': 'bit_clear_exact',
            'function': bit_clear['name'],
            'inputs': {bit_clear['param']: value},
            'return_value': iterations,
            'calls': iterations, 'max_stack_depth': 1,
            'time': f"{iterations} loop iterations",
            'space': '1 counter/input variable',
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': 'O(popcount(n)), worst-case O(log n)',
            'symbolic_space_complexity': 'O(1)',
            'reason': 'Exact simulation for n = n & (n-1), which removes one set bit per loop'
        }

    def _find_ackermann_function(self, code, language):
        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if body and self._has_ackermann_recursion(name, body):
                return {'name': name, 'params': self._function_param_names(code, name)}
        return None

    def _function_param_names(self, code, func_name):
        signature = re.search(rf'\b{func_name}\s*\(([^)]*)\)', code)
        if not signature:
            return []
        params = []
        for raw in signature.group(1).split(','):
            raw = raw.strip()
            if not raw:
                continue
            name_match = re.search(r'([A-Za-z_]\w*)\s*(?:=.*)?$', raw)
            if name_match:
                params.append(name_match.group(1))
        return params

    def _parse_concrete_input_values(self, concrete_inputs, func_name, params):
        if concrete_inputs is None:
            return None
        if isinstance(concrete_inputs, (list, tuple)) and len(concrete_inputs) >= 2:
            return self._two_ints(concrete_inputs[0], concrete_inputs[1])
        if isinstance(concrete_inputs, dict):
            scoped = concrete_inputs.get(func_name)
            if scoped is not None:
                parsed = self._parse_concrete_input_values(scoped, func_name, params)
                if parsed:
                    return parsed
            if len(params) >= 2 and params[0] in concrete_inputs and params[1] in concrete_inputs:
                return self._two_ints(concrete_inputs[params[0]], concrete_inputs[params[1]])
            if 'm' in concrete_inputs and 'n' in concrete_inputs:
                return self._two_ints(concrete_inputs['m'], concrete_inputs['n'])
            values = list(concrete_inputs.values())
            if len(values) >= 2:
                return self._two_ints(values[0], values[1])
        if isinstance(concrete_inputs, str):
            call_match = re.search(rf'\b{func_name}\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', concrete_inputs)
            if call_match:
                return self._two_ints(call_match.group(1), call_match.group(2))
            named = {}
            for key, value in re.findall(r'\b([A-Za-z_]\w*)\s*[:=]\s*(-?\d+)', concrete_inputs):
                named[key] = value
            if len(params) >= 2 and params[0] in named and params[1] in named:
                return self._two_ints(named[params[0]], named[params[1]])
            if 'm' in named and 'n' in named:
                return self._two_ints(named['m'], named['n'])
            numbers = re.findall(r'-?\d+', concrete_inputs)
            if len(numbers) >= 2:
                return self._two_ints(numbers[0], numbers[1])
        return None

    def _find_literal_call_values(self, code, func_name):
        match = re.search(rf'\b{func_name}\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', code)
        return self._two_ints(match.group(1), match.group(2)) if match else None

    def _two_ints(self, first, second):
        try:
            return int(first), int(second)
        except (TypeError, ValueError):
            return None

    def _simulate_ackermann(self, m, n, call_limit=100000):
        if m < 0 or n < 0:
            return {'available': False, 'reason': 'Ackermann requires non-negative integer inputs'}
        calls = 0
        max_depth = 0

        def ack(a, b, depth):
            nonlocal calls, max_depth
            calls += 1
            max_depth = max(max_depth, depth)
            if calls > call_limit:
                raise RuntimeError('call limit exceeded')
            if a == 0:
                return b + 1
            if b == 0:
                return ack(a - 1, 1, depth + 1)
            inner = ack(a, b - 1, depth + 1)
            return ack(a - 1, inner, depth + 1)

        try:
            value = ack(m, n, 1)
        except (RecursionError, RuntimeError):
            return {
                'available': False, 'kind': 'ackermann_exact',
                'inputs': {'m': m, 'n': n},
                'reason': f'Exceeds safe simulation limit of {call_limit} calls'
            }
        return {'available': True, 'return_value': value, 'calls': calls, 'max_stack_depth': max_depth}

    # ─────────────────────────────────────────────
    # GRAPH ALGORITHM DETECTION
    # ─────────────────────────────────────────────

    def detect_graph_algorithm(self, code):
        # Bidirectional BFS
        if re.search(r'bidirectional.?bfs|bi.?bfs|meet.?in.?middle.*bfs|bfs.*meet.?in.?middle', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bidirectional BFS',
                'complexity': 'O(b^(d/2))', 'space': 'O(b^(d/2))',
                'reason': 'Two simultaneous BFS from source and target meet in middle',
                'can_optimize': False,
                'note': 'Optimal for unweighted shortest path when source and target are both known.'
            }
        # Johnson's Algorithm
        if re.search(r"johnson.?algorithm|johnson.?shortest|reweight.*johnson", code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Johnson's Algorithm",
                'complexity': 'O(V² log V + VE)', 'space': 'O(V + E)',
                'reason': 'Bellman-Ford once O(VE) + Dijkstra from each vertex O(V(V+E)log V)',
                'can_optimize': False,
                'note': 'Best all-pairs shortest paths for sparse graphs with negative weights.'
            }
        # Euler path / circuit
        if re.search(r'euler.?path|euler.?circuit|euler.?tour|hierholzer|fleury', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Eulerian Path/Circuit (Hierholzer's)",
                'complexity': 'O(V + E)', 'space': 'O(V + E)',
                'reason': "Hierholzer's visits every edge exactly once in O(E)",
                'can_optimize': False,
                'note': 'Already optimal.'
            }
        # Articulation points / bridges
        if re.search(r'articulation.?point|bridge.?find|cut.?vertex|biconnect', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Articulation Points / Bridges (Tarjan's)",
                'complexity': 'O(V + E)', 'space': 'O(V)',
                'reason': 'Single DFS with low-link values detects all bridges and cut vertices',
                'can_optimize': False, 'note': 'Already optimal — linear DFS-based detection.'
            }
        # Bipartite check
        if re.search(r'bipartite|two.?color|is.?bipartite|bfs.*color.*graph|color.*bfs.*graph', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bipartite Check (2-Coloring BFS/DFS)',
                'complexity': 'O(V + E)', 'space': 'O(V)',
                'reason': 'BFS/DFS with 2-coloring visits each vertex and edge once',
                'can_optimize': False, 'note': 'Already optimal.'
            }
        # Hopcroft-Karp
        if re.search(r'hopcroft.?karp|bipartite.*matching|maximum.*matching.*bipartite', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Hopcroft-Karp Bipartite Matching',
                'complexity': 'O(E√V)', 'space': 'O(V + E)',
                'reason': 'BFS finds augmenting paths in O(E) × O(√V) phases',
                'can_optimize': False, 'note': 'Already optimal for bipartite matching.'
            }
        # Hungarian
        if re.search(r'hungarian|assignment.?problem|kuhn.*munkres|munkres', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Hungarian Algorithm (Assignment Problem)',
                'complexity': 'O(n³)', 'space': 'O(n²)',
                'reason': 'O(n) phases, each finding augmenting path in O(n²) over n×n cost matrix',
                'can_optimize': False,
                'note': 'Already optimal for dense assignment. Use Jonker-Volgenant for sparse cases.'
            }
        # Dinic's max flow
        if re.search(r"dinic|dinics|dinic.?algorithm|level.?graph.*flow|blocking.?flow", code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Dinic's Max-Flow",
                'complexity': 'O(V²E)', 'space': 'O(V + E)',
                'reason': 'O(V) BFS phases × O(VE) blocking flow per phase → O(V²E)',
                'can_optimize': False,
                'note': 'O(E√V) on unit-capacity graphs. Faster than Edmonds-Karp in practice.'
            }
        # 2-SAT
        if re.search(r'\b2.?sat\b|two.?sat|implication.*graph.*scc|scc.*2sat', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': '2-SAT (Implication Graph + SCC)',
                'complexity': 'O(V + E)', 'space': 'O(V + E)',
                'reason': 'Build implication graph O(V+E), run SCC O(V+E), check satisfiability O(V)',
                'can_optimize': False,
                'note': 'Already optimal. 3-SAT is NP-complete; 2-SAT is solvable in linear time.'
            }
        # LCA
        if re.search(r'\blca\b|lowest.?common.?ancestor|sparse.?table.*lca|binary.?lifting.*lca', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Lowest Common Ancestor (Binary Lifting)',
                'complexity': 'O(n log n) preprocess, O(log n) query', 'space': 'O(n log n)',
                'reason': 'Binary lifting precomputes 2^k ancestors for each node in O(n log n)',
                'can_optimize': True, 'optimized_to': 'O(n) preprocess, O(1) query',
                'note': 'Farach-Colton & Bender achieves O(n) preprocess, O(1) query via Euler tour + RMQ.'
            }
        # Heavy-Light Decomposition
        if re.search(r'heavy.?light|hld|heavy.?path.?decomp', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Heavy-Light Decomposition',
                'complexity': 'O(n log n) build, O(log² n) query', 'space': 'O(n)',
                'reason': 'O(log n) heavy chains × O(log n) segment tree query per chain',
                'can_optimize': True, 'optimized_to': 'O(log n) query with Fenwick tree',
                'note': 'Using Fenwick tree instead of segment tree reduces query to O(log n).'
            }
        # Centroid Decomposition
        if re.search(r'centroid.?decomp|centroid.*tree', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Centroid Decomposition',
                'complexity': 'O(n log n)', 'space': 'O(n log n)',
                'reason': 'O(log n) levels of decomposition × O(n) work per level',
                'can_optimize': False, 'note': 'Already optimal for distance queries on trees.'
            }
        # Sparse table / RMQ
        if re.search(r'sparse.?table|rmq|range.?minimum.?query|range.?max.*query.*sparse', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Sparse Table (RMQ)',
                'complexity': 'O(n log n) build, O(1) query', 'space': 'O(n log n)',
                'reason': 'Precompute all 2^k range minima in O(n log n); queries O(1) via overlap',
                'can_optimize': False,
                'note': 'Already optimal for static RMQ. Use segment tree for dynamic updates.'
            }
        # Dijkstra
        if re.search(r'dijkstra|priorityqueue|priority_queue', code, re.IGNORECASE):
            if re.search(r'dist|distance', code, re.IGNORECASE):
                return {
                    'detected': True, 'algorithm': "Dijkstra's Shortest Path",
                    'complexity': 'O((V + E) log V)', 'space': 'O(V + E)',
                    'reason': 'Priority queue based graph traversal — O((V+E) log V)',
                    'can_optimize': False,
                    'note': 'Already optimal for non-negative weights and sparse graphs.'
                }
        # Bellman-Ford
        if re.search(r'bellman.?ford|relax', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bellman-Ford',
                'complexity': 'O(V × E)', 'space': 'O(V)',
                'reason': 'V-1 relaxation passes over all E edges',
                'can_optimize': True, 'optimized_to': 'O((V + E) log V)',
                'note': 'If no negative weights, replace with Dijkstra for O((V+E) log V).'
            }
        # Floyd-Warshall
        if re.search(r'floyd|warshall|all.?pairs', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Floyd-Warshall',
                'complexity': 'O(V³)', 'space': 'O(V²)',
                'reason': 'Triple nested loop over all vertex pairs',
                'can_optimize': True, 'optimized_to': 'O((V + E) log V) per source',
                'note': 'For sparse graphs, run Dijkstra from each vertex for better performance.'
            }
        # A*
        if re.search(r'\ba\s*\*\s*search\b|a_star|astar|heuristic.*path|path.*heuristic', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'A* Search',
                'complexity': 'O(E log V)', 'space': 'O(V)',
                'reason': 'Heuristic-guided priority-queue search',
                'can_optimize': False,
                'note': 'Complexity depends on heuristic quality. Optimal with admissible heuristic.'
            }
        # SCC
        if re.search(r'strongly.?connected|tarjan|kosaraju|scc', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'SCC (Tarjan/Kosaraju)',
                'complexity': 'O(V + E)', 'space': 'O(V)',
                'reason': 'Linear DFS-based SCC detection',
                'can_optimize': False, 'note': 'Already optimal.'
            }
        # Max-flow
        if re.search(r'max.?flow|ford.?fulkerson|edmonds.?karp|bfs.*flow|flow.*bfs', code, re.IGNORECASE):
            if self._looks_like_edmonds_karp_matrix_driver('', code, code, 'python'):
                return {
                    'detected': True, 'algorithm': 'Max-Flow (Edmonds-Karp, adjacency matrix)',
                    'complexity': 'O(V E²)', 'space': 'O(V^2)',
                    'reason': 'Edmonds-Karp uses O(VE) augmenting paths and an O(E) BFS per augmentation',
                    'can_optimize': True, 'optimized_to': "O(V²E) with Dinic's on adjacency lists",
                    'note': 'Use adjacency lists plus Dinic for better asymptotic behavior on sparse graphs.'
                }
            return {
                'detected': True, 'algorithm': 'Max-Flow (Edmonds-Karp)',
                'complexity': 'O(V E²)', 'space': 'O(V + E)',
                'reason': 'BFS augmenting paths × E iterations',
                'can_optimize': True, 'optimized_to': "O(V²E) with Dinic's",
                'note': "Dinic's algorithm gives O(V²E) which is better on unit-capacity graphs."
            }
        # Repeated DFS with a fresh visited set for every start node
        if self._looks_like_repeated_fresh_graph_search(code, 'dfs'):
            return {
                'detected': True, 'algorithm': 'Repeated DFS from All Nodes',
                'complexity': 'O(V * (V + E))', 'space': 'O(V)',
                'reason': 'Outer loop starts DFS with a fresh visited set for each vertex, so traversal work can repeat from every start node',
                'can_optimize': True, 'optimized_to': 'O(V + E)',
                'note': 'Reuse one visited set across the outer loop when you only need graph traversal/components.'
            }
        # BFS
        if re.search(r'\bqueue\b|deque|bfs|breadth.?first', code, re.IGNORECASE):
            if re.search(r'visited|seen|graph|adj', code, re.IGNORECASE):
                return {
                    'detected': True, 'algorithm': 'Breadth-First Search (BFS)',
                    'complexity': 'O(V + E)', 'space': 'O(V)',
                    'reason': 'Each vertex and edge visited once',
                    'can_optimize': False, 'note': 'BFS is already optimal for unweighted shortest paths.'
                }
        # DFS
        if re.search(r'\bdfs\b|depth.?first|visited\s*=', code, re.IGNORECASE):
            if re.search(r'graph|adj|neighbor', code, re.IGNORECASE):
                return {
                    'detected': True, 'algorithm': 'Depth-First Search (DFS)',
                    'complexity': 'O(V + E)', 'space': 'O(V)',
                    'reason': 'Each vertex and edge visited once',
                    'can_optimize': False, 'note': 'DFS is already optimal for graph traversal.'
                }
        # Kruskal
        if re.search(r'kruskal|union.?find|disjoint', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Kruskal's MST",
                'complexity': 'O(E log E)', 'space': 'O(V)',
                'reason': 'Sorting edges O(E log E) + Union-Find operations',
                'can_optimize': False,
                'note': "Already optimal. Prim's with priority queue is better for dense graphs."
            }
        # Prim
        if re.search(r"\bprim(?:_?mst|'?s)?\b|minimum.?spanning", code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Prim's MST",
                'complexity': 'O((V + E) log V)', 'space': 'O(V)',
                'reason': 'Priority queue based MST construction',
                'can_optimize': False, 'note': 'Already optimal for sparse graphs.'
            }
        # Topological sort
        if re.search(r'topological|topo.?sort|in.?degree|kahn', code, re.IGNORECASE):
            if re.search(r'in.?degree|indegree|queue.*topo|topo.*queue', code, re.IGNORECASE):
                return {
                    'detected': True, 'algorithm': "Topological Sort (Kahn's BFS)",
                    'complexity': 'O(V + E)', 'space': 'O(V)',
                    'reason': "Kahn's: O(V) queue operations + O(E) edge relaxations",
                    'can_optimize': False, 'note': 'Already optimal for DAG ordering.'
                }
            return {
                'detected': True, 'algorithm': 'Topological Sort (DFS)',
                'complexity': 'O(V + E)', 'space': 'O(V)',
                'reason': 'Each vertex and edge processed once in DFS post-order',
                'can_optimize': False, 'note': 'Already optimal.'
            }
        return {'detected': False}

    # ─────────────────────────────────────────────
    # KNOWN ALGORITHM DETECTION
    # ─────────────────────────────────────────────

    def detect_known_algorithm(self, code):
        # Generator T(n)=T(n-1)+T(n/2)
        if re.search(r'yield\s*\*', code, re.IGNORECASE):
            for name in re.findall(r'function\s*\*\s*(\w+)', code):
                body = self._extract_function_body(code, name, 'javascript')
                if not body:
                    continue
                has_dec = bool(re.search(rf'yield\s*\*\s*{name}\s*\([^)]*-\s*1', body))
                has_half = bool(re.search(rf'yield\s*\*\s*{name}\s*\([^)]*(?:Math\.floor|/\s*2)', body))
                if has_dec and has_half:
                    return {
                        'detected': True,
                        'algorithm': 'Generator recursion T(n)=T(n-1)+T(n/2)',
                        'complexity': 'O(2^n)', 'space': 'O(2^n)',
                        'reason': 'T(n-1) dominates and creates exponentially many generator frames',
                        'can_optimize': True, 'optimized_to': 'O(n)',
                        'note': 'Replace the generator with a memoized plain function.'
                    }

        # Fibonacci (named or explicit)
        if re.search(r'fibonacci|fib\s*\(|fib\s*\[', code, re.IGNORECASE):
            has_memo = bool(re.search(r'memo|cache|@lru_cache|@cache|dp\s*=', code, re.IGNORECASE))
            has_matrix = bool(re.search(r'matrix.*fib|fib.*matrix|matrix.*exp', code, re.IGNORECASE))
            if has_matrix:
                return {
                    'detected': True, 'algorithm': 'Fibonacci via Matrix Exponentiation',
                    'complexity': 'O(log n)', 'space': 'O(log n)',
                    'reason': '[[1,1],[1,0]]^n gives nth Fibonacci in O(log n) matrix multiplications',
                    'can_optimize': False,
                    'note': 'Already optimal. Binet formula gives O(1) but has floating-point precision issues.'
                }
            if has_memo:
                return {
                    'detected': True, 'algorithm': 'Fibonacci (Memoized/DP)',
                    'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'Memoization ensures each subproblem computed once',
                    'can_optimize': True, 'optimized_to': 'O(log n)',
                    'note': 'Can be further optimized to O(log n) using matrix exponentiation.'
                }

        # Meet in the middle
        if re.search(r'meet.?in.?middle|meet.?in.?the.?middle|half.*subset.*sum|split.*half.*search', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Meet in the Middle',
                'complexity': 'O(2^(n/2))', 'space': 'O(2^(n/2))',
                'reason': 'Split into halves: 2^(n/2)+2^(n/2) subproblems joined via sorting/hashing',
                'can_optimize': False,
                'note': 'Optimal for exponential problems that can be split. Square root of brute force O(2^n).'
            }

        # DSU / Union-Find
        if re.search(r'union.?find|dsu|disjoint.?set|path.?compress|union.?by.?rank|find_parent|find_root', code, re.IGNORECASE) or self._looks_like_union_find(code):
            return {
                'detected': True, 'algorithm': 'Disjoint Set Union (Union-Find)',
                'complexity': 'O(α(n))', 'space': 'O(n)',
                'reason': 'Path compression + union by rank gives amortized O(α(n)) ≈ O(1) per operation',
                'can_optimize': False,
                'note': 'Already optimal — inverse Ackermann α(n) ≤ 4 for all practical n.'
            }

        # Matrix exponentiation
        if re.search(r'matrix.?exp|matpow|mat_pow|matrix.*power|fast.?matrix.?mul', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Matrix Exponentiation',
                'complexity': 'O(k³ log n)', 'space': 'O(k²)',
                'reason': 'Binary exponentiation on k×k matrices: O(log n) multiplications each O(k³)',
                'can_optimize': False,
                'note': 'Used for linear recurrences in O(k³ log n). Essential for fast Fibonacci, tiling DPs.'
            }

        # Suffix array
        if re.search(r'suffix.?array|suffix_array|sa.?is|dc3.?algorithm|skew.?algorithm', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Suffix Array',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Comparison-based construction with O(n log n) radix sort on doubled suffixes',
                'can_optimize': True, 'optimized_to': 'O(n)',
                'note': 'DC3/Skew algorithm achieves O(n) construction. Combine with LCP array for O(1) LCP queries.'
            }

        # Suffix automaton / DAWG
        if re.search(r'suffix.?automat|sam\b|dawg\b|suffix.*state.*last', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Suffix Automaton (SAM / DAWG)',
                'complexity': 'O(n)', 'space': 'O(n)',
                'reason': 'Online linear-time construction — at most 2n-1 states and 3n-4 transitions',
                'can_optimize': False,
                'note': 'Already optimal. Represents all substrings in O(n) space.'
            }

        # Aho-Corasick
        if re.search(r'aho.?corasick|aho_corasick|trie.*failure|failure.*link.*trie', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Aho-Corasick Multi-Pattern Search',
                'complexity': 'O(n + m + z)', 'space': 'O(m × σ)',
                'reason': 'Build trie O(m), failure links O(m), search text O(n+z) where z=occurrences',
                'can_optimize': False, 'note': 'Already optimal for multiple-pattern search.'
            }

        # Manacher's algorithm
        if re.search(r"manacher|manachers|palindrome.*o.?n|longest.*palindrome.*linear", code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Manacher's Algorithm",
                'complexity': 'O(n)', 'space': 'O(n)',
                'reason': 'Linear-time longest palindromic substring via center expansion with reuse',
                'can_optimize': False, 'note': 'Already optimal for palindrome detection.'
            }

        # LIS
        if re.search(r'\blis\b|longest.?increasing.?subseq|patience.?sort.*lis|bisect.*lis', code, re.IGNORECASE):
            has_nlogn = bool(re.search(r'bisect|binary.?search.*lis|tails\s*=', code, re.IGNORECASE))
            if has_nlogn:
                return {
                    'detected': True, 'algorithm': 'LIS (Patience Sorting / Binary Search)',
                    'complexity': 'O(n log n)', 'space': 'O(n)',
                    'reason': 'Binary search on tails array — O(n) elements × O(log n) lookup',
                    'can_optimize': False, 'note': 'Already optimal.'
                }
            return {
                'detected': True, 'algorithm': 'LIS (DP)',
                'complexity': 'O(n²)', 'space': 'O(n)',
                'reason': 'For each element, check all previous — O(n) per element',
                'can_optimize': True, 'optimized_to': 'O(n log n)',
                'note': 'Use patience sorting with binary search (bisect) for O(n log n).'
            }

        # Coin change / Unbounded knapsack
        if re.search(r'coin.?change|unbounded.?knapsack|min.?coins|fewest.?coins', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Coin Change / Unbounded Knapsack (DP)',
                'complexity': 'O(n × W)', 'space': 'O(W)',
                'reason': 'DP table: n coin denominations × W target amount',
                'can_optimize': False, 'note': 'Already optimal as pseudo-polynomial.'
            }

        # 0/1 Knapsack
        if re.search(r'0.?1.?knapsack|zero.?one.?knapsack|01.?knap', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': '0/1 Knapsack (DP)',
                'complexity': 'O(n × W)', 'space': 'O(n × W)',
                'reason': 'DP table: n items × W capacity',
                'can_optimize': True, 'optimized_to': 'O(n × W) with O(W) space',
                'note': 'Space can be reduced to O(W) by iterating capacity in reverse (1D DP).'
            }

        # Word break
        if re.search(r'word.?break|wordbreak|word_break', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Word Break (DP)',
                'complexity': 'O(n² × m)', 'space': 'O(n)',
                'reason': 'O(n²) substrings × O(m) dictionary lookup per substring',
                'can_optimize': True, 'optimized_to': 'O(n × L × m)',
                'note': 'Use trie for O(L) word lookup instead of O(m).'
            }

        # Regex / wildcard matching DP
        if re.search(r'regex.?match|regexp.?dp|isMatch.*\.\*|dp.*regex|wildcard.?match', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Regex / Wildcard Matching (DP)',
                'complexity': 'O(n × m)', 'space': 'O(n × m)',
                'reason': 'DP over all n×m pairs of text position and pattern position',
                'can_optimize': True, 'optimized_to': 'O(n × m) with O(m) space',
                'note': 'Space reducible to O(m) with rolling DP rows.'
            }

        # Bitmask DP
        if re.search(r'bitmask.?dp|dp.*1\s*<<|1\s*<<.*dp\[|visited.*bitmask|bitmask.*visited', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bitmask DP',
                'complexity': 'O(n² × 2^n)', 'space': 'O(n × 2^n)',
                'reason': '2^n subset states × n ending positions × O(n) transition',
                'can_optimize': False, 'note': 'Standard approach for TSP and subset covering. Practical up to n≈20.'
            }

        # Convex hull trick / CHT
        if re.search(r'convex.?hull.?trick|cht\b|li.?chao|line.*container|slope.?trick', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Convex Hull Trick / Li Chao Tree DP Optimization',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'CHT reduces O(n²) DP transition to O(n log n) via convex hull of lines',
                'can_optimize': False, 'note': 'Already optimal. O(n) if queries are monotone.'
            }

        # Miller-Rabin
        if re.search(r'miller.?rabin|miller_rabin|primality.*probabilistic|strong.*witness', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Miller-Rabin Primality Test',
                'complexity': 'O(k log² n)', 'space': 'O(1)',
                'reason': 'k witnesses × O(log n) modular exponentiations × O(log n) per multiplication',
                'can_optimize': False, 'note': 'k=7 witnesses gives deterministic result for n < 3.3×10²⁴.'
            }

        # Extended GCD
        if re.search(r'extended.?gcd|ext.?gcd|bezout|extended_euclidean', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Extended Euclidean Algorithm',
                'complexity': 'O(log min(a,b))', 'space': 'O(log min(a,b))',
                'reason': 'Same as GCD — each step reduces min(a,b) by Fibonacci ratio',
                'can_optimize': False, 'note': 'Already optimal. Used for modular inverse.'
            }

        # CRT
        if re.search(r'chinese.?remainder|crt\b|crt_combine|garner', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Chinese Remainder Theorem',
                'complexity': 'O(k log M)', 'space': 'O(k)',
                'reason': 'k modular equations × O(log M) extended GCD per equation',
                'can_optimize': False, 'note': "Already optimal. Garner's algorithm avoids big-integer arithmetic."
            }

        # Pollard's rho
        if re.search(r'pollard.?rho|pollard_rho|rho.*factor', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Pollard's Rho Factorization",
                'complexity': 'O(n^(1/4))', 'space': 'O(1)',
                'reason': 'Expected O(n^(1/4)) iterations by birthday paradox on pseudorandom cycle',
                'can_optimize': False,
                'note': 'Best practical algorithm for semi-primes. Combine with Miller-Rabin for robust factorization.'
            }

        # Strassen
        if re.search(r'strassen', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Strassen's Matrix Multiplication",
                'complexity': 'O(n^2.807)', 'space': 'O(n²)',
                'reason': '7T(n/2)+O(n²) → T(n)=O(n^log₂7) ≈ O(n^2.807)',
                'can_optimize': False,
                'note': 'Better than naive O(n³). Coppersmith-Winograd O(n^2.376) exists but is impractical.'
            }

        # Karatsuba
        if re.search(r'karatsuba|karatsuba_multiply|karatsuba_mult', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Karatsuba Multiplication',
                'complexity': 'O(n^1.585)', 'space': 'O(n log n)',
                'reason': '3T(n/2)+O(n) → O(n^log₂3) ≈ O(n^1.585)',
                'can_optimize': False,
                'note': 'Already faster than O(n²). For very large integers, use FFT-based multiplication O(n log n).'
            }

        # FFT
        if re.search(r'\bfft\b|fast_fourier|fastfourier|cooley.?tukey|butterfly.*fft|fft.*butterfly', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Fast Fourier Transform (FFT)',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Cooley-Tukey: 2T(n/2)+O(n) → O(n log n)',
                'can_optimize': False,
                'note': 'Already optimal for DFT. Ensure input size is power of 2 for maximum efficiency.'
            }

        # NTT
        if re.search(r'\bntt\b|number.?theoretic.?transform|modular.*fft', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Number Theoretic Transform (NTT)',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'FFT over modular arithmetic — same divide-and-conquer structure as FFT',
                'can_optimize': False,
                'note': 'Use for exact polynomial multiplication modulo a prime. Avoids FFT floating-point errors.'
            }

        # Huffman
        if re.search(r'huffman|huffman_code|huffman_tree|huffman_encode', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Huffman Coding',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Build min-heap O(n), extract-insert n times each O(log n) → O(n log n)',
                'can_optimize': False, 'note': 'Already optimal for greedy prefix-free encoding.'
            }

        # Activity Selection
        if re.search(r'activity.?select|interval.?schedul|job.?schedul|greedy.*interval|finish.?time.*sort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Activity Selection / Interval Scheduling',
                'complexity': 'O(n log n)', 'space': 'O(1)',
                'reason': 'Dominant cost is sorting activities by finish time: O(n log n)',
                'can_optimize': False, 'note': 'Already optimal. If pre-sorted, reduce to O(n).'
            }

        # Sudoku Solver
        if re.search(r'sudoku|solve_sudoku|solveSudoku|is_valid.*board|board.*backtrack', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Sudoku Solver (Backtracking)',
                'complexity': 'O(9^m)', 'space': 'O(m)',
                'reason': 'Up to 9 choices for each of m empty cells — exponential backtracking tree',
                'can_optimize': True, 'optimized_to': 'Pruned exponential (constraint propagation)',
                'note': 'Add constraint propagation (arc consistency / naked singles) to dramatically prune the search space.'
            }

        # Randomized QuickSort
        if re.search(r'randomized.?quick|random.*pivot|rand.*partition|shuffle.*sort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Randomized QuickSort',
                'complexity': 'O(n log n)', 'space': 'O(log n)',
                'reason': 'Random pivot gives expected O(n log n) — eliminates adversarial O(n²) worst case',
                'can_optimize': False, 'note': 'No worst-case guarantee; use Introsort for guaranteed O(n log n).'
            }

        # Monte Carlo
        if re.search(r'monte.?carlo|montecarlo|random.*sample.*estimate|pi.*random|estimate.*pi', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Monte Carlo Algorithm',
                'complexity': 'O(n)', 'space': 'O(1)',
                'reason': 'Linear in number of random samples; probabilistic correctness',
                'can_optimize': False, 'note': 'Error decreases as O(1/√n). Increase sample count to improve accuracy.'
            }

        # Las Vegas
        if re.search(r'las.?vegas|lasvegas|always.?correct.*random|random.*always.?correct', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Las Vegas Algorithm',
                'complexity': 'O(expected)', 'space': 'O(1)',
                'reason': 'Always produces correct result; runtime is random with finite expected value',
                'can_optimize': False,
                'note': 'Correctness is guaranteed. Expected runtime depends on probability of success per trial.'
            }

        # AVL Tree
        if re.search(r'\bavl\b|avl.?tree|avl_tree|left.?rotate.*right.?rotate|balance.?factor.*avl', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'AVL Tree',
                'complexity': 'O(log n)', 'space': 'O(n)',
                'reason': 'Height-balanced BST guarantees O(log n) insert, delete, search via rotations',
                'can_optimize': False,
                'note': 'Already optimal. Red-Black Trees have fewer rotations but same asymptotic complexity.'
            }

        # Red-Black Tree
        if re.search(r'red.?black|redblack|rb.?tree|rbtree|color.*red.*black|black.*height', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Red-Black Tree',
                'complexity': 'O(log n)', 'space': 'O(n)',
                'reason': 'Self-balancing BST — O(log n) ops with at most 2 rotations per insert',
                'can_optimize': False, 'note': 'Already optimal. Preferred over AVL when insertions/deletions dominate.'
            }

        # Splay Tree
        if re.search(r'splay.?tree|splay\s*\(|splay_tree', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Splay Tree',
                'complexity': 'O(log n) amortized', 'space': 'O(n)',
                'reason': 'Splay operation brings accessed node to root — O(log n) amortized',
                'can_optimize': False,
                'note': 'O(log n) amortized, O(n) worst-case per op. Excellent cache locality for non-uniform access.'
            }

        # Treap
        if re.search(r'\btreap\b|treap.?node|tree.*heap.*bst|bst.*heap.*rand', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Treap (Randomized BST)',
                'complexity': 'O(log n) expected', 'space': 'O(n)',
                'reason': 'Random priorities maintain expected O(log n) height with high probability',
                'can_optimize': False,
                'note': 'Split and merge in O(log n). Simpler than Red-Black Trees with same expected bounds.'
            }

        # Skip List
        if re.search(r'skip.?list|skiplist|skip_list', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Skip List',
                'complexity': 'O(log n) expected', 'space': 'O(n log n) expected',
                'reason': 'Randomized multi-level linked list — O(log n) expected levels traversed per op',
                'can_optimize': False, 'note': 'O(log n) expected for search/insert/delete.'
            }

        # B-Tree / B+-Tree
        if re.search(r'\bb.?tree\b|btree|b_tree|b\+tree|b\+.?tree|bplus', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'B-Tree / B+-Tree',
                'complexity': 'O(log_t n)', 'space': 'O(n)',
                'reason': 'Height O(log_t n) where t is minimum degree — each node has 2t-1 keys',
                'can_optimize': False,
                'note': 'Optimal for disk-based storage with large t reducing I/O. Used in databases and file systems.'
            }

        # Bloom Filter
        if re.search(r'bloom.?filter|bloomfilter', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bloom Filter',
                'complexity': 'O(k)', 'space': 'O(m)',
                'reason': 'k hash functions applied per insert/query — O(k) time, O(m) bits space',
                'can_optimize': False, 'note': 'No false negatives. Optimal k = (m/n) ln 2.'
            }

        # Van Emde Boas tree
        if re.search(r'van.?emde.?boas|veb.?tree|veb\b', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Van Emde Boas Tree',
                'complexity': 'O(log log U)', 'space': 'O(U)',
                'reason': 'Recursive structure on universe U: T(U)=T(√U)+O(1) → O(log log U)',
                'can_optimize': False,
                'note': 'Fastest for integer keys in [0, U). Impractical for large U due to O(U) space.'
            }

        # Fibonacci Heap
        if re.search(r'fibonacci.?heap|fib.?heap|fibheap|decrease.?key.*fibonacci', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Fibonacci Heap',
                'complexity': 'O(log n)', 'space': 'O(n)',
                'reason': 'Amortized O(1) insert/decrease-key, O(log n) amortized delete-min via lazy consolidation',
                'can_optimize': False,
                'note': 'Theoretically optimal for Dijkstra but high constant factors make binary heaps faster in practice.'
            }

        # Hash Table
        if re.search(r'hash.?table|hashtable|open.?addressing|linear.?probing|chaining.*hash|separate.?chaining|load.?factor', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Hash Table',
                'complexity': 'O(1) average, O(n) worst', 'space': 'O(n)',
                'reason': 'Average O(1) with good hash and low load factor; worst-case O(n) on collisions',
                'can_optimize': True, 'optimized_to': 'O(1) average with good hash function',
                'note': 'Keep load factor below 0.7. Use a universal hash function to minimize collision probability.'
            }

        # Boyer-Moore
        if re.search(r'boyer.?moore|boyermoore|bad.?character|good.?suffix', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Boyer-Moore String Search',
                'complexity': 'O(n/m) best, O(nm) worst', 'space': 'O(m + σ)',
                'reason': 'Bad-character and good-suffix heuristics enable sublinear average-case scanning',
                'can_optimize': False,
                'note': 'Fastest practical string search on large alphabets. Use KMP for adversarial input.'
            }

        # Trie
        if re.search(r'\btrie\b|prefix.?tree|trie.?node|trienode|trie.?insert|trie.?search', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Trie (Prefix Tree)',
                'complexity': 'O(m)', 'space': 'O(n × m × σ)',
                'reason': 'Insert/search/delete each traverse at most m nodes (key length m)',
                'can_optimize': False,
                'note': 'O(m) is optimal for prefix operations. Use compressed tries for space reduction.'
            }

        # Convex Hull
        if re.search(r'convex.?hull|graham.?scan|jarvis|chan.*convex|cross.?product.*hull', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Convex Hull (Graham Scan / Jarvis March)',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Sort points O(n log n) + linear scan O(n) → O(n log n)',
                'can_optimize': False,
                'note': "Chan's algorithm achieves O(n log h) where h = hull size."
            }

        # Closest Pair
        if re.search(r'closest.?pair|nearest.?pair|closest_pair|min.?distance.*points|strip.*closest', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Closest Pair of Points',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Divide and conquer: T(n)=2T(n/2)+O(n log n) → O(n log n) with presorted y',
                'can_optimize': False,
                'note': 'Ensure y-coordinates are presorted before recursion to avoid O(n log² n).'
            }

        # Line Segment Intersection
        if re.search(r'line.?intersection|sweep.?line|segment.?intersect|bentley.?ottmann|event.?queue.*segment', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Line Segment Intersection (Sweep Line)',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'Bentley-Ottmann sweep: O((n+k) log n) where k=intersections',
                'can_optimize': False,
                'note': 'For all k intersections: O((n+k) log n). Use balanced BST for active segment order.'
            }

        # Newton's Method
        if re.search(r'newton.?method|newtons_method|newton_raphson|raphson|f_prime.*newton|derivative.*iterate', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Newton's Method (Newton-Raphson)",
                'complexity': 'O(log n)', 'space': 'O(1)',
                'reason': 'Quadratic convergence: each iteration doubles correct digits → O(log n) iterations',
                'can_optimize': False,
                'note': 'Converges quadratically near root. Diverges if starting far from root or at an inflection point.'
            }

        # Gaussian Elimination
        if re.search(r'gaussian.?elim|gauss.?elim|row.?echelon|back.?substitution|pivot.*matrix.*solve', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Gaussian Elimination',
                'complexity': 'O(n³)', 'space': 'O(n²)',
                'reason': 'Three nested loops over n×n matrix — O(n³) floating-point operations',
                'can_optimize': True, 'optimized_to': 'O(n^2.376) theoretical',
                'note': 'Use LU decomposition for multiple RHS vectors. Strassen-based methods give O(n^2.807) but impractical.'
            }

        # LU Decomposition
        if re.search(r'\blu\b.*decomp|lu_decomp|ludecomp|lower.?upper.*decomp|l.*u.*factori', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'LU Decomposition',
                'complexity': 'O(n³)', 'space': 'O(n²)',
                'reason': 'Factorizes n×n matrix into L and U — same operation count as Gaussian elimination',
                'can_optimize': False,
                'note': 'Preferred over Gaussian when solving Ax=b for multiple b vectors.'
            }

        # Fast Exponentiation
        if re.search(r'fast.?exp|binary.?exp|power.*mod|modpow|mod_pow|exponentiation.?by.?squaring|square.*multiply', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Fast Exponentiation (Binary Exponentiation)',
                'complexity': 'O(log n)', 'space': 'O(1)',
                'reason': 'Halves exponent on each step via repeated squaring → O(log n) multiplications',
                'can_optimize': False, 'note': 'Already optimal. Essential for modular arithmetic in cryptography.'
            }

        # RSA
        if re.search(r'\brsa\b|rsa_encrypt|rsa_decrypt|rsa_keygen|phi.*euler.*rsa|public.?key.*private.?key', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'RSA Cryptography',
                'complexity': 'O(k³)', 'space': 'O(k)',
                'reason': 'Key generation: O(k²) modular exponentiation × primality tests; encryption O(k²) with k-bit keys',
                'can_optimize': False,
                'note': 'Use k ≥ 2048 bits for modern security. Use optimized libraries (OpenSSL) in production.'
            }

        # Diffie-Hellman
        if re.search(r'diffie.?hellman|dh.?key.?exchange|discrete.?log.*dh|dh_shared', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Diffie-Hellman Key Exchange',
                'complexity': 'O(log p)', 'space': 'O(1)',
                'reason': 'Dominant operation: modular exponentiation g^a mod p — O(log p) multiplications',
                'can_optimize': False,
                'note': 'Use prime p ≥ 2048 bits. Prefer ECDH for same security with smaller keys.'
            }

        # AES
        if re.search(r'\baes\b|aes_encrypt|aes_decrypt|sub.?bytes|mix.?columns|shift.?rows|add.?round.?key', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'AES (Advanced Encryption Standard)',
                'complexity': 'O(n)', 'space': 'O(1)',
                'reason': 'Each block processed in fixed rounds (10/12/14) — linear in message length n',
                'can_optimize': False,
                'note': 'Use hardware AES-NI instructions. Never implement from scratch in production.'
            }

        # SHA
        if re.search(r'\bsha\b|sha256|sha512|sha_hash|message.?digest|sha.?1|sha.?2|sha.?3', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'SHA Hash Function',
                'complexity': 'O(n)', 'space': 'O(1)',
                'reason': 'Processes message in fixed-size chunks — linear in input length n',
                'can_optimize': False, 'note': 'Use SHA-256 or SHA-3. MD5/SHA-1 are cryptographically broken.'
            }

        # Gradient Descent / SGD
        if re.search(r'gradient.?descent|grad_descent|learning.?rate.*gradient|sgd|stochastic.?gradient|adam.?optim|rmsprop', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Gradient Descent / SGD',
                'complexity': 'O(iterations × n)', 'space': 'O(n)',
                'reason': 'Each iteration computes gradient over n parameters/data points',
                'can_optimize': True, 'optimized_to': 'O(iterations × batch_size)',
                'note': 'Use mini-batch SGD to reduce per-iteration cost. Adam/RMSProp often converge in fewer iterations.'
            }

        # Simulated Annealing
        if re.search(r'simulated.?anneal|annealing|temperature.*cool|cooling.?schedule|metropolis.*accept', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Simulated Annealing',
                'complexity': 'O(iterations)', 'space': 'O(1)',
                'reason': 'Probabilistic metaheuristic — runtime proportional to cooling schedule iterations',
                'can_optimize': False, 'note': 'Tune initial temperature and cooling rate. No optimality guarantee.'
            }

        # Genetic Algorithm
        if re.search(r'genetic.?algorithm|genetic_algo|population.*fitness|crossover.*mutate|evolve.*generation|chromosome.*fitness', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Genetic Algorithm',
                'complexity': 'O(generations × population × fitness_cost)', 'space': 'O(population)',
                'reason': 'Each generation evaluates entire population',
                'can_optimize': False,
                'note': 'No convergence guarantee to global optimum. Population size controls exploration/exploitation.'
            }

        # Linear Regression
        if re.search(r'linear.?regression|least.?squares|ols\b|normal.?equation.*regression|fit.*slope.*intercept', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Linear Regression (OLS)',
                'complexity': 'O(n × d²)', 'space': 'O(d²)',
                'reason': 'Normal equations require O(nd²) for XᵀX and O(d³) for inversion',
                'can_optimize': True, 'optimized_to': 'O(n × d) with iterative gradient descent',
                'note': 'For large d, use gradient descent O(nd) per iteration.'
            }

        # Decision Tree
        if re.search(r'decision.?tree|gini.?impurity|information.?gain.*split|entropy.*split|best.?split.*feature', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Decision Tree',
                'complexity': 'O(n log n × d)', 'space': 'O(n)',
                'reason': 'At O(log n) depth levels, evaluate d features across n samples',
                'can_optimize': False, 'note': 'Pre-sort features once O(nd log n). Limit max_depth to prevent overfitting.'
            }

        # Random Forest
        if re.search(r'random.?forest|random_forest|bagging.*trees|bootstrap.*aggregate|n_estimators', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Random Forest',
                'complexity': 'O(k × n log n × d)', 'space': 'O(k × n)',
                'reason': 'k trees each trained in O(n log n × d) with random feature subset',
                'can_optimize': True, 'optimized_to': 'O(k × n log n × √d)',
                'note': 'Parallelise tree training. Use √d features per split — improves accuracy too.'
            }

        # Neural Network
        if re.search(r'neural.?network|backprop|back.?propag|forward.?pass|activation.*relu|sigmoid.*layer|dense.*layer|weight.*bias.*learn', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Neural Network (Backpropagation)',
                'complexity': 'O(epochs × n × L × w)', 'space': 'O(L × w)',
                'reason': 'Each epoch: forward + backward pass over n samples × L layers × w weights',
                'can_optimize': True, 'optimized_to': 'O(epochs × batch × L × w) with mini-batch SGD',
                'note': 'Use GPU parallelism. Mini-batch training dramatically reduces per-step cost.'
            }

        # Branch and Bound — TSP
        if re.search(r'branch.?and.?bound|branch_bound|bnb.?tsp|tsp.*exact.*bound|bound.*prune.*tsp', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Branch and Bound (TSP Exact)',
                'complexity': 'O(n!)', 'space': 'O(n²)',
                'reason': 'Exponential search space — worst case explores all permutations, pruned by lower bound',
                'can_optimize': True, 'optimized_to': 'O(n² × 2^n) with bitmask DP (Held-Karp)',
                'note': 'Replace with Held-Karp DP for exact TSP: O(n² × 2^n) far better than O(n!) in practice.'
            }

        # Lazy Propagation
        if re.search(r'lazy.?prop|lazy_prop|lazy.*segment|segment.*lazy|pending.*update.*tree|push.?down.*lazy', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Segment Tree with Lazy Propagation',
                'complexity': 'O(log n)', 'space': 'O(n)',
                'reason': 'Lazy tags defer range updates — each range update/query O(log n) amortized',
                'can_optimize': False, 'note': 'Already optimal for range-update range-query problems.'
            }

        # Dynamic Array (Amortized)
        if self._looks_like_dynamic_array_doubling(code) or re.search(r'dynamic.?array|amortized|amortised|vector.*push_back.*realloc', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Dynamic Array (Amortized Append)',
                'complexity': 'O(n)', 'space': 'O(n)',
                'reason': 'Dynamic-array doubling: resizes copy 1+2+4+...+n elements total = O(n), so n appends are O(n) total and O(1) amortized each',
                'can_optimize': False, 'note': 'Already optimal. Pre-reserve capacity if final size is known.'
            }

        # Bitwise Algorithms
        if re.search(r'bit.?manipul|bitwise.?trick|popcount|bit.?count|lowest.?set.?bit|highest.?set.?bit|hamming.?weight|bit.?reversal', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bitwise Algorithm',
                'complexity': 'O(log n) to O(1)', 'space': 'O(1)',
                'reason': 'Bit-level operations on w-bit words run in O(1) per word; loop variants O(popcount) or O(log n)',
                'can_optimize': False,
                'note': 'Hardware popcount makes popcount(n) O(1). Use n & (n-1) to clear lowest set bit.'
            }

        # Two Pointers
        if self._looks_like_two_pointers(code):
            return {
                'detected': True, 'algorithm': 'Two Pointers',
                'complexity': 'O(n)', 'space': 'O(1)',
                'reason': 'Two pointers traverse array at most once each — total O(n) movements',
                'can_optimize': False, 'note': 'Already optimal for sorted-array pair/partition problems.'
            }

        # Sliding Window
        if self._looks_like_sliding_window(code):
            return {
                'detected': True, 'algorithm': 'Sliding Window',
                'complexity': 'O(n)', 'space': 'O(1)',
                'reason': 'Window expands and contracts — each element added and removed at most once → O(n)',
                'can_optimize': False, 'note': 'Already optimal for contiguous subarray/substring problems.'
            }

        # Prefix Sum
        if re.search(r'prefix.?sum|prefix_sum|cumulative.?sum|running.?sum|presum|prefix.*array', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Prefix Sum',
                'complexity': 'O(n) build, O(1) query', 'space': 'O(n)',
                'reason': 'Single pass to build O(n), range sum queries in O(1) via subtraction',
                'can_optimize': False,
                'note': 'Already optimal. Extend to 2D prefix sums for matrix range queries in O(1).'
            }

        # Monotonic Stack
        if self._looks_like_monotonic_stack(code):
            return {
                'detected': True, 'algorithm': 'Monotonic Stack',
                'complexity': 'O(n)', 'space': 'O(n)',
                'reason': 'Each element pushed and popped at most once — O(n) total operations amortized',
                'can_optimize': False,
                'note': 'Already optimal for next-greater-element, histogram area, and similar span problems.'
            }

        # Permutation backtracking
        if self._looks_like_permutation_backtracking(code):
            stores_results = self._permutation_materializes_results(code)
            return {
                'detected': True, 'algorithm': 'Permutation Backtracking',
                'complexity': 'O(n * n!)',
                'space': 'O(n * n!)' if stores_results else 'O(n)',
                'reason': 'Backtracking generates n! permutations, each of length n',
                'can_optimize': False,
                'note': (
                    'Unavoidable if all permutations are required. Stream results to reduce output memory.'
                    if stores_results else
                    'Traversal stack/path is O(n) when permutations are visited but not all stored.'
                )
            }

        # Subset / Power Set Generation
        if self._looks_like_subset_generation(code):
            return {
                'detected': True, 'algorithm': 'Subset / Power Set Generation',
                'complexity': 'O(n * 2^n)', 'space': 'O(n * 2^n)',
                'reason': 'Generates all 2^n subsets; total size of all subsets is n·2^(n-1)',
                'can_optimize': False,
                'note': 'Unavoidable if every subset must be returned. Stream subsets to reduce peak memory.'
            }

        # Subset backtracking
        if self._looks_like_subset_backtracking(code):
            return {
                'detected': True, 'algorithm': 'Subset Backtracking',
                'complexity': 'O(2^n)', 'space': 'O(n)',
                'reason': 'Backtracking explores every subset',
                'can_optimize': True, 'optimized_to': 'O(n × target) with DP',
                'note': 'Use memoization or tabulation when the target/state space is bounded.'
            }

        # Segmented Sieve
        if re.search(r'segmented.?sieve|sieve.*segment', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Segmented Sieve',
                'complexity': 'O(n log log n)', 'space': 'O(√n)',
                'reason': 'Same as Eratosthenes but processes in √n-sized blocks — O(√n) space',
                'can_optimize': False,
                'note': 'Preferred over plain sieve when n is large and memory is limited.'
            }

        # Sieve of Eratosthenes
        if re.search(r'sieve|eratosthenes|is_prime\s*=\s*\[', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Sieve of Eratosthenes',
                'complexity': 'O(n log log n)', 'space': 'O(n)',
                'reason': 'Prime harmonic series: n/2 + n/3 + n/5 + ... = O(n log log n)',
                'can_optimize': False, 'note': 'Already optimal for finding all primes up to n.'
            }

        # Binary search
        if re.search(r'binary.?search|bisect|binarySearch', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Binary Search',
                'complexity': 'O(log n)', 'space': 'O(1)',
                'reason': 'Input halved on each step', 'can_optimize': False
            }

        # Merge sort
        if re.search(r'merge.?sort|mergeSort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Merge Sort',
                'complexity': 'O(n log n)', 'space': 'O(n)',
                'reason': 'T(n)=2T(n/2)+O(n) — Master Theorem Case 2 → O(n log n)',
                'can_optimize': False
            }

        # Quick sort
        if re.search(r'quick.?sort|quickSort|partition', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Quick Sort',
                'complexity': 'O(n log n) average, O(n²) worst', 'space': 'O(log n)',
                'reason': 'Partition-based divide and conquer',
                'can_optimize': True, 'optimized_to': 'O(n log n) guaranteed',
                'note': 'Use randomized pivot or Merge Sort/Tim Sort for O(n log n) guaranteed.'
            }

        # Tim Sort
        if re.search(r'timsort|tim.?sort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Tim Sort',
                'complexity': 'O(n log n) worst, O(n) best', 'space': 'O(n)',
                'reason': 'Hybrid merge/insertion sort — O(n) on nearly-sorted data, O(n log n) worst case',
                'can_optimize': False,
                'note': 'Used by Python sorted() and Java Arrays.sort(Object[]). Already optimal.'
            }

        # Heap sort
        if re.search(r'heap.?sort|heapSort|heapify', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Heap Sort',
                'complexity': 'O(n log n)', 'space': 'O(1)',
                'reason': 'Build heap O(n), extract n times O(log n)',
                'can_optimize': False
            }

        # Bubble sort
        if re.search(r'bubble.?sort|bubbleSort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Bubble Sort',
                'complexity': 'O(n²)', 'space': 'O(1)',
                'reason': 'Nested comparison passes over array',
                'can_optimize': True, 'optimized_to': 'O(n log n)',
                'note': 'Replace with built-in sort() or Merge Sort for O(n log n).'
            }

        # Counting / Radix sort
        if re.search(r'counting.?sort|countingSort|radix.?sort|radixSort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Counting/Radix Sort',
                'complexity': 'O(n + k)', 'space': 'O(n + k)',
                'reason': 'Linear-time sorting for bounded integer keys',
                'can_optimize': False
            }

        # KMP
        if re.search(r'kmp|knuth.?morris|failure.?function|lps\s*=', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'KMP String Search',
                'complexity': 'O(n + m)', 'space': 'O(m)',
                'reason': 'Linear preprocessing of pattern + linear scan of text',
                'can_optimize': False
            }

        # Rabin-Karp
        if re.search(r'rabin.?karp|rolling.?hash', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Rabin-Karp',
                'complexity': 'O(n + m) average', 'space': 'O(1)',
                'reason': 'Rolling hash comparison — O(n+m) expected, O(nm) worst case',
                'can_optimize': False
            }

        # Z-Algorithm
        if re.search(r'\bz.?array\b|z.?function|z\s*\[', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Z-Algorithm',
                'complexity': 'O(n)', 'space': 'O(n)',
                'reason': 'Linear Z-array construction',
                'can_optimize': False
            }

        # LCS / Edit Distance
        if re.search(r'\blcs\b|longest.?common.?sub|edit.?distance|levenshtein', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'LCS / Edit Distance (DP)',
                'complexity': 'O(n × m)', 'space': 'O(n × m)',
                'reason': 'DP table over two strings of lengths n and m',
                'can_optimize': False, 'note': 'Space can be reduced to O(min(n,m)) with rolling rows.'
            }

        # Matrix Chain Multiplication
        if re.search(r'matrix.?chain|matrixChain|mcm', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Matrix Chain Multiplication',
                'complexity': 'O(n³)', 'space': 'O(n²)',
                'reason': 'DP over all subchains: O(n²) cells × O(n) split choices',
                'can_optimize': False
            }

        # Travelling Salesman
        if re.search(r'\btsp\b|travelling.?salesman|traveling.?salesman', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Travelling Salesman (DP/Bitmask)',
                'complexity': 'O(n² × 2^n)', 'space': 'O(n × 2^n)',
                'reason': 'Bitmask DP over all subsets × n ending cities',
                'can_optimize': False,
                'note': 'NP-hard; heuristics (nearest-neighbour, 2-opt) give O(n²) approximations.'
            }

        # N-Queens
        if re.search(r'\bnqueens\b|n.?queens|queen.?place', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'N-Queens Backtracking',
                'complexity': 'O(n!)', 'space': 'O(n)',
                'reason': 'Permutation search with constraint pruning',
                'can_optimize': False
            }

        # Sqrt Decomposition / Mo's Algorithm
        if re.search(r'sqrt.?decomp|mos.?algo|block.?size.*sqrt|math\.sqrt.*block', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': "Sqrt Decomposition / Mo's Algorithm",
                'complexity': 'O((n + q) √n)', 'space': 'O(√n)',
                'reason': 'Queries sorted by √n-sized blocks',
                'can_optimize': False
            }

        # Segment Tree
        if re.search(r'segment.?tree|segTree|seg_tree|build.*seg|query.*seg', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Segment Tree',
                'complexity': 'O(n) build, O(log n) query/update', 'space': 'O(n)',
                'reason': 'Binary tree over range segments',
                'can_optimize': False
            }

        # Fenwick Tree / BIT
        if re.search(r'fenwick|bit\s*\[|binary.?indexed', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Fenwick Tree (BIT)',
                'complexity': 'O(log n) query/update', 'space': 'O(n)',
                'reason': 'Low-bit jumps update/query in O(log n)',
                'can_optimize': False
            }

        # Selection sort
        if re.search(r'selection.?sort|selectionSort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Selection Sort',
                'complexity': 'O(n²)', 'space': 'O(1)',
                'reason': 'Finds minimum n times over shrinking array',
                'can_optimize': True, 'optimized_to': 'O(n log n)',
                'note': 'Replace with built-in sort() or Heap Sort for O(n log n).'
            }

        # Insertion sort
        if re.search(r'insertion.?sort|insertionSort', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Insertion Sort',
                'complexity': 'O(n²)', 'space': 'O(1)',
                'reason': 'Each element shifted into correct position',
                'can_optimize': True, 'optimized_to': 'O(n log n)',
                'note': 'Good for small/nearly-sorted arrays. Use Merge Sort for large inputs.'
            }

        # Dynamic programming
        if re.search(r'dp\s*=\s*\[|memo\s*=\s*\{|@lru_cache|knapsack', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Dynamic Programming',
                'complexity': 'O(n) to O(n²) depending on subproblems', 'space': 'O(n)',
                'reason': 'Memoized subproblem solutions',
                'can_optimize': False,
                'note': 'DP is already optimized. Space can sometimes be reduced using rolling arrays.'
            }

        # Data-Dependent Loop
        if re.search(r'while.*\binput\b|while.*\bread\b|for.*\binput\b|loop.*until.*eof|while.*not.*done.*input', code, re.IGNORECASE):
            return {
                'detected': True, 'algorithm': 'Data-Dependent / Input-Driven Loop',
                'complexity': 'O(input size)', 'space': 'O(1)',
                'reason': 'Loop iterations depend on runtime input — complexity proportional to input data size',
                'can_optimize': False,
                'note': 'Profile with realistic data; avoid buffering entire input if streaming is possible.'
            }

        return {'detected': False}

    # ─────────────────────────────────────────────
    # PATTERN DETECTORS
    # ─────────────────────────────────────────────

    def _looks_like_two_pointers(self, code):
        has_two_pointer_names = bool(re.search(
            r'\b(?:left|lo|low|i)\s*=\s*0.*\b(?:right|hi|high|j)\s*=\s*(?:len|n|arr\.length|size)',
            code, re.IGNORECASE | re.DOTALL
        ))
        has_while_convergence = bool(re.search(
            r'while\s*\(?\s*(?:left|lo)\s*<\s*(?:right|hi)\s*\)?', code, re.IGNORECASE
        ))
        has_both_moves = (
            bool(re.search(r'(?:left|lo)\s*\+\+|(?:left|lo)\s*\+=\s*1', code, re.IGNORECASE)) and
            bool(re.search(r'(?:right|hi)\s*--|(?:right|hi)\s*-=\s*1', code, re.IGNORECASE))
        )
        return (has_two_pointer_names and has_while_convergence) or has_both_moves

    def _looks_like_sliding_window(self, code):
        has_window_name = bool(re.search(r'sliding.?window|window_size|max_window|min_window', code, re.IGNORECASE))
        has_window_vars = bool(re.search(r'\b(?:window|left|start|begin)\b.*\b(?:right|end|j)\b', code, re.IGNORECASE))
        has_expand_shrink = bool(re.search(r'(?:while|if)\s*.*\b(?:window|left|start)\b.*(?:\+\+|-=|\+=)', code, re.IGNORECASE))
        has_classic_shape = self._has_sliding_window_for_while_shape(code)
        return has_window_name or (has_window_vars and has_expand_shrink) or has_classic_shape

    def _has_sliding_window_for_while_shape(self, code):
        lines = code.splitlines()
        while_with_window_pointer = re.compile(
            r'\bwhile\b.*\b(?:left|start|lo)\b\s*(?:<|<=)\s*\b(?:right|end|i)\b',
            re.IGNORECASE
        )
        for index, line in enumerate(lines):
            if not re.search(r'\bfor\b', line, re.IGNORECASE):
                continue
            for candidate in lines[index + 1:index + 26]:
                if while_with_window_pointer.search(candidate):
                    return True
        return False

    def _looks_like_monotonic_stack(self, code):
        has_stack_ops = bool(re.search(r'stack\s*=\s*\[\]|\.append\s*\(|\.pop\s*\(', code))
        has_mono_comparison = (
            bool(re.search(r'while\s+stack\s+and\s+(?:stack\[-1\]|stack\.peek)', code, re.IGNORECASE)) or
            bool(re.search(r'while\s*\(?\s*!?\s*(?:stack|mono)\s*\.isEmpty\s*\(\)', code, re.IGNORECASE))
        )
        has_mono_name = bool(re.search(
            r'monoton|next.?greater|prev.?greater|next.?smaller|histogram|largest.?rectangle', code, re.IGNORECASE
        ))
        return has_mono_name or (has_stack_ops and has_mono_comparison)

    def _looks_like_dynamic_array_doubling(self, code):
        compact = self._compact_ws(code)
        has_capacity = bool(re.search(r'\bcapacity\b', code, re.IGNORECASE))
        doubles_capacity = bool(re.search(
            r'\bcapacity\s*\*=\s*2\b|\bcapacity\s*=\s*capacity\s*\*\s*2\b|'
            r'\bnew_?\w*\s*=\s*\[[^\]]*\]\s*\*\s*\(?\s*2\s*\*\s*capacity\s*\)?|'
            r'\bnew\s+\w+\s*\[\s*2\s*\*\s*capacity\s*\]',
            code,
            re.IGNORECASE
        ))
        copies_old_items = bool(re.search(
            r'for\s+\w+\s+in\s+range\s*\(\s*capacity\s*\)|'
            r'for\s*\([^;]*;\s*\w+\s*<\s*capacity\s*;',
            code,
            re.IGNORECASE
        ))
        appends = bool(re.search(r'\.append\s*\(|\.push\s*\(|push_back\s*\(', code, re.IGNORECASE))
        resize_guard = bool(re.search(r'if\s+[^:\n{]*(?:size|len\s*\([^)]*\))\s*==\s*capacity', compact, re.IGNORECASE))
        return has_capacity and doubles_capacity and copies_old_items and appends and resize_guard

    def _looks_like_binary_exponentiation_recursion(self, func_name, body):
        has_parity_branch = bool(re.search(r'%\s*2|&\s*1|is_?odd|is_?even', body, re.IGNORECASE))
        has_halving_call = bool(re.search(
            rf'\b{func_name}\s*\([^)]*(?://\s*2|/\s*2|>>\s*1|Math\.floor\s*\([^)]*/\s*2)',
            body
        ))
        has_decrement_call = bool(re.search(
            rf'\b{func_name}\s*\([^)]*\b\w+\s*-\s*1',
            body
        ))
        return has_parity_branch and has_halving_call and has_decrement_call

    def _looks_like_matrix_power_recursion(self, func_name, body, func_complexities=None):
        if not self._looks_like_binary_exponentiation_recursion(func_name, body):
            return False
        matrix_hint = bool(re.search(r'\bmatrix\b|mat(?:rix)?|k×k|k\s*x\s*k', body, re.IGNORECASE))
        helper_call = re.search(r'\b(\w*(?:multiply|matmul|matrix_mul|matrix_multiply|mul)\w*)\s*\(', body, re.IGNORECASE)
        if not helper_call:
            return False
        if not func_complexities:
            return matrix_hint
        helper = helper_call.group(1)
        helper_complexity = func_complexities.get(helper, '')
        return matrix_hint or helper_complexity in ('O(n³)', 'O(n^3)', 'O(k³)')

    def _looks_like_naive_matrix_multiplication(self, code):
        compact = self._compact_ws(code)
        loop_count = len(re.findall(r'\b(?:for|while)\b', code))
        has_2d_product = bool(re.search(
            r'\[[^\]]+\]\s*\[[^\]]+\].*\*.*\[[^\]]+\]\s*\[[^\]]+\]',
            compact
        ))
        updates_2d_result = bool(re.search(
            r'\[[^\]]+\]\s*\[[^\]]+\]\s*(?:\+=|=)',
            compact
        ))
        matrix_names = bool(re.search(r'\b(?:matrix|mat|multiply|matmul|A|B|result)\b', code))
        return loop_count >= 3 and has_2d_product and updates_2d_result and matrix_names

    def _looks_like_repeated_fresh_graph_search(self, code, search_name='dfs'):
        return bool(self._repeated_fresh_graph_search_info(code, search_name))

    def _repeated_fresh_graph_search_info(self, code, search_name='dfs'):
        cache_key = (str(code or ''), str(search_name or ''))
        if cache_key in self._repeated_fresh_search_cache:
            return self._repeated_fresh_search_cache[cache_key]

        if not code:
            self._repeated_fresh_search_cache[cache_key] = None
            return None
        compact = self._compact_ws(code)
        if not re.search(rf'\b{search_name}\s*\(', compact, re.IGNORECASE):
            self._repeated_fresh_search_cache[cache_key] = None
            return None
        if not re.search(
            r'\b(?:graph|adj|adjacency|neighbor|neighbour|List\s*<\s*List|g\s*\.get|visited|seen|vis)\b',
            compact,
            re.IGNORECASE
        ):
            self._repeated_fresh_search_cache[cache_key] = None
            return None

        fresh_seen = (
            r'(?:set\s*\(\s*\)|new\s+Set\s*\(\s*\)|'
            r'new\s+HashSet(?:\s*<[^>]*>)?\s*\(\s*\)|'
            r'new\s+boolean\s*\[[^\]]+\]|new\s+bool\s*\[[^\]]+\]|'
            r'new\s+Array\s*\([^)]+\)\s*\.fill\s*\(\s*false\s*\)|'
            r'Array\s*\([^)]+\)\s*\.fill\s*\(\s*false\s*\)|'
            r'Collections\.nCopies\s*\([^)]+\)|'
            r'(?:std::)?vector\s*<\s*bool\s*>\s*\([^)]+\))'
        )
        search_call_with_fresh_seen = rf'\b{search_name}\s*\([^;{{}}]*{fresh_seen}[^;{{}}]*\)'
        loop_header = r'(?:for\s+\w+\s+in\s+\w+\s*:|for\s*\([^)]*\)\s*\{?|for\s*\([^)]*:[^)]*\)\s*\{?)'

        caller = self._find_repeated_search_caller(code, search_name, fresh_seen)
        if re.search(rf'{loop_header}.{{0,900}}{search_call_with_fresh_seen}', compact, re.IGNORECASE | re.DOTALL):
            result = {'caller': caller, 'callee': search_name}
            self._repeated_fresh_search_cache[cache_key] = result
            return result

        fresh_seen_assignment = (
            rf'(?:\b(?:visited|seen|vis)\s*=\s*{fresh_seen}|'
            rf'\bboolean\s*\[\]\s+(?:visited|seen|vis)\s*=\s*{fresh_seen}|'
            rf'\b(?:Set|HashSet)(?:\s*<[^>]*>)?\s+(?:visited|seen|vis)\s*=\s*{fresh_seen}|'
            rf'\b(?:std::)?vector\s*<\s*bool\s*>\s+(?:visited|seen|vis)\s*\([^)]+\))'
        )
        call_with_seen_name = rf'\b{search_name}\s*\([^;{{}}]*\b(?:visited|seen|vis)\b[^;{{}}]*\)'
        if re.search(
            rf'{loop_header}.{{0,900}}{fresh_seen_assignment}.{{0,900}}{call_with_seen_name}',
            compact,
            re.IGNORECASE | re.DOTALL
        ):
            result = {'caller': caller, 'callee': search_name}
            self._repeated_fresh_search_cache[cache_key] = result
            return result
        self._repeated_fresh_search_cache[cache_key] = None
        return None

    def _find_repeated_search_caller(self, code, search_name, fresh_seen_pattern):
        func_names = self._function_names(code, self.detect_language(code))
        call_with_fresh_seen = rf'\b{search_name}\s*\([^;{{}}]*{fresh_seen_pattern}[^;{{}}]*\)'
        assignment_then_call = (
            rf'(?:\b(?:visited|seen|vis)\s*=|'
            rf'\bboolean\s*\[\]\s+(?:visited|seen|vis)\s*=|'
            rf'\b(?:Set|HashSet)(?:\s*<[^>]*>)?\s+(?:visited|seen|vis)\s*=|'
            rf'\b(?:std::)?vector\s*<\s*bool\s*>\s+(?:visited|seen|vis)\s*\()'
            rf'.{{0,600}}\b{search_name}\s*\([^;{{}}]*\b(?:visited|seen|vis)\b[^;{{}}]*\)'
        )
        for name in func_names:
            if name == search_name:
                continue
            body = self._extract_function_body(code, name, self.detect_language(code))
            compact_body = self._compact_ws(body)
            has_loop = bool(re.search(r'(?:for\s+\w+\s+in\s+\w+\s*:|for\s*\([^)]*\))', compact_body, re.IGNORECASE))
            if not has_loop:
                continue
            if re.search(call_with_fresh_seen, compact_body, re.IGNORECASE | re.DOTALL):
                return name
            if re.search(assignment_then_call, compact_body, re.IGNORECASE | re.DOTALL):
                return name
        return None

    def _looks_like_graph_dfs_function(self, name, body, full_code='', language='unknown'):
        if not name or not body:
            return False
        if not re.search(rf'\b{name}\s*\(', body):
            return False
        has_visited_guard = bool(re.search(
            r'(?:visited|seen|vis)\s*(?:\.contains\s*\(|\.has\s*\(|\[)|'
            r'\b(?:visited|seen|vis)\.add\s*\(|'
            r'\b(?:visited|seen|vis)\s*\[[^\]]+\]\s*=\s*true',
            body,
            re.IGNORECASE
        ))
        has_adjacency_loop = bool(re.search(
            r'for\s+(?:\w+\s+)?\w+\s+in\s+\w+\s*\[[^\]]+\]|'
            r'for\s*\([^)]*:\s*\w+\.get\s*\([^)]+\)\s*\)|'
            r'for\s*\([^)]*of\s+\w+\s*\[[^\]]+\][^)]*\)|'
            r'for\s*\([^)]*:\s*\w+\s*\[[^\]]+\]\s*\)|'
            r'\b(?:graph|adj|adjacency|g)\s*(?:\.get\s*\(|\[[^\]]+\])',
            body,
            re.IGNORECASE
        ))
        graph_context = bool(re.search(
            r'\b(?:graph|adj|adjacency|neighbor|neighbour|List\s*<\s*List|vector\s*<\s*vector|g\s*\.get)\b',
            f'{full_code}\n{body}',
            re.IGNORECASE
        ))
        return has_visited_guard and has_adjacency_loop and graph_context

    def _looks_like_permutation_backtracking(self, code):
        code_lower = code.lower()
        has_permutation_name = bool(re.search(r'\b(permute|permutation|permutations|backtrack)\b', code_lower))
        has_used_flags = bool(re.search(r'boolean\s*\[\]\s*used|used\s*=\s*\[|visited\s*=\s*\[|used\[.*?\]\s*=', code, re.IGNORECASE))
        has_path_mutation = bool(re.search(r'\.(?:add|append|push)\s*\(|\.(?:remove|pop)\s*\(', code, re.IGNORECASE))
        has_backtrack_call = len(re.findall(r'\bbacktrack\s*\(', code, re.IGNORECASE)) >= 2
        has_full_length_base = bool(re.search(
            r'\w+\.size\s*\(\)\s*==\s*\w+\.(?:size\s*\(\)|length)|len\s*\(\s*\w+\s*\)\s*==\s*len\s*\(',
            code, re.IGNORECASE
        ))
        return has_permutation_name and has_used_flags and has_path_mutation and has_backtrack_call and has_full_length_base

    def _permutation_materializes_results(self, code):
        return bool(re.search(
            r'result(?:s)?\.add\s*\(\s*new\s+ArrayList|results?\.append\s*\(|res\.append\s*\(|\[\.\.\.current\]',
            code, re.IGNORECASE
        ))

    def _looks_like_subset_generation(self, code):
        has_subset_name = bool(re.search(r'\b(subset|subsets|power.?set|powerset|combination|combinations)\b', code, re.IGNORECASE))
        returns_list_of_lists = bool(re.search(
            r'return\s+\[\s*\[\s*\]\s*\]|return\s+new\s+ArrayList\s*<|return\s+result|return\s+res|return\s+ans',
            code, re.IGNORECASE
        ))
        recursive_step = bool(re.search(r'\b\w+\s*=\s*(\w+)\s*\([^)]*(?:\+\s*1|-\s*1)[^)]*\)', code))
        iterates_previous = bool(re.search(
            r'for\s+\w+\s+in\s+\w+|for\s*\([^;]*:[^)]*\)|for\s*\([^;]*of\s+\w+', code, re.IGNORECASE
        ))
        duplicates = bool(re.search(
            r'\.append\s*\(\s*\[|\.append\s*\(\s*\w+\s*\)|\.add\s*\(\s*new\s+ArrayList|'
            r'\.push\s*\(\s*\[|\[\s*\.\.\.\w+|concat\s*\(',
            code, re.IGNORECASE
        ))
        return has_subset_name and returns_list_of_lists and recursive_step and iterates_previous and duplicates

    def _looks_like_subset_backtracking(self, code):
        return (
            bool(re.search(r'\b(subset|subsets|combination|powerSet)\b', code, re.IGNORECASE)) and
            bool(re.search(r'for\s+\w+\s+in\s+range|for\s*\(\s*(?:int|let|var|const)', code)) and
            bool(re.search(r'(?:backtrack|recurse|dfs)\s*\(', code, re.IGNORECASE))
        )

    # ─────────────────────────────────────────────
    # RECURSION ANALYSIS
    # ─────────────────────────────────────────────

    def analyze_recursion(self, code, language):
        func_names = self._function_names(code, language)

        for name in func_names:
            body = self._extract_function_body(code, name, language)
            if not body:
                continue
            recursion_result = self._detect_body_recursion_complexity(name, body)
            if not recursion_result:
                continue

            call_count = len(re.findall(rf'\b{name}\s*\(', body))
            complexity = recursion_result['complexity']
            rec_type = 'recursive'
            if complexity in ('O(1)', 'O(log n)'):
                rec_type = 'divide_conquer_single'
            elif complexity == 'O(n)':
                rec_type = 'linear'
            elif complexity == 'O(n log n)':
                rec_type = 'divide_conquer'
            elif complexity in ('O((log n)!)', 'O(n^((log n + 1)/2))', 'O(n^log n)'):
                rec_type = 'quasi_polynomial'
            elif complexity == 'O(A(m, n))':
                rec_type = 'ackermann'
            elif 'φⁿ' in complexity:
                rec_type = 'fibonacci_exponential'
            elif '^n)' in complexity or 'ⁿ)' in complexity or '2^n' in complexity or '3^n' in complexity:
                rec_type = 'exponential'
            payload = {
                'is_recursive': True, 'type': rec_type,
                'branches': call_count, 'func_name': name,
                'complexity': complexity, 'reason': recursion_result['reason']
            }
            if recursion_result.get('recurrence_analysis'):
                payload['recurrence_analysis'] = recursion_result['recurrence_analysis']
            return payload

        return {'is_recursive': False}

    def detect_mutual_recursion(self, code, language):
        func_names = self._function_names(code, language)
        bodies = {name: self._extract_function_body(code, name, language) for name in func_names}

        for caller in func_names:
            caller_body = bodies.get(caller, '')
            if not caller_body:
                continue
            for callee in func_names:
                if caller == callee:
                    continue
                if not re.search(rf'\b{callee}\s*\(', caller_body):
                    continue
                callee_body = bodies.get(callee, '')
                if not re.search(rf'\b{caller}\s*\(', callee_body):
                    continue
                cycle_text = f'{caller_body}\n{callee_body}'
                if self._mutual_cycle_has_sqrt_shrink(caller, callee, caller_body, callee_body):
                    return {
                        'detected': True, 'complexity': 'O(log log n)', 'space': 'O(log log n)',
                        'functions': [caller, callee],
                        'reason': f'Mutual recursion {caller}↔{callee} shrinks by √n → O(log log n) depth'
                    }
                if re.search(r'\b\w+\s*-\s*1\b', cycle_text):
                    return {
                        'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                        'functions': [caller, callee],
                        'reason': f'Mutual recursion {caller}↔{callee} decrements linearly → O(n)'
                    }
        return {'detected': False}

    def _mutual_cycle_has_sqrt_shrink(self, caller, callee, caller_body, callee_body):
        call_patterns = [
            rf'\b{callee}\s*\([^)]*(?:sqrt|Math\.sqrt)[^)]*\)',
            rf'\b{caller}\s*\([^)]*(?:sqrt|Math\.sqrt)[^)]*\)',
        ]
        if any(re.search(p, caller_body) or re.search(p, callee_body) for p in call_patterns):
            return True
        return bool(re.search(r'(?:sqrt|Math\.sqrt)\s*\(', f'{caller_body}\n{callee_body}'))

    def _recursive_call_multiplier(self, func_name, body):
        contexts = self._call_loop_contexts(body, {func_name}, current_func=None)
        if not contexts:
            return None
        return self._max_complexity([complexity for _, complexity in contexts])

    def _called_function_complexities(self, body, func_complexities, current_func=None):
        target_names = set(func_complexities.keys())
        if current_func:
            target_names.discard(current_func)
        results = []
        for func_name, multiplier in self._call_loop_contexts(body, target_names, current_func):
            callee = func_complexities.get(func_name)
            if not callee:
                continue
            if multiplier == 'O(1)':
                results.append(callee)
                continue
            results.append(self._tuple_to_string(self._multiply_complexity(
                self._parse_complexity_string(multiplier),
                self._parse_complexity_string(callee)
            )))
        return results

    def _call_loop_contexts(self, body, target_names, current_func=None):
        cache_key = (
            str(body or ''),
            tuple(sorted(str(name) for name in (target_names or set()))),
            str(current_func or ''),
        )
        if cache_key in self._call_context_cache:
            return self._call_context_cache[cache_key]

        contexts = []
        loop_stack = []
        lines = body.split('\n')
        constant_iterables = self._constant_local_iterable_names(body)
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            indent = self._get_indent(line)
            loop_stack = [item for item in loop_stack if item['indent'] < indent]
            for name in target_names:
                if name == current_func:
                    continue
                if self._line_has_direct_function_call(stripped, name):
                    multiplier = ('const', 0)
                    for loop in loop_stack:
                        multiplier = self._multiply_complexity(multiplier, loop['complexity'])
                    contexts.append((name, self._tuple_to_string(multiplier)))
            is_loop = re.match(r'for\s*[\(\s]', stripped) or re.match(r'while\s*[\(\s]', stripped)
            if is_loop:
                body_after_header = lines[index + 1:]
                loop_type = (
                    self.classify_for_loop(stripped, body_after_header, lines, 'unknown')
                    if stripped.startswith('for')
                    else self.classify_while_loop(stripped, body_after_header, lines, 'unknown')
                )
                loop_complexity = self._loop_bound_complexity(stripped, loop_type)
                iter_match = re.search(
                    r'for\s+(?:\w+\s*,\s*)?\w+\s+in\s+([A-Za-z_]\w*)\b',
                    stripped
                )
                if iter_match and iter_match.group(1) in constant_iterables:
                    loop_complexity = ('const', 0)
                loop_stack.append({
                    'indent': indent,
                    'complexity': loop_complexity
                })
        self._call_context_cache[cache_key] = contexts
        return contexts

    def _line_has_direct_function_call(self, line, name):
        pattern = re.compile(rf'\b{re.escape(str(name))}\s*\(')
        for match in pattern.finditer(str(line or '')):
            start = match.start()
            if start > 0 and line[start - 1] == '.':
                if start >= 3 and line[start - 3:start] == '...':
                    return True
                continue
            return True
        return False

    def _constant_local_iterable_names(self, body):
        names = set()
        for match in re.finditer(r'(?m)^\s*([A-Za-z_]\w*)\s*=\s*([\[\(\{])', str(body or '')):
            names.add(match.group(1))
        return names

    # ─────────────────────────────────────────────
    # FUNCTION BODY EXTRACTION
    # ─────────────────────────────────────────────

    def _extract_function_body(self, code, func_name, language):
        cache_key = (str(code or ''), str(func_name or ''), str(language or ''))
        if cache_key in self._function_body_cache:
            return self._function_body_cache[cache_key]

        body = ''
        if language == 'python':
            node = self._python_function_node(code, func_name)
            if node:
                body = self._python_function_source(code, node, include_header=False)
            self._function_body_cache[cache_key] = body
            return body

        if language in ('java', 'cpp', 'c', 'javascript', 'typescript'):
            synthetic = self._javascript_synthetic_function(code, func_name, language)
            if synthetic:
                body = synthetic.get('body') or ''
                self._function_body_cache[cache_key] = body
                return body
            signature = re.search(
                rf'(?:def\s+|function\s*\*?\s+|(?:const|let|var)\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?'
                rf'(?:void|int|long|double|float|boolean|bool|char|String|List[\w<>\[\], ?]*|'
                rf'ArrayList[\w<>\[\], ?]*|Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|'
                rf'vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+){func_name}\s*(?:=\s*)?\([^)]*\)',
                code
            )
            if signature:
                open_brace = code.find('{', signature.end())
                if open_brace != -1:
                    depth = 0
                    for pos in range(open_brace, len(code)):
                        if code[pos] == '{':
                            depth += 1
                        elif code[pos] == '}':
                            depth -= 1
                            if depth == 0:
                                body = self._brace_code_to_indented_lines(code[open_brace + 1:pos])
                                self._function_body_cache[cache_key] = body
                                return body

        lines = code.split('\n')
        in_func = False
        body_lines = []
        base_indent = None
        for line in lines:
            stripped = line.strip()
            if re.match(
                rf'(?:def\s+|function\s*\*?\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?'
                rf'(?:void|int|long|double|float|boolean|bool|char|String|List[\w<>\[\], ?]*|'
                rf'ArrayList[\w<>\[\], ?]*|Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|'
                rf'vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+|(?:const|let|var)\s+){func_name}\s*(?:=\s*)?\(',
                stripped
            ):
                in_func = True
                base_indent = len(line) - len(line.lstrip())
                if language == 'python':
                    inline_body = re.match(
                        rf'(?:async\s+)?def\s+{re.escape(func_name)}\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:\s*(.+)$',
                        stripped,
                    )
                    if inline_body and inline_body.group(1).strip():
                        body = inline_body.group(1).strip()
                        self._function_body_cache[cache_key] = body
                        return body
                continue
            if in_func:
                if not stripped:
                    body_lines.append(line)
                    continue
                curr_indent = len(line) - len(line.lstrip())
                if curr_indent <= base_indent and stripped:
                    break
                body_lines.append(line)
        body = '\n'.join(body_lines)
        self._function_body_cache[cache_key] = body
        return body

    def _brace_code_to_indented_lines(self, code):
        lines = []
        current = []
        indent = 0
        paren_depth = 0

        def flush():
            text = ''.join(current).strip()
            current.clear()
            if text:
                lines.append(('    ' * indent) + text)

        for char in code:
            if char == '(':
                paren_depth += 1; current.append(char)
            elif char == ')':
                paren_depth = max(0, paren_depth - 1); current.append(char)
            elif char == '{':
                flush(); indent += 1
            elif char == '}':
                flush(); indent = max(0, indent - 1)
            elif char == ';' and paren_depth == 0:
                current.append(char); flush()
            elif char == '\n':
                flush()
            else:
                current.append(char)
        flush()
        return '\n'.join(lines)

    # ─────────────────────────────────────────────
    # LOOP CLASSIFICATION
    # ─────────────────────────────────────────────

    def detect_special_loop_patterns(self, code, language):
        compact = self._compact_ws(code)

        # Two-pointer → O(n)
        if self._looks_like_two_pointers(code):
            return {'detected': True, 'complexity': 'O(n)', 'reason': 'Two-pointer: each pointer moves at most n steps total'}

        # Sliding window → O(n)
        if self._looks_like_sliding_window(code):
            return {'detected': True, 'complexity': 'O(n)', 'reason': 'Sliding window: each element added and removed at most once'}

        # Monotonic stack → O(n)
        if self._looks_like_monotonic_stack(code):
            return {'detected': True, 'complexity': 'O(n)', 'reason': 'Monotonic stack: each element pushed/popped at most once (amortized O(n))'}

        # i*i < n → O(√n) loop
        sqrt_loop = (
            bool(re.search(
                r'for\s*\(?\s*(?:let|var|const|int|long)?\s*(\w+)\s*=\s*[012]\s*;'
                r'\s*\1\s*\*\s*\1\s*(?:<|<=)\s*\w+', compact, re.IGNORECASE
            )) or
            bool(re.search(r'while\s*\(?\s*(\w+)\s*\*\s*\1\s*(?:<|<=)\s*\w+', compact, re.IGNORECASE)) or
            bool(re.search(r'for\s+\w+\s+in\s+range\s*\(\s*int\s*\(\s*(?:math\.)?sqrt', compact, re.IGNORECASE))
        )
        if sqrt_loop:
            return {'detected': True, 'complexity': 'O(√n)', 'reason': 'Loop condition i*i < n or i < √n — iterates O(√n) times'}

        shifted_log_sum = bool(re.search(
            r'while\s+(\w+)\s*<\s*(\w+).*?\b(\w+)\s*=\s*\1\s+'
            r'while\s+\3\s*<\s*\2.*?'
            r'(?:\3\s*\*=\s*2|\3\s*=\s*\3\s*\*\s*2|\3\s*<<=\s*1).*?'
            r'(?:\1\s*\+=\s*1|\1\s*=\s*\1\s*\+\s*1|\1\+\+|\+\+\1)',
            compact, re.IGNORECASE
        ))
        if shifted_log_sum:
            return {'detected': True, 'complexity': 'O(n)', 'reason': 'Shifted logarithmic inner loop: sum_i log(n/i) = O(n)'}

        harmonic_while_python = bool(re.search(
            r'for\s+(\w+)\s+in\s+range\s*\(\s*1\s*,\s*(\w+)(?:\s*\+\s*1)?\s*\).*?'
            r'\b(\w+)\s*=\s*(?:0|1)\s+while\s+\3\s*(?:<|<=)\s*\2\s*:?.*?\b\3\s*\+=\s*\1\b',
            compact, re.IGNORECASE
        ))
        harmonic_while_js = bool(re.search(
            r'for\s*\(\s*(?:let|var|const|int|long)?\s*(\w+)\s*=\s*1\s*;'
            r'\s*\1\s*<=?\s*(\w+)[^;]*;[^)]*(?:\1\+\+|\+\+\1|\1\s*\+=\s*1)[^)]*\).*?'
            r'(?:let|var|const|int|long)?\s*(\w+)\s*=\s*(?:0|1)\s*;?\s*'
            r'while\s*\(?\s*\3\s*<=?\s*\2\s*\)?.*?\b\3\s*\+=\s*\1\b',
            compact, re.IGNORECASE
        ))
        if harmonic_while_python or harmonic_while_js:
            return {'detected': True, 'complexity': 'O(n log n)', 'reason': 'Harmonic step loop: n/1 + n/2 + ... + n/n = O(n log n)'}

        geometric_prefix_linear = bool(re.search(
            r'while\s+(\w+)\s*<\s*\w+.*?for\s+\w+\s+in\s+range\s*\(\s*\1\s*\).*?'
            r'(?:\1\s*\*=\s*2|\1\s*=\s*\1\s*\*\s*2|\1\s*<<=\s*1)',
            compact, re.IGNORECASE
        ))
        if geometric_prefix_linear:
            loop_complexity = self.compute_loop_complexity(self.extract_loop_tree(code, language))
            if loop_complexity and loop_complexity != 'O(n)':
                return {
                    'detected': True,
                    'complexity': loop_complexity,
                    'reason': f'Geometric prefix sum with nested work: {loop_complexity}'
                }
            return {'detected': True, 'complexity': 'O(n)', 'reason': 'Geometric prefix sum: 1+2+4+...+n = O(n)'}

        harmonic_step_js = bool(re.search(
            r'for\s*\(\s*(?:let|var|const)?\s*(\w+)\s*=[^;]*;\s*\1\s*\*\s*\1\s*<=?\s*\w+[^;]*;\s*\1\+\+.*?'
            r'for\s*\([^;]*;[^;]*<\s*\w+[^;]*;\s*\w+\s*\+=\s*\1\s*\)',
            compact, re.IGNORECASE
        ))
        harmonic_step_python = bool(re.search(
            r'for\s+\w+\s+in\s+range\s*\(\s*1\s*,.*?\).*?for\s+\w+\s+in\s+range\s*\(\s*0\s*,\s*\w+\s*,\s*\w+\s*\)',
            compact, re.IGNORECASE
        ))
        if harmonic_step_js or harmonic_step_python:
            return {'detected': True, 'complexity': 'O(n log n)', 'reason': 'Harmonic loop: n/1 + n/2 + ... = O(n log n)'}

        return {'detected': False}

    def detect_catastrophic_regex(self, code):
        regex_patterns = []
        regex_patterns.extend(re.findall(r'/(.+?)/[gimsuy]*', code))
        regex_patterns.extend(re.findall(r'RegExp\s*\(\s*[\'"](.+?)[\'"]', code))
        regex_patterns.extend(re.findall(r're\.compile\s*\(\s*[rR]?[\'"](.+?)[\'"]', code))
        if not regex_patterns:
            return {'detected': False}
        regex_is_used = bool(re.search(
            r'\.test\s*\(|\.match\s*\(|\.search\s*\(|\.exec\s*\(|re\.(?:match|search|fullmatch)\s*\(', code
        ))
        if not regex_is_used:
            return {'detected': False}
        for pattern in regex_patterns:
            if self._has_catastrophic_regex_shape(pattern):
                return {
                    'detected': True, 'complexity': 'O(2^n)', 'space': 'O(n)',
                    'pattern': pattern,
                    'reason': 'Catastrophic regex backtracking: nested ambiguous quantifiers can try exponentially many matches'
                }
        return {'detected': False}

    def _has_catastrophic_regex_shape(self, pattern):
        nested_quantifier = bool(re.search(r'\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*[+*{]', pattern))
        overlapping_alternation = bool(re.search(r'\(([^|()]+)\|(\1[^()]*)\)\s*[+*{]', pattern))
        repeated_wildcard = bool(re.search(r'\((?:\.\*|\.\+|\[[^\]]+\][+*])\)\s*[+*{]', pattern))
        return nested_quantifier or overlapping_alternation or repeated_wildcard

    def _is_sorting_call(self, line):
        return bool(re.search(r'\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\(', line))

    def _sorting_complexity(self, code):
        if not any(self._is_sorting_call(line) for line in code.split('\n')):
            return None
        max_depth = self._max_sorting_loop_depth(code)
        if max_depth <= 0: return 'O(n log n)'
        if max_depth == 1: return 'O(n² log n)'
        if max_depth == 2: return 'O(n³ log n)'
        return f'O(n^{max_depth + 1} log n)'

    def _max_sorting_loop_depth(self, code):
        operation_depth = self._max_operation_loop_depth(
            code,
            r'(?:\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\()'
        )
        loop_stack = []
        max_depth = 0
        for line in code.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            indent = self._get_indent(line)
            loop_stack = [level for level in loop_stack if level < indent]
            if self._is_sorting_call(stripped):
                max_depth = max(max_depth, len(loop_stack))
            if re.match(r'(for|while)\s*[\(\s]', stripped):
                loop_stack.append(indent)
        return max(max_depth, operation_depth)

    def _max_operation_loop_depth(self, code, operation_pattern):
        loop_stack = []
        max_depth = 0
        for line in code.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            indent = self._get_indent(line)
            loop_stack = [level for level in loop_stack if level < indent]
            if re.search(operation_pattern, stripped):
                max_depth = max(max_depth, len(loop_stack))
            if re.match(r'(for|while)\s*[\(\s]', stripped):
                loop_stack.append(indent)

        compact = self._compact_ws(code)
        loop_pattern = r'(?:\bfor\s*\([^)]*\)|\bwhile\s*\([^)]*\)|\bfor\s+\w+\s+in\s+\w+)\s*(?:\{|:)?'
        if re.search(loop_pattern + r'.*?' + loop_pattern + r'.*?' + operation_pattern, compact):
            max_depth = max(max_depth, 2)
        elif re.search(loop_pattern + r'.*?' + operation_pattern, compact):
            max_depth = max(max_depth, 1)
        return max_depth

    def classify_loop(self, body_lines, all_lines, lang):
        body = '\n'.join(body_lines) if isinstance(body_lines, list) else body_lines
        log_patterns = [
            r'\*=\s*[2-9]', r'\/=\s*[2-9]', r'>>=\s*1', r'<<=\s*1',
            r'Math\.floor\s*\(\s*\w+\s*\/\s*2\s*\)',
            r'\w+\s*=\s*\w+\s*\*\s*[2-9]', r'\w+\s*=\s*\w+\s*\/\s*[2-9]',
            r'\b(\w+)\s*\+=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
            r'\b(\w+)\s*-=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
        ]
        for pattern in log_patterns:
            if re.search(pattern, body):
                return 'logarithmic'
        return 'linear'

    def classify_while_loop(self, header, body_lines, all_lines, lang):
        control = self._loop_control_variable(header)
        if not control:
            return self.classify_loop(body_lines, all_lines, lang)
        body = '\n'.join(body_lines) if isinstance(body_lines, list) else str(body_lines)
        patterns = [
            rf'\b{control}\s*\*=\s*[2-9]\b', rf'\b{control}\s*=\s*{control}\s*\*\s*[2-9]\b',
            rf'\b{control}\s*=\s*[2-9]\s*\*\s*{control}\b', rf'\b{control}\s*<<=\s*1\b',
            rf'\b{control}\s*(?://|/)=\s*[2-9]\b', rf'\b{control}\s*=\s*{control}\s*(?://|/)\s*[2-9]\b',
            rf'\b{control}\s*>>=\s*1\b',
            rf'\b{control}\s*\+=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*-=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*&\s*\(?\s*{control}\s*-\s*1\s*\)?',
            rf'\b{control}\s*&=\s*\(?\s*{control}\s*-\s*1\s*\)?',
        ]
        if any(re.search(p, body) for p in patterns):
            return 'logarithmic'
        return 'linear'

    def classify_for_loop(self, header, body_lines, all_lines, lang):
        js_for = re.search(r'for\s*\([^;]*;[^;]*;([^)]*)\)', header)
        if js_for:
            update = js_for.group(1).strip()
            for p in [
                r'\*=\s*[2-9]', r'\/=\s*[2-9]', r'>>=\s*1',
                r'=\s*\w+\s*\*\s*[2-9]', r'=\s*\w+\s*\/\s*[2-9]',
                r'\b(\w+)\s*\+=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
            ]:
                if re.search(p, update):
                    return 'logarithmic'
            return 'linear'
        if re.search(r'for\s+\w+\s+in\s+', header):
            return 'linear'
        return 'linear'

    def _loop_control_variable(self, header):
        while_match = re.search(r'while\s*\(?\s*(\w+)\s*(?:<|<=|>|>=)', header)
        if while_match:
            return while_match.group(1)
        for_match = re.search(r'for\s*\(\s*(?:(?:let|var|const|int|long|size_t)\s+)?(\w+)\s*=', header)
        if for_match:
            return for_match.group(1)
        return None

    def _loop_growth_variable(self, header, body_lines):
        control = self._loop_control_variable(header)
        if not control:
            return None
        body = '\n'.join(body_lines) if isinstance(body_lines, list) else str(body_lines)
        growth_patterns = [
            rf'\b{control}\s*\*=\s*[2-9]\b', rf'\b{control}\s*=\s*{control}\s*\*\s*[2-9]\b',
            rf'\b{control}\s*<<=\s*1\b',
            rf'\b{control}\s*(?://|/)=\s*[2-9]\b', rf'\b{control}\s*=\s*{control}\s*(?://|/)\s*[2-9]\b',
            rf'\b{control}\s*>>=\s*1\b',
            rf'\b{control}\s*\+=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*&\s*\(?\s*{control}\s*-\s*1\s*\)?',
            rf'\b{control}\s*&=\s*\(?\s*{control}\s*-\s*1\s*\)?',
        ]
        if any(re.search(pattern, body) for pattern in growth_patterns):
            return control
        js_for = re.search(r'for\s*\([^;]*;[^;]*;([^)]*)\)', header)
        if js_for:
            update = js_for.group(1)
            if any(re.search(pattern, update) for pattern in growth_patterns):
                return control
        return None

    def _loop_bound_variables(self, header):
        range_match = re.search(r'for\s+\w+\s+in\s+range\s*\(([^)]*)\)', header)
        if range_match:
            args = [arg.strip() for arg in range_match.group(1).split(',')]
            bounds = set()
            for arg in args[:2]:
                bounds.update(re.findall(r'\b[a-zA-Z_]\w*\b', arg))
            return bounds
        js_match = re.search(r'for\s*\([^;]*;([^;]*);[^)]*\)', header)
        if js_match:
            control = self._loop_control_variable(header)
            condition = js_match.group(1)
            bounds = set()
            if control:
                for bound in re.findall(rf'\b{control}\s*(?:<|<=|>|>=)\s*(\w+)', condition):
                    bounds.add(bound)
                for bound in re.findall(rf'\b(\w+)\s*(?:<|<=|>|>=)\s*{control}\b', condition):
                    bounds.add(bound)
            return bounds
        return set()

    def _loop_bound_complexity(self, header, loop_type):
        if loop_type == 'logarithmic':
            return ('log', 1)
        range_match = re.search(r'for\s+\w+\s+in\s+range\s*\(([^)]*)\)', header)
        if range_match:
            args = [arg.strip() for arg in range_match.group(1).split(',')]
            bound = args[0] if len(args) == 1 else args[1] if len(args) >= 2 else ''
            power = self._polynomial_bound_power(bound)
            if power is not None:
                if power <= 0:
                    return ('const', 0)
                return ('n', power)
        js_match = re.search(r'for\s*\([^;]*;([^;]*);[^)]*\)', header)
        if js_match:
            control = self._loop_control_variable(header)
            condition = js_match.group(1)
            if control:
                bound = self._condition_bound_expression(condition, control)
                power = self._polynomial_bound_power(bound)
                if power is not None:
                    if power <= 0:
                        return ('const', 0)
                    return ('n', power)
        return ('n', 1)

    def _condition_bound_expression(self, condition, control):
        right = re.search(rf'\b{control}\s*(?:<|<=)\s*(.+)$', condition)
        if right:
            return right.group(1).strip()
        left = re.search(rf'^(.+?)\s*(?:<|<=)\s*{control}\b', condition)
        if left:
            return left.group(1).strip()
        return ''

    def _polynomial_bound_power(self, expression):
        expression = expression.strip()
        if not expression:
            return 1
        if re.fullmatch(r'\d+', expression):
            return 0
        expr = re.sub(r'\s+', '', expression)
        if re.fullmatch(r'[A-Z_][A-Z0-9_]*', expr):
            return 0
        exponent_match = re.fullmatch(r'\w+(?:\*\*|\^)(\d+)', expr)
        if exponent_match:
            return int(exponent_match.group(1))
        factors = expr.split('*')
        if len(factors) > 1 and all(re.fullmatch(r'\w+', factor) for factor in factors):
            return len(factors)
        if re.fullmatch(r'\w+', expr):
            return 1
        return 1

    def extract_loop_tree(self, code, lang):
        lines = code.split('\n')
        return self._parse_loops(lines, 0, lang)

    def _get_indent(self, line):
        return len(line) - len(line.lstrip())

    def _parse_loops(self, lines, start_indent, lang):
        loops = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            indent = self._get_indent(line)
            is_loop = re.match(r'for\s*[\(\s]', stripped) or re.match(r'while\s*[\(\s]', stripped)
            if is_loop and indent >= start_indent:
                body_lines = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    if not next_stripped:
                        j += 1
                        continue
                    next_indent = self._get_indent(next_line)
                    if next_indent <= indent:
                        break
                    body_lines.append(next_line)
                    j += 1
                header = stripped
                if re.match(r'while', stripped):
                    loop_type = self.classify_while_loop(header, body_lines, lines, lang)
                else:
                    loop_type = self.classify_for_loop(header, body_lines, lines, lang)
                children = self._parse_loops(body_lines, 0, lang)
                loops.append({
                    'type': loop_type, 'header': header, 'children': children,
                    'growth_var': self._loop_growth_variable(header, body_lines),
                    'bound_vars': self._loop_bound_variables(header),
                    'bound_complexity': self._loop_bound_complexity(header, loop_type),
                })
                i = j
            else:
                i += 1
        return loops

    # ─────────────────────────────────────────────
    # COMPLEXITY MATH
    # ─────────────────────────────────────────────

    def compute_loop_complexity(self, loops):
        if not loops:
            return None
        complexities = [self._loop_complexity(loop) for loop in loops]
        return self._max_complexity(complexities)

    def _loop_complexity(self, loop):
        own = loop.get('bound_complexity') or (
            ('log', 1) if loop['type'] == 'logarithmic' else ('n', 1)
        )
        if loop['children']:
            terms = [own]
            for child_loop in loop['children']:
                child = self._loop_complexity(child_loop)
                if self._is_geometric_prefix_sum(loop, child_loop):
                    terms.append(child)
                else:
                    terms.append(self._multiply_complexity(own, child))
            return self._max_complexity_tuple(terms)
        return own

    def _is_geometric_prefix_sum(self, parent, child):
        growth_var = parent.get('growth_var')
        return (
            parent.get('type') == 'logarithmic' and
            growth_var and
            growth_var in child.get('bound_vars', set())
        )

    def _multiply_complexity(self, a, b):
        type_a, pow_a = a
        type_b, pow_b = b
        if type_a == 'const':
            return b
        if type_b == 'const':
            return a
        if type_a in ('quasi_log_fact', 'quasi_poly', 'quasi_poly_half') or type_b in ('quasi_log_fact', 'quasi_poly', 'quasi_poly_half'):
            return ('quasi_poly', 1)
        log_powers = {'log': 1, 'log2': 2, 'log3': 3, 'log4': 4}
        if type_a in log_powers and type_b in log_powers:
            return self._log_power_tuple(log_powers[type_a] + log_powers[type_b])
        if type_a == 'log' and type_b == 'n':
            if pow_b == 2: return ('n2_log', 1)
            if pow_b == 3: return ('n3_log', 1)
            return ('n_log', 1)
        if type_a == 'n' and type_b == 'log':
            if pow_a == 2: return ('n2_log', 1)
            if pow_a == 3: return ('n3_log', 1)
            return ('n_log', 1)
        combos = {
            ('n', 'n'): ('n', pow_a + pow_b),
            ('n', 'log'): ('n_log', 1), ('log', 'n'): ('n_log', 1),
            ('log', 'log'): ('log2', 1),
            ('n', 'n_log'): ('n2_log', 1), ('n_log', 'n'): ('n2_log', 1),
            ('n', 'log2'): ('n_log2', 1), ('log2', 'n'): ('n_log2', 1),
            ('n_log', 'log'): ('n_log2', 1), ('log', 'n_log'): ('n_log2', 1),
            ('sqrt', 'n'): ('n', 2),
        }
        result = combos.get((type_a, type_b))
        if result:
            return result
        if type_a == 'n' and type_b == 'n':
            return ('n', pow_a + pow_b)
        return ('n', pow_a + pow_b)

    def _log_power_tuple(self, power):
        if power <= 1:
            return ('log', 1)
        if power == 2:
            return ('log2', 1)
        if power == 3:
            return ('log3', 1)
        if power == 4:
            return ('log4', 1)
        return ('logp', power)

    def _complexity_rank(self, c):
        type_c, pow_c = c
        ranks = {
            'const': 0, 'alpha': 0.05, 'loglog': 0.5, 'log': 1,
            'log2': 2, 'log3': 2.2, 'log4': 2.3, 'logp': 2.4, 'sqrt': 2.5,
            'n': 10, 'n_log': 15, 'n_log2': 16,
            'n2_log': 25, 'n3_log': 35,
            'strassen': 28, 'k3_log': 35,
            'v_times_ve': 30,
            'quasi_log_fact': 90, 'quasi_poly_half': 89, 'quasi_poly': 90,
            'phi_exp': 95, 'exp': 100, 'n_exp': 105,
            'factorial': 110, 'n_factorial': 120, 'ackermann': 140,
        }
        if type_c == 'n':
            return 10 * float(pow_c)
        return ranks.get(type_c, 10)

    def _max_complexity_tuple(self, complexities):
        return max(complexities, key=self._complexity_rank)

    def _max_complexity(self, complexities):
        ranked = [
            (self._parse_complexity_string(c), c)
            for c in complexities
            if c
        ]
        if not ranked:
            return 'O(1)'
        best_tuple, best_original = max(
            ranked,
            key=lambda item: self._complexity_rank(item[0])
        )
        if self._has_contextual_complexity_label(best_original):
            return str(best_original)
        return self._tuple_to_string(best_tuple)

    def _has_contextual_complexity_label(self, complexity):
        if not isinstance(complexity, str):
            return False
        return bool(re.search(
            r'\b(?:average|worst|best|amortized|build|query|preprocess|V|E|k)\b',
            complexity,
            re.IGNORECASE
        ))

    def _parse_complexity_string(self, s):
        if not s:
            return ('const', 0)
        if isinstance(s, tuple):
            return s
        normalized = (
            str(s)
            .replace('²', '²')
            .replace('³', '³')
            .replace('√', 'âˆš')
            .replace('φⁿ', 'Ï†â¿')
            .replace('α', 'Î±')
            .replace('^2', '²')
            .replace('^3', '³')
        )
        if re.fullmatch(r'O\(n²\) average,\s*O\(n³\) worst', normalized):
            return ('n', 3)
        mapping = {
            'O(1)': ('const', 0),
            'O(1) amortized': ('const', 0),
            'O(log n) amortized': ('log', 1),
            'O(α(n))': ('alpha', 1),
            'O(log log n)': ('loglog', 1),
            'O(log log U)': ('loglog', 1),
            'O(log n)': ('log', 1),
            'O(log_t n)': ('log', 1),
            'O(log n) to O(1)': ('log', 1),
            'O(log min(a,b))': ('log', 1),
            'O(log p)': ('log', 1),
            'O(k log² n)': ('log2', 1),
            'O(log² n)': ('log2', 1),
            'O(log^2 n)': ('log2', 1),
            'O(log³ n)': ('log3', 1),
            'O(log^3 n)': ('log3', 1),
            'O(√n)': ('sqrt', 1),
            'O(n^(1/4))': ('n', 1),
            'O(n)': ('n', 1),
            'O(n log log n)': ('n', 1),
            'O(n log n)': ('n_log', 1),
            'O(n log² n)': ('n_log2', 1),
            'O(n log n) build, O(1) query': ('n_log', 1),
            'O(n log n) preprocess, O(log n) query': ('n_log', 1),
            'O(n log n) build, O(log n) query': ('n_log', 1),
            'O(n log n) build, O(log² n) query': ('n_log', 1),
            'O(n log n) worst, O(n) best': ('n_log', 1),
            'O(n) build, O(log n) query/update': ('n', 1),
            f'O(n{chr(178)})': ('n', 2), f'O(n{chr(179)})': ('n', 3),
            f'O(n{chr(178)} log n)': ('n2_log', 1), f'O(n{chr(179)} log n)': ('n3_log', 1),
            'O(n²)': ('n', 2), 'O(n^2)': ('n', 2),
            'O(n² log n)': ('n2_log', 1), 'O(n^2 log n)': ('n2_log', 1),
            'O(n³)': ('n', 3), 'O(n^3)': ('n', 3),
            'O(n³ log n)': ('n3_log', 1), 'O(n^3 log n)': ('n3_log', 1),
            'O(n^2.807)': ('strassen', 1),
            'O(n^1.585)': ('n', 1.585),
            'O(φⁿ)': ('phi_exp', 1),
            'O(n!)': ('factorial', 1),
            'O((log n)!)': ('quasi_log_fact', 1),
            'O(n^((log n + 1)/2))': ('quasi_poly_half', 1),
            'O(n^log n)': ('quasi_poly', 1),
            'O(n × n!)': ('n_factorial', 1), 'O(n * n!)': ('n_factorial', 1),
            'O(A(m, n))': ('ackermann', 1),
            'O(2ⁿ)': ('exp', 2), 'O(2^n)': ('exp', 2),
            'O(2^(n/2))': ('exp', 2),
            'O(n * 2^n)': ('n_exp', 2), 'O(n × 2^n)': ('n_exp', 2),
            'O(n² × 2^n)': ('n_exp', 2),
            'O(3ⁿ)': ('exp', 3), 'O(3^n)': ('exp', 3),
            'O((V + E) log V)': ('n_log', 1), 'O(V + E)': ('n', 1),
            'O(V)': ('n', 1), 'O(E)': ('n', 1),
            'O(E log V)': ('n_log', 1), 'O(E log E)': ('n_log', 1),
            'O(E√V)': ('n', 2),
            'O(V × E)': ('n', 2), 'O(V^2)': ('n', 2), 'O(V²)': ('n', 2),
            'O(V * (V + E))': ('v_times_ve', 1),
            'O(V x (V + E))': ('v_times_ve', 1),
            'O(V*(V+E))': ('v_times_ve', 1),
            'O(V E²)': ('n', 3), 'O(V E^2)': ('n', 3), 'O(V³)': ('n', 3), 'O(V^3)': ('n', 3),
            'O(V^3 E)': ('n', 4), 'O(V³E)': ('n', 4), 'O(V³ E)': ('n', 4),
            'O(V²E)': ('n', 3), 'O(V² log V + VE)': ('n2_log', 1),
            'O(n + k)': ('n', 1), 'O(n + m)': ('n', 1), 'O(n × m)': ('n', 2),
            'O(n + m + z)': ('n', 1),
            'O(log n) query/update': ('log', 1),
            'O((n + q) √n)': ('n', 2),
            'O(n log n) average, O(n²) worst': ('n', 2),
            'O(n + m) average': ('n', 1),
            'O(n/m) best, O(nm) worst': ('n', 2),
            'O(m)': ('log', 1),
            'O(k)': ('const', 0),
            f'O(k{chr(178)})': ('n', 2), f'O(k{chr(179)})': ('n', 3),
            'O(kÂ²)': ('n', 2), 'O(k^2)': ('n', 2),
            'O(k log M)': ('log', 1),
            f'O(k{chr(179)} log n)': ('k3_log', 1),
            'O(k³ log n)': ('n', 3),
            'O(epochs × n × L × w)': ('n', 2),
            'O(epochs × batch × L × w)': ('n', 2),
            'O(iterations × n)': ('n', 1),
            'O(n × d²)': ('n', 2),
            'O(k × n log n × d)': ('n_log', 1),
            'O(k × n log n × √d)': ('n_log', 1),
            'O(9^m)': ('exp', 9),
            'O(iterations)': ('n', 1),
            'O(generations × population × fitness_cost)': ('n', 2),
            'O(1) average, O(n) worst': ('n', 1),
            'O(k³)': ('n', 3),
            'O(input size)': ('n', 1),
            'O(popcount(n)), worst-case O(log n)': ('log', 1),
            'O(expected)': ('n', 1),
            'O(2^n) worst, much better with good bounds': ('exp', 2),
            'O(b^(d/2))': ('exp', 2),
            'O(n × W)': ('n', 2),
            'O(n² × m)': ('n', 3),
            'O(n² × 2^n)': ('n_exp', 2),
            'O(n log n × d)': ('n_log', 1),
            'O(k × n)': ('n', 1),
            'O(n log n) build, O(log² n) query': ('n_log', 1),
            'O(k³ log n)': ('k3_log', 1), 'O(k^3 log n)': ('k3_log', 1),
        }
        fractional = re.fullmatch(r'O\(n\^([0-9]+(?:\.[0-9]+)?)\)', s)
        if fractional:
            exponent = float(fractional.group(1))
            return ('const', 0) if exponent <= 0 else ('n', exponent)
        if s in mapping:
            return mapping[s]
        if normalized in mapping:
            return mapping[normalized]
        return ('n', 1)

    def _tuple_to_string(self, c):
        type_c, pow_c = c
        mapping = {
            'const': 'O(1)', 'alpha': 'O(α(n))', 'loglog': 'O(log log n)',
            'log': 'O(log n)', 'log2': 'O(log² n)', 'log3': 'O(log³ n)',
            'log4': 'O(log^4 n)', 'sqrt': 'O(√n)',
            'n_log': 'O(n log n)', 'n_log2': 'O(n log² n)',
            'n2_log': 'O(n² log n)', 'n3_log': 'O(n³ log n)',
            'factorial': 'O(n!)', 'n_factorial': 'O(n * n!)',
            'ackermann': 'O(A(m, n))',
            'quasi_log_fact': 'O((log n)!)',
            'quasi_poly_half': 'O(n^((log n + 1)/2))',
            'quasi_poly': 'O(n^log n)',
            'n_exp': f'O(n * {pow_c}^n)', 'exp': f'O({pow_c}^n)',
            'strassen': 'O(n^2.807)',
            'phi_exp': 'O(φⁿ)',
            'v_times_ve': 'O(V * (V + E))',
            'k3_log': 'O(k³ log n)',
        }
        if type_c in mapping:
            return mapping[type_c]
        if type_c == 'logp':
            return f'O(log^{pow_c} n)'
        if type_c == 'n':
            if isinstance(pow_c, float) and pow_c.is_integer():
                pow_c = int(pow_c)
            if pow_c <= 0: return 'O(1)'
            if pow_c == 1: return 'O(n)'
            if pow_c == 2: return 'O(n²)'
            if pow_c == 3: return 'O(n³)'
            return f'O(n^{pow_c})'
        return 'O(n)'

    def _quadratic(self):
        return self._tuple_to_string(('n', 2))

    def _cubic(self):
        return self._tuple_to_string(('n', 3))

    def _alpha(self):
        return self._tuple_to_string(('alpha', 1))

    def _polynomial_complexity(self, power):
        if isinstance(power, float) and power.is_integer():
            power = int(power)
        if power <= 0:
            return 'O(1)'
        if power == 1:
            return 'O(n)'
        if power == 2:
            return self._quadratic()
        if power == 3:
            return self._cubic()
        return f'O(n^{power})'

    def detect_reduce_accumulator_copy(self, code, language):
        if not self._is_javascript_like(language):
            return {'detected': False}
        if '.reduce' not in code:
            return {'detected': False}

        compact = self._compact_ws(code)
        accumulator_names = set()
        for pattern in (
            r'\.reduce\s*\(\s*\(?\s*([A-Za-z_$][\w$]*)\s*,',
            r'\.reduce\s*\(\s*function\s*\(\s*([A-Za-z_$][\w$]*)\s*,',
        ):
            accumulator_names.update(re.findall(pattern, compact))

        for acc in accumulator_names:
            escaped = re.escape(acc)
            copies_growing_accumulator = bool(re.search(
                rf'(?:\[\s*\.\.\.\s*{escaped}\b|\{{\s*\.\.\.\s*{escaped}\b|'
                rf'\b{escaped}\s*\.\s*concat\s*\(|'
                rf'Object\.assign\s*\(\s*\{{\s*\}}\s*,\s*{escaped}\b|'
                rf'Array\.from\s*\(\s*{escaped}\b)',
                compact
            ))
            if copies_growing_accumulator:
                return {
                    'detected': True,
                    'pattern': 'reduce_accumulator_copy',
                    'complexity': self._quadratic(),
                    'space': 'O(n)',
                    'total_allocation': self._quadratic(),
                    'reason': (
                        'reduce() copies the growing accumulator on each iteration; '
                        '0+1+2+...+n copied elements gives quadratic work'
                    )
                }

        return {'detected': False}

    def detect_java_stream_pipeline(self, code, language):
        if language != 'java':
            return {'detected': False}
        if not re.search(r'\.(?:stream|parallelStream)\s*\(', code):
            return {'detected': False}

        compact = self._compact_ws(code)
        stream_count = len(re.findall(r'\.(?:stream|parallelStream)\s*\(', compact))
        materializes = bool(re.search(
            r'\.(?:collect|toList|toArray)\s*\(|Collectors\.(?:toList|toSet|toMap|groupingBy)',
            compact
        ))
        sorted_stage = bool(re.search(r'\.sorted\s*\(', compact))
        nested_stream = bool(
            stream_count >= 2 and re.search(r'\.flatMap(?:ToInt|ToLong|ToDouble)?\s*\(', compact)
        )
        callback_nested_scan = bool(re.search(
            r'\.(?:map|filter|flatMap|anyMatch|allMatch|noneMatch)\s*\([^;]*->[^;]*'
            r'(?:\.(?:stream|parallelStream)\s*\(|\.contains\s*\(|\.indexOf\s*\()',
            compact
        ))

        if nested_stream or callback_nested_scan:
            return {
                'detected': True,
                'pattern': 'java_nested_stream_pipeline',
                'complexity': self._quadratic(),
                'space': self._quadratic() if materializes else 'O(n)',
                'auxiliary_space': self._quadratic() if materializes else 'O(1)',
                'total_allocation': self._quadratic() if materializes else 'O(n)',
                'reason': (
                    'Nested Java Stream pipeline: an outer stream drives an inner stream/linear scan, '
                    'so it processes O(n²) element pairs'
                )
            }

        if sorted_stage:
            return {
                'detected': True,
                'pattern': 'java_stream_sorted',
                'complexity': 'O(n log n)',
                'space': 'O(n)',
                'auxiliary_space': 'O(n)',
                'reason': 'Java Stream sorted() buffers and sorts the stream elements'
            }

        return {
            'detected': True,
            'pattern': 'java_stream_pipeline',
            'complexity': 'O(n)',
            'space': 'O(n)' if materializes else 'O(n)',
            'auxiliary_space': 'O(n)' if materializes else 'O(1)',
            'total_allocation': 'O(n)',
            'reason': 'Java Stream pipeline performs an implicit linear traversal of the input collection'
        }

    def detect_implicit_iteration_complexity(self, code, language):
        if language == 'python':
            has_explicit_loop = self._has_explicit_loop_statement(code)
            if re.search(r'\[[^\]]*\bfor\b[^\]]*\bfor\b[^\]]*\]', code, re.DOTALL):
                return {
                    'detected': True, 'complexity': self._quadratic(), 'space': self._quadratic(),
                    'reason': 'Python list comprehension has two implicit nested iterations'
                }
            if re.search(r'\[[^\]]*\bfor\b[^\]]*\]|\{[^}]*\bfor\b[^}]*\}', code, re.DOTALL):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'Python comprehension materializes one output element per input element'
                }
            if re.search(r'\.\s*join\s*\(', code) and re.search(r'\bfor\b.+\bin\b', code, re.DOTALL):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'join over a generator visits each generated item and materializes an output string'
                }
            if not has_explicit_loop and re.search(r'\[[^\]\n]*:[^\]\n]*\]', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'Python slicing copies an input-sized sequence or string'
                }
            if not has_explicit_loop and re.search(r'\.\s*(?:lower|upper|casefold|replace|split)\s*\(', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'String transformation scans the input and returns a new string/list'
                }
            if re.search(r'\b(?:list|tuple|set)\s*\(', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'Built-in materializes an iterable with an implicit O(n) scan'
                }
            if re.search(r'\b(?:sum|min|max|any|all)\s*\(', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(1)',
                    'reason': 'Built-in consumes an iterable with an implicit O(n) scan'
                }
            compact = self._compact_ws(code)
            constant_sequence_vars = set(re.findall(
                r'\b(\w+)\s*=\s*(?:[rubfRUBF]{0,3})?[\'"][^\'"]*[\'"]',
                compact,
            ))
            for match in re.finditer(r'\b(\w+)\s+in\s+(\w+)\b', code):
                prefix = code[max(0, match.start() - 40):match.start()]
                if re.search(r'\bfor\b[^:;\n]*$', prefix):
                    continue
                if match.group(2) in constant_sequence_vars:
                    continue
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(1)',
                    'reason': 'Membership test over a sequence may scan O(n) elements'
                }
        if self._is_javascript_like(language):
            reduce_copy = self.detect_reduce_accumulator_copy(code, language)
            if reduce_copy.get('detected'):
                return reduce_copy
            if re.search(r'\.(?:map|filter|slice|concat)\s*\(|\[\s*\.\.\.', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(n)',
                    'reason': 'Array operation implicitly visits/copies O(n) elements'
                }
            if re.search(r'\.(?:reduce|forEach|some|every|find|includes|indexOf)\s*\(', code):
                return {
                    'detected': True, 'complexity': 'O(n)', 'space': 'O(1)',
                    'reason': 'Array method performs an implicit O(n) traversal'
                }
        return {'detected': False}

    def detect_binary_search_pattern(self, code, language):
        compact = self._compact_ws(code)
        if not re.search(r'\bwhile\b', compact):
            return {'detected': False}
        has_midpoint = bool(re.search(
            r'\b(?:mid|middle)\b\s*=.*?(?://\s*2|/\s*2|>>\s*1|Math\.floor\s*\()',
            compact
        ))
        lower_names = r'(?:lo|low|left|l|start)'
        upper_names = r'(?:hi|high|right|r|end)'
        moves_lower = bool(re.search(rf'\b{lower_names}\b\s*=\s*(?:mid|middle)\s*\+\s*1', compact))
        moves_upper = bool(re.search(rf'\b{upper_names}\b\s*=\s*(?:mid|middle)\s*-\s*1', compact))
        compares_mid = bool(re.search(r'\[[^\]]*(?:mid|middle)[^\]]*\]', compact))
        if has_midpoint and moves_lower and moves_upper and compares_mid:
            return {
                'detected': True,
                'complexity': 'O(log n)',
                'space': 'O(1)',
                'reason': 'Binary search halves the remaining search interval each iteration'
            }
        return {'detected': False}

    def detect_linear_membership_scan(self, code, language):
        if language == 'python':
            compact = self._compact_ws(code)
            hash_vars = set(re.findall(r'\b(\w+)\s*=\s*(?:set|dict)\s*\(', compact))
            hash_vars.update(re.findall(r'\b(\w+)\s*=\s*\{', compact))
            hash_vars.update(re.findall(r'\b(\w+)\s*\.\s*add\s*\(', compact))
            constant_sequence_vars = set(re.findall(
                r'\b(\w+)\s*=\s*(?:[rubfRUBF]{0,3})?[\'"][^\'"]*[\'"]',
                compact,
            ))
            list_vars = set(re.findall(r'\b(\w+)\s*=\s*\[\s*\]', compact))
            for match in re.finditer(r'\b(\w+)\s+in\s+(\w+)\b', compact):
                prefix = compact[max(0, match.start() - 40):match.start()]
                if re.search(r'\bfor\b[^:;]*$', prefix):
                    continue
                target = match.group(2)
                if target in hash_vars or target in constant_sequence_vars:
                    continue
                depth = self._max_operation_loop_depth(code, rf'\b\w+\s+in\s+{re.escape(target)}\b')
                complexity = self._polynomial_complexity(depth + 1)
                grows_target = target in list_vars and re.search(rf'\b{re.escape(target)}\s*\.\s*append\s*\(', compact)
                return {
                    'detected': True,
                    'complexity': complexity,
                    'space': 'O(n)' if grows_target else 'O(1)',
                    'reason': 'Membership test over a sequence scans O(n) elements; inside loops this adds another factor'
                }
        if self._is_javascript_like(language):
            if not re.search(r'\.(?:includes|indexOf)\s*\(', code):
                return {'detected': False}
            depth = self._max_operation_loop_depth(code, r'\.(?:includes|indexOf)\s*\(')
            return {
                'detected': True,
                'complexity': self._polynomial_complexity(depth + 1),
                'space': 'O(1)',
                'reason': 'Array membership search scans O(n) elements; inside loops this adds another factor'
            }
        if language == 'java':
            compact = self._compact_ws(code)
            if re.search(r'\b(?:HashSet|HashMap|TreeSet|TreeMap)\b', compact):
                return {'detected': False}
            if not re.search(r'\.contains\s*\(', compact):
                return {'detected': False}
            depth = self._max_operation_loop_depth(code, r'\.contains\s*\(')
            return {
                'detected': True,
                'complexity': self._polynomial_complexity(depth + 1),
                'space': 'O(1)',
                'reason': 'List/linear collection contains() scans O(n) elements; inside loops this adds another factor'
            }
        if language in ('cpp', 'c'):
            if not re.search(r'\b(?:std::)?find\s*\(', code):
                return {'detected': False}
            depth = self._max_operation_loop_depth(code, r'\b(?:std::)?find\s*\(')
            return {
                'detected': True,
                'complexity': self._polynomial_complexity(depth + 1),
                'space': 'O(1)',
                'reason': 'std::find over an iterator range scans O(n) elements; inside loops this adds another factor'
            }
        return {'detected': False}

    def detect_priority_queue_operations(self, code, language):
        compact = self._compact_ws(code)
        has_heap = bool(re.search(r'\bpriority_queue\s*<|\bPriorityQueue\s*<|\bheapq\b', compact))
        if not has_heap or not re.search(r'\b(?:for|while)\b', compact):
            return {'detected': False}
        has_heap_operation = bool(re.search(
            r'\.(?:push|pop|offer|poll|add)\s*\(|\bheapq\.(?:heappush|heappop)\s*\(',
            compact
        ))
        if not has_heap_operation:
            return {'detected': False}
        depth = max(1, self._loop_depth_hint(code))
        if depth >= 3:
            complexity = self._tuple_to_string(('n3_log', 1))
        elif depth == 2:
            complexity = self._tuple_to_string(('n2_log', 1))
        else:
            complexity = 'O(n log n)'
        return {
            'detected': True,
            'complexity': complexity,
            'space': self._polynomial_complexity(depth),
            'reason': 'Priority queue heap operations cost O(log n) inside the loop'
        }

    def detect_bulk_allocation_complexity(self, code, language):
        compact = self._compact_ws(code)
        two_dimensional = bool(re.search(
            r'\b(?:std::)?vector\s*<\s*(?:std::)?vector\s*<[^>]+>\s*>\s+\w+\s*\(\s*\w+\s*,\s*(?:std::)?vector\s*<[^>]+>\s*\(\s*\w+',
            compact
        )) or bool(re.search(r'\bnew\s+\w+\s*\[\s*\w+\s*\]\s*\[\s*\w+\s*\]', compact))
        if two_dimensional:
            return {
                'detected': True,
                'complexity': self._quadratic(),
                'space': self._quadratic(),
                'reason': 'Two-dimensional allocation materializes n by n storage'
            }

        one_dimensional = bool(re.search(
            r'\b(?:std::)?vector\s*<[^>]+>\s+\w+\s*\(\s*\w+\s*\)',
            compact
        )) or bool(re.search(r'\bnew\s+\w+\s*\[\s*\w+\s*\]', compact)) or bool(re.search(
            r'\bnew\s+Array\s*\(\s*\w+\s*\)|\bArray\s*\(\s*\w+\s*\)\s*\.fill',
            compact
        ))
        if one_dimensional:
            return {
                'detected': True,
                'complexity': 'O(n)',
                'space': 'O(n)',
                'reason': 'Input-sized allocation materializes n elements'
            }
        return {'detected': False}

    def detect_mutable_container_growth(self, code, language):
        compact = self._compact_ws(code)
        if not re.search(r'\b(?:for|while)\b', compact):
            return {'detected': False}
        has_container = bool(re.search(
            r'=\s*\[\s*\]|=\s*\{\s*\}|\bnew\s+(?:Map|Set|HashMap|HashSet|ArrayList)\b|'
            r'\b(?:unordered_)?map\s*<|\b(?:unordered_)?set\s*<|\b(?:std::)?vector\s*<',
            compact
        ))
        mutation_pattern = (
            r'(?:\.\s*(?:append|push|push_back|add|set|put|emplace|insert)\s*\(|'
            r'\b\w+\s*\[[^\]]+\]\s*(?:=(?!=)|\+\+|\+=))'
        )
        if not has_container or not re.search(mutation_pattern, compact):
            return {'detected': False}
        depth = self._max_operation_loop_depth(code, mutation_pattern)
        if depth <= 0:
            return {'detected': False}
        space = self._polynomial_complexity(depth)
        return {
            'detected': True,
            'complexity': space,
            'space': space,
            'reason': 'Mutable container stores one element per loop iteration combination'
        }

    def detect_materialized_subarray_serialization(self, code, language):
        if not self._is_javascript_like(language):
            return {'detected': False}

        compact = self._compact_ws(code)
        has_nested_pair_loops = len(re.findall(r'\bfor\s*\(', compact)) >= 2 and bool(re.search(
            r'for\s*\([^;]*\bi\b[^;]*;[^;]*(?:\.length|\bn\b)[^;]*;[^)]*\).*?'
            r'for\s*\([^;]*\bj\b\s*=\s*\bi\b[^;]*;[^;]*(?:\.length|\bn\b)[^;]*;[^)]*\)',
            compact
        ))
        has_materialized_slice = bool(re.search(r'\.slice\s*\(\s*\bi\b\s*,\s*\bj\b', compact))
        serializes_slice = bool(re.search(r'\bJSON\s*\.\s*stringify\s*\(|\.join\s*\(', compact))
        stores_serialized_value = bool(re.search(
            r'\b(?:set|seen|subs|subarrays|keys)\s*\.\s*(?:add|set)\s*\(|\bnew\s+Set\s*<',
            compact,
            re.IGNORECASE
        ))

        if has_nested_pair_loops and has_materialized_slice and serializes_slice:
            stores = stores_serialized_value or bool(re.search(r'\.add\s*\(\s*JSON\s*\.\s*stringify', compact))
            return {
                'detected': True,
                'pattern': 'materialized_subarray_serialization',
                'complexity': self._cubic(),
                'space': self._cubic() if stores else 'O(n)',
                'total_allocation': self._cubic(),
                'reason': (
                    'Nested subarray enumeration materializes arr.slice(i, j) for O(n²) ranges; '
                    'copying and JSON/string serialization scan up to O(n) elements per range'
                ),
            }
        return {'detected': False}

    def detect_bitmask_subset_enumeration(self, code, language):
        compact = self._compact_ws(code)
        outer = bool(re.search(
            r'for\s*\([^;]*\bmask\b[^;]*;[^;]*(?:<|<=)\s*\(?\s*1\s*<<\s*\w+\s*\)?',
            compact
        )) or bool(re.search(r'for\s+\w+\s+in\s+range\s*\(\s*1\s*<<\s*\w+\s*\)', compact))
        if not outer:
            return {'detected': False}
        scans_bits = bool(re.search(
            r'for\s*\([^;]*(?:\bi\b|\bbit\b)[^;]*;[^;]*(?:\bi\b|\bbit\b)\s*(?:<|<=)\s*\w+',
            compact
        )) or bool(re.search(r'for\s+\w+\s+in\s+range\s*\(\s*\w+\s*\)', compact))
        complexity = 'O(n * 2^n)' if scans_bits else 'O(2^n)'
        reason = (
            'Bitmask subset enumeration: the outer loop visits 2^n masks; the inner bit scan adds a factor n'
            if scans_bits else
            'Bitmask subset enumeration: the loop visits 2^n masks'
        )
        return {
            'detected': True, 'algorithm': 'Bitmask subset enumeration',
            'complexity': complexity, 'space': 'O(1)', 'reason': reason
        }

    def detect_immutable_string_concat(self, code, language):
        compact = self._compact_ws(code)
        if not re.search(r'\b(?:for|while)\b', compact):
            return {'detected': False}
        string_var = re.search(r'\b(\w+)\s*=\s*(["\'])\2', code)
        if not string_var:
            return {'detected': False}
        name = re.escape(string_var.group(1))
        if re.search(rf'\b{name}\s*\+=|\b{name}\s*=\s*{name}\s*\+', compact):
            return {
                'detected': True, 'complexity': self._quadratic(), 'space': 'O(n)',
                'reason': 'Immutable string concatenation inside a loop copies the growing prefix each iteration'
            }
        return {'detected': False}

    def detect_linear_front_insert(self, code, language):
        compact = self._compact_ws(code)
        if not re.search(r'\b(?:for|while)\b', compact):
            return {'detected': False}
        front_insert = bool(re.search(
            r'\.insert\s*\(\s*0\s*,|\.unshift\s*\(|\.add\s*\(\s*0\s*,|\.insert\s*\([^)]*\.begin\s*\(',
            compact
        ))
        if not front_insert:
            return {'detected': False}
        return {
            'detected': True, 'complexity': self._quadratic(), 'space': 'O(n)',
            'reason': 'Front insertion inside a loop shifts existing elements, so total work is quadratic'
        }

    def detect_nested_key_count(self, code, language):
        compact = self._compact_ws(code)
        if not self._is_javascript_like(language):
            return {'detected': False}
        if re.search(r'for\s*\(\s*(?:let|const|var)\s+\w+\s+in\s+(\w+)\s*\).*?for\s*\(\s*(?:let|const|var)\s+\w+\s+in\s+\1\s*\).*?count\s*\+\+', compact):
            return {
                'detected': True, 'complexity': self._quadratic(), 'space': 'O(1)',
                'reason': 'Nested object-key loops count every pair of keys'
            }
        return {'detected': False}

    def _loop_depth_hint(self, code):
        compact = self._compact_ws(code)
        loops = len(re.findall(r'\bfor\s*\(|\bfor\s+\w+\s+in\b|\bwhile\s*\(', compact))
        return max(1, loops)

    def detect_ordered_map_access(self, code, language):
        compact = self._compact_ws(code)
        has_ordered = bool(re.search(r'\bTreeMap\b|\bTreeSet\b|\bstd::map\b|\bstd::set\b|\bmap\s*<', compact))
        has_unordered = bool(re.search(r'\bunordered_map\b|\bHashMap\b|\bHashSet\b', compact))
        if not has_ordered or has_unordered:
            return {'detected': False}
        access = bool(re.search(r'\.(?:put|get|getOrDefault|remove|containsKey)\s*\(|\[[^\]]+\]\s*(?:\+\+|=|\+=)', compact))
        if not access:
            return {'detected': False}
        depth = self._loop_depth_hint(code)
        if depth >= 2:
            complexity, space = self._tuple_to_string(('n2_log', 1)), self._quadratic()
        else:
            complexity, space = 'O(n log n)', 'O(n)'
        return {
            'detected': True, 'complexity': complexity, 'space': space,
            'reason': 'Ordered map/tree lookup inside loop adds an O(log n) factor'
        }

    def detect_ordered_tree_drain(self, code, language):
        compact = self._compact_ws(code)
        has_ordered_tree = bool(re.search(
            r'\b(?:std::)?(?:multi)?set\s*<|\b(?:std::)?(?:multi)?map\s*<|'
            r'\b(?:multiset|set|multimap|map)\s*<|\bTreeSet\b|\bTreeMap\b',
            compact
        ))
        if not has_ordered_tree or not re.search(r'\bwhile\s*\(', compact):
            return {'detected': False}

        cpp_drain = bool(re.search(
            r'while\s*\(\s*!\s*\w+\.empty\s*\(\s*\)\s*\).*?'
            r'(?:\.begin\s*\(\s*\).*?)?\.erase\s*\(',
            compact,
            re.IGNORECASE
        ))
        java_drain = bool(re.search(
            r'while\s*\(\s*!\s*\w+\.isEmpty\s*\(\s*\)\s*\).*?'
            r'\.(?:remove|pollFirst|pollLast|firstEntry|pollFirstEntry|pollLastEntry)\s*\(',
            compact,
            re.IGNORECASE
        ))
        if not cpp_drain and not java_drain:
            return {'detected': False}

        return {
            'detected': True,
            'pattern': 'ordered_tree_drain',
            'complexity': 'O(n log n)',
            'space': 'O(n)',
            'auxiliary_space': 'O(1)',
            'reason': 'Draining an ordered tree container removes n nodes; each erase/remove is modeled as O(log n), and the container stores O(n) input elements'
        }

    def detect_recursive_ordered_map_access(self, code, language):
        compact = self._compact_ws(code)
        if not re.search(r'\bTreeMap\b|\bTreeSet\b|\bstd::map\b|\bstd::set\b|\bmap\s*<', compact):
            return {'detected': False}
        if not re.search(r'\.(?:put|remove|insert|erase)\s*\(', compact):
            return {'detected': False}
        if not re.search(r'\b(\w+)\s*\([^)]*(?:-\s*1|\+\s*1)[^)]*\)', compact):
            return {'detected': False}
        return {
            'detected': True, 'complexity': 'O(n log n)', 'space': 'O(n)',
            'reason': 'Recursive ordered map/set update: one or more TreeMap/tree-map updates per level cost O(log n) each'
        }

    def detect_hash_table_access(self, code, language):
        compact = self._compact_ws(code)
        has_hash = bool(re.search(r'\bHashMap\b|\bHashSet\b|\bunordered_map\b|\bunordered_set\b|\bnew\s+Map\s*\(', compact))
        if not has_hash or not re.search(r'\b(?:for|while)\b', compact):
            return {'detected': False}
        depth = self._loop_depth_hint(code)
        average = self._polynomial_complexity(depth)
        space = self._polynomial_complexity(depth)
        collision_hint = bool(re.search(r'\*\s*(?:16|1000003)|crafted|collision|cluster', compact, re.IGNORECASE))
        if re.search(r'\bunordered_map\b|\bunordered_set\b', compact) and collision_hint:
            worst = self._polynomial_complexity(max(2, depth * 2))
            return {
                'detected': True, 'complexity': f'{average} average, {worst} worst', 'space': space,
                'per_operation_worst': 'O(n)',
                'collision_worst_total': worst,
                'reason': f'Hash table access is O(1) average/amortized, but Collision-heavy worst-case total time is {worst}'
            }
        if collision_hint and re.search(r'\bHashMap\b|\bHashSet\b', compact):
            if depth >= 3:
                java_worst = self._tuple_to_string(('n3_log', 1))
            elif depth == 2:
                java_worst = self._tuple_to_string(('n2_log', 1))
            else:
                java_worst = 'O(n log n)'
            return {
                'detected': True,
                'complexity': average,
                'space': space,
                'per_operation_worst': 'O(log n)',
                'collision_worst_total': java_worst,
                'reason': (
                    'Hash table access inside the loop is O(1) average/amortized; '
                    f'Java HashMap treeifies long buckets, so collision-heavy total time is {java_worst}'
                )
            }
        return {
            'detected': True, 'complexity': average, 'space': space,
            'reason': 'Hash table access inside the loop is O(1) average/amortized; Java HashMap treeifies long buckets'
        }

    def _looks_like_recursive_slice_partition(self, func_name, body):
        if not func_name or not body:
            return False
        if bool(re.search(rf'\b{func_name}\s*\([^)]*\.slice\s*\(', body)) and bool(re.search(r'\.slice\s*\(', body)):
            return True
        escaped = re.escape(func_name)
        has_mid_halving = bool(re.search(
            r'\bmid\s*=\s*(?:len\s*\([^)]*\)|\w+(?:\.size\s*\(\))?)\s*(?://|/|>>)\s*2',
            body
        ))
        left_slice_call = bool(re.search(
            rf'\b{escaped}\s*\([^)]*\[[^\]]*:\s*mid\s*\]',
            body
        ))
        right_slice_call = bool(re.search(
            rf'\b{escaped}\s*\([^)]*\[\s*mid\s*:\s*[^\]]*\]',
            body
        ))
        return has_mid_halving and left_slice_call and right_slice_call

    def _looks_like_memoized_recursive_slice_keys(self, func_name, body):
        return (
            self._looks_like_recursive_slice_partition(func_name, body) and
            bool(re.search(r'\b(?:memo|cache)\b|\.join\s*\(|JSON\.stringify', body, re.IGNORECASE))
        )

    def _looks_like_recursive_resort_merge(self, func_name, body):
        return (
            bool(re.search(rf'\b{func_name}\s*\(', body)) and
            bool(re.search(r'\bsorted\s*\([^)]*\+[^)]*\)|\.sort\s*\(', body))
        )

    def _looks_like_binary_choice_backtracking(self, func_name, body):
        if not func_name or not body:
            return False
        escaped = re.escape(func_name)
        calls = re.findall(rf'\b{escaped}\s*\(([^)]*)\)', body)
        if len(calls) < 2:
            return False
        progresses = 0
        for args in calls:
            first_arg = args.split(',', 1)[0]
            if re.search(r'\b(?:index|idx|i|pos|start)\s*\+\s*1\b|\b(?:index|idx|i|pos|start)\s*-\s*1\b', first_arg):
                progresses += 1
        if progresses < 2:
            return False
        has_choice_mutation = bool(re.search(
            r'\.(?:append|push|add)\s*\(|\.(?:pop|remove)\s*\(',
            body,
            re.IGNORECASE
        ))
        has_length_base = bool(re.search(
            r'\b(?:index|idx|i|pos|start)\s*(?:==|>=)\s*len\s*\(|'
            r'\b(?:index|idx|i|pos|start)\s*(?:==|>=)\s*\w+\.size\s*\(\)',
            body
        ))
        return has_choice_mutation and has_length_base

    def _backtracking_materializes_results(self, body):
        return bool(re.search(
            r'\b(?:result|results|res|ans|output)\s*\.(?:append|push|add)\s*\(\s*(?:\w+\s*\[:\]|list\s*\(|new\s+ArrayList|\[[^\]]*\.\.\.)|'
            r'\b(?:result|results|res|ans|output)\s*\.(?:append|push|add)\s*\(',
            body,
            re.IGNORECASE
        ))

    def _looks_like_huffman_heap_driver(self, code, full_code=''):
        combined = self._compact_ws(f'{full_code}\n{code}')
        local = self._compact_ws(code)
        has_heap = bool(re.search(r'\bpriority_queue\s*<|\bPriorityQueue\s*<|\bheapq\b', local))
        if not has_heap:
            return False
        has_huffman_context = bool(re.search(
            r'huffman|freq|frequency|Node|left|right|code\s*\+\s*["\']?[01]',
            combined,
            re.IGNORECASE
        ))
        has_merge_loop = bool(re.search(
            r'(?:while|for)[^{;\n]*(?:size\s*\(\)\s*>\s*1|len\s*\([^)]*\)\s*>\s*1|\.size\s*>\s*1)',
            local,
            re.IGNORECASE
        ))
        pop_count = len(re.findall(r'\.(?:pop|poll)\s*\(|\bheapq\.heappop\s*\(', local))
        push_count = len(re.findall(r'\.(?:push|offer|add)\s*\(|\bheapq\.heappush\s*\(', local))
        return has_huffman_context and has_merge_loop and pop_count >= 2 and push_count >= 1

    def _looks_like_structural_tree_recursion(self, func_name, body):
        compact = self._compact_ws(body)
        recursive_child_calls = len(re.findall(
            rf'\b{re.escape(func_name)}\s*\(\s*\w+\s*(?:\.|->)\s*(?:left|right|child|children|next)\b',
            compact
        ))
        has_null_base = bool(re.search(r'\b(?:None|nullptr|null)\b|!\s*\w+', compact))
        return recursive_child_calls >= 1 and has_null_base

    def _looks_like_memoized_scalar_recursion(self, func_name, body, full_code=''):
        compact_body = self._compact_ws(body)
        compact_full = self._compact_ws(full_code)
        if not re.search(rf'\b{re.escape(func_name)}\s*\(', compact_body):
            return False
        has_cache_decorator = bool(re.search(
            rf'@(?:functools\.)?(?:lru_cache|cache)(?:\s*\([^)]*\))?\s*def\s+{re.escape(func_name)}\s*\(',
            full_code
        ))
        has_memo_table = bool(re.search(r'\b(?:memo|cache|dp)\b', compact_body, re.IGNORECASE))
        if not (has_cache_decorator or has_memo_table):
            return False
        if re.search(r'\.slice\s*\(|\[[^:\]]*:[^:\]]*\]|substring\s*\(|substr\s*\(', compact_body):
            return False
        return bool(re.search(r'\b\w+\s*[-+]\s*[12]\b', compact_body) or re.search(r'//\s*2|/\s*2', compact_body))

    def _looks_like_cpp_vector_string_memo_recursion(self, func_name, body, full_code=''):
        compact = self._compact_ws(f'{full_code}\n{body}')
        body_compact = self._compact_ws(body)
        has_unordered_string_memo = bool(re.search(r'unordered_map\s*<\s*string|unordered_map\s*<\s*std::string', compact))
        has_string_key = bool(re.search(r'(?:std::)?string\s+\w+\s*=', body_compact))
        builds_key_from_values = bool(re.search(r'for\s*\([^:;]+:\s*\w+\).*?\+=.*?to_string', body_compact))
        uses_memo_key = bool(re.search(r'\bmemo\s*\.(?:count|find)\s*\([^)]*key|memo\s*\[\s*key\s*\]', body_compact))
        copies_vector_halves = bool(re.search(r'vector\s*<[^>]+>\s+\w+\s*\([^)]*\.begin\s*\(\)', body_compact))
        recurses_on_splits = len(re.findall(rf'\b{func_name}\s*\([^)]*\b(?:left|right)\b', body_compact)) >= 2
        return (
            has_unordered_string_memo and has_string_key and builds_key_from_values and
            uses_memo_key and copies_vector_halves and recurses_on_splits
        )

    def _looks_like_looped_halving_recursion(self, func_name, body):
        compact = self._compact_ws(body)
        return bool(re.search(
            rf'for\s*\([^;]*;[^;]*<\s*\w+[^;]*;[^)]*\).*?\b{func_name}\s*\([^)]*(?:/\s*2|//\s*2|>>\s*1)',
            compact
        ))

    def _looks_like_union_find(self, code):
        compact = self._compact_ws(code)
        has_find = bool(re.search(r'\bdef\s+find\s*\(|\bfind\s*\(', compact))
        has_union = bool(re.search(r'\bdef\s+union\s*\(|\bunion\s*\(', compact))
        has_parent_compression = bool(re.search(r'parent\s*\[[^\]]+\]\s*=\s*find\s*\(\s*parent\s*\[', compact))
        has_rank_or_size = bool(re.search(r'\b(?:rank|size)\s*\[', compact))
        return has_find and has_union and has_parent_compression and has_rank_or_size

    def detect_recursive_shared_collection_growth(self, code, language):
        compact = self._compact_ws(code)
        match = re.search(r'function\s+(\w+)\s*\(([^)]*)\)', compact)
        if not match:
            return {'detected': False}
        func_name, params = match.group(1), match.group(2)
        param_match = re.search(r'(?:^|,)\s*(\w+)\s*=\s*\[\]', params)
        if not param_match:
            return {'detected': False}
        collection = param_match.group(1)
        calls = len(re.findall(rf'\b{func_name}\s*\([^)]*\b{collection}\b[^)]*\)', compact))
        pushes = bool(re.search(rf'\b{collection}\s*\.(?:push|append)\s*\(', compact))
        pops = bool(re.search(rf'\b{collection}\s*\.(?:pop)\s*\(', compact))
        if calls >= 2 and pushes and not pops:
            return {
                'detected': True, 'pattern': 'recursive_shared_collection_growth',
                'complexity': 'O(2^n)', 'space': 'O(2^n)',
                'reason': 'Branching recursion passes the same mutable collection; pushes are not undone, so it can grow once per recursive node'
            }
        return {'detected': False}

    def detect_memory_allocation_complexity(self, code, language, space_complexity=None, time_result=None):
        graph = self.detect_graph_algorithm(code)
        if graph.get('detected') and graph.get('algorithm') == 'Repeated DFS from All Nodes':
            return {
                'pattern': 'repeated_dfs_fresh_visited',
                'peak_live_auxiliary_space': 'O(V)',
                'total_allocated_space': 'O(V²)',
                'reason': (
                    'Each DFS call uses one fresh visited set with up to O(V) entries; '
                    'restarting from every vertex can allocate/insert O(V²) visited entries over the full run'
                )
            }
        shared = self.detect_recursive_shared_collection_growth(code, language)
        if shared['detected']:
            return {
                'pattern': shared['pattern'],
                'peak_live_auxiliary_space': 'O(2^n)',
                'total_allocated_space': 'O(2^n)',
                'reason': shared['reason']
            }
        materialized_subarrays = self.detect_materialized_subarray_serialization(code, language)
        if materialized_subarrays.get('detected'):
            return {
                'pattern': materialized_subarrays['pattern'],
                'peak_live_auxiliary_space': materialized_subarrays.get('space', self._cubic()),
                'total_allocated_space': materialized_subarrays.get('total_allocation', self._cubic()),
                'reason': (
                    'The Set can retain O(n²) serialized subarrays, and the total stored/copied '
                    'string content across all subarrays is O(n³)'
                )
            }
        ordered_tree_drain = self.detect_ordered_tree_drain(code, language)
        if ordered_tree_drain.get('detected'):
            return {
                'pattern': 'ordered_tree_drain',
                'peak_live_auxiliary_space': ordered_tree_drain.get('space', 'O(n)'),
                'total_allocated_space': ordered_tree_drain.get('space', 'O(n)'),
                'auxiliary_space': ordered_tree_drain.get('auxiliary_space', 'O(1)'),
                'reason': (
                    'The ordered tree container holds O(n) input nodes while the drain loop uses '
                    'only O(1) extra iterator/scalar storage'
                )
            }
        java_stream = self.detect_java_stream_pipeline(code, language)
        if java_stream.get('detected'):
            return {
                'pattern': java_stream.get('pattern', 'java_stream_pipeline'),
                'peak_live_auxiliary_space': java_stream.get('space', 'O(n)'),
                'total_allocated_space': java_stream.get('total_allocation', java_stream.get('space', 'O(n)')),
                'auxiliary_space': java_stream.get('auxiliary_space', 'O(1)'),
                'reason': (
                    'Java Stream pipelines hide iteration inside fluent calls; lazy terminals such as count() '
                    'avoid materializing all mapped results, while collect()/toList() retains the output'
                )
            }
        reduce_copy = self.detect_reduce_accumulator_copy(code, language)
        if reduce_copy.get('detected'):
            return {
                'pattern': 'reduce_accumulator_copy',
                'peak_live_auxiliary_space': reduce_copy.get('space', 'O(n)'),
                'total_allocated_space': reduce_copy.get('total_allocation', self._quadratic()),
                'reason': (
                    'reduce() returns a fresh copied accumulator on every step; peak live output is linear, '
                    'but cumulative copied/allocated array entries are quadratic'
                )
            }
        immutable_concat = self.detect_immutable_string_concat(code, language)
        if immutable_concat.get('detected'):
            return {
                'pattern': 'immutable_string_concat_loop',
                'peak_live_auxiliary_space': 'O(n)',
                'total_allocated_space': self._quadratic(),
                'reason': (
                    'Repeated immutable string concatenation creates growing temporary strings; '
                    'peak live string data is O(n), but cumulative copied/allocated characters are quadratic'
                )
            }
        bulk_allocation = self.detect_bulk_allocation_complexity(code, language)
        if bulk_allocation.get('detected'):
            return {
                'pattern': 'bulk_allocation',
                'peak_live_auxiliary_space': bulk_allocation.get('space', 'O(n)'),
                'total_allocated_space': bulk_allocation.get('space', 'O(n)'),
                'reason': bulk_allocation.get('reason', 'Input-sized allocation materializes storage')
            }
        mutable_growth = self.detect_mutable_container_growth(code, language)
        if mutable_growth.get('detected'):
            return {
                'pattern': 'mutable_container_growth',
                'peak_live_auxiliary_space': mutable_growth.get('space', 'O(n)'),
                'total_allocated_space': mutable_growth.get('space', 'O(n)'),
                'reason': mutable_growth.get('reason', 'Mutable container grows with loop iterations')
            }
        func_names = self._function_names(code, language)
        for name in func_names:
            body = self._extract_function_body(code, name, language)
            if self._looks_like_cpp_vector_string_memo_recursion(name, body, code):
                return {
                    'pattern': 'cpp_vector_string_memo_recursion',
                    'peak_live_auxiliary_space': self._quadratic(),
                    'total_allocated_space': self._quadratic(),
                    'reason': 'C++ recursive vector splits and serialized memo keys can retain/copy quadratic total key/vector data'
                }
            if self._looks_like_memoized_recursive_slice_keys(name, body):
                return {
                    'pattern': 'memoized_recursive_slice_keys',
                    'peak_live_auxiliary_space': 'O(n log n)',
                    'total_allocated_space': 'O(n log n)',
                    'reason': 'Memoized recursive slicing materializes serialized keys and copied slices'
                }
            if self._looks_like_recursive_resort_merge(name, body):
                return {
                    'pattern': 'recursive_resort_merge_copy',
                    'peak_live_auxiliary_space': 'O(n)',
                    'total_allocated_space': 'O(n log n)',
                    'reason': (
                        'Recursive slices, left + right concatenation, and sorted(left + right) '
                        'materialize O(n) data per recursion level'
                    )
                }
            if self._looks_like_recursive_slice_partition(name, body):
                return {
                    'pattern': 'recursive_slice_copy',
                    'peak_live_auxiliary_space': 'O(n)',
                    'total_allocated_space': 'O(n log n)',
                    'reason': 'Recursive divide-and-conquer copies slices at each level'
                }
        return {
            'pattern': 'direct_auxiliary_space',
            'peak_live_auxiliary_space': space_complexity or 'O(1)',
            'total_allocated_space': space_complexity or 'O(1)',
            'reason': 'Peak auxiliary space follows the detected data structures and recursion depth'
        }

    def explain_space_complexity(self, code, language, space_complexity, memory_analysis=None):
        memory_analysis = memory_analysis or {}
        pattern = memory_analysis.get('pattern')
        if pattern == 'recursive_shared_collection_growth':
            return memory_analysis.get('reason', 'Same mutable collection grows across recursive branches')
        if pattern == 'recursive_slice_copy':
            return 'Total allocated slice memory is O(n log n), while peak live auxiliary space is O(n)'
        if pattern == 'recursive_resort_merge_copy':
            return 'Peak live list data is O(n), while slices, left + right, and sorted(left + right) allocate O(n log n) total data'
        if pattern == 'memoized_recursive_slice_keys':
            return 'Memo table stores materialized memo keys/serialized keys plus copied slices'
        if pattern == 'cpp_vector_string_memo_recursion':
            return 'Memo table string keys plus copied vectors can retain/copy O(n²) auxiliary data in the conservative model'
        if pattern == 'materialized_subarray_serialization':
            return 'Set stores serialized subarrays: O(n²) entries with up to O(n) characters each, so worst-case auxiliary space is O(n³)'
        if pattern == 'repeated_dfs_fresh_visited':
            return 'Peak visited set and recursion stack are O(V), while repeated fresh visited sets allocate O(V²) total entries over all starts'
        if pattern == 'reduce_accumulator_copy':
            return 'Peak returned accumulator space is O(n), but copying the growing accumulator inside reduce() allocates O(n²) total array entries'
        if pattern == 'ordered_tree_drain':
            return 'The ordered tree container itself holds O(n) elements; the drain loop uses only O(1) extra auxiliary variables'
        if pattern == 'java_nested_stream_pipeline':
            if memory_analysis.get('auxiliary_space') == 'O(1)':
                return 'The input list holds O(n) elements; count() consumes the nested streams lazily, so extra pipeline space is O(1)'
            return 'Nested Java streams materialize O(n²) output when collected into a list/array/map'
        if pattern == 'java_stream_sorted':
            return 'Java Stream sorted() buffers elements for sorting, using O(n) space'
        if pattern == 'java_stream_pipeline':
            return 'The input collection holds O(n) elements; the stream pipeline itself uses only small iterator state unless it collects output'
        if pattern == 'immutable_string_concat_loop':
            return 'Peak final string space is O(n), but repeated immutable concatenation allocates O(n²) total copied characters'
        if pattern == 'bulk_allocation':
            return memory_analysis.get('reason', 'Input-sized allocation materializes auxiliary storage')
        if pattern == 'mutable_container_growth':
            return memory_analysis.get('reason', 'Mutable container growth determines auxiliary space')
        if self.detect_recursive_ordered_map_access(code, language).get('detected'):
            return 'Recursive ordered map/set update keeps one inserted entry per active level'
        if self._sorting_complexity(code) and re.search(r'\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\(', code):
            if self._sorting_space_complexity(code, language) == 'O(n)':
                return 'built-in stable/dynamic sort may use linear auxiliary space in this language runtime model'
            return 'sort operation uses logarithmic auxiliary stack space in this runtime model'
        if space_complexity == 'O(1)':
            return 'Only a constant number of scalar variables are allocated'
        return f'Auxiliary data structures or recursion account for {space_complexity} space'

    def _sorting_space_complexity(self, code, language, has_array=False, has_dict=False, has_cpp_vector_alloc=False):
        if language in ('javascript', 'typescript'):
            return 'O(n)'
        if language == 'python':
            return 'O(n)'
        if has_array or has_dict or has_cpp_vector_alloc:
            return 'O(n)'
        return 'O(log n)'

    def _unknown_call_names(self, code, language, extra_known_defs=None):
        known_defs = set(self._function_names(code, language))
        known_defs.update(self._class_names(code, language))
        if extra_known_defs:
            known_defs.update(extra_known_defs)
        builtins = {
            'range', 'len', 'sum', 'min', 'max', 'print', 'str', 'int', 'float',
            'list', 'dict', 'set', 'tuple', 'sorted', 'Math', 'console',
            'Set', 'Map', 'JSON', 'slice', 'stringify', 'add', 'open', 'input',
            'enumerate', 'zip', 'map', 'filter', 'any', 'all', 'abs', 'round',
            'bool', 'isinstance', 'choice', 'randint', 'callable', 'compile',
            'exec', 'eval', 'next', 'iter', 'super', 'type', 'repr', 'id', 'hash',
            'dir', 'vars', 'locals', 'globals', 'getattr', 'setattr', 'hasattr',
            'delattr', 'Exception', 'BaseException', 'ValueError', 'TypeError',
            'KeyError', 'IndexError', 'AttributeError', 'RuntimeError',
            'NotImplementedError', 'StopIteration', 'ImportError', 'OSError',
            'FileNotFoundError', 'enumerate', 'reversed', 'pow', 'divmod'
        }
        searchable = self._strip_string_literals(code)
        calls = set(re.findall(r'(?<!\.)\b([A-Za-z_]\w*)\s*\(', searchable))
        keywords = {'if', 'for', 'while', 'switch', 'return', 'function'}
        return sorted(c for c in calls if c not in known_defs and c not in builtins and c not in keywords)

    def _analysis_confidence_summary(self, code, language, time_result):
        notes = []
        if language == 'unknown':
            notes.append('Language could not be inferred from the filename.')
        if language == 'python':
            try:
                ast.parse(code)
            except SyntaxError:
                notes.append('Python syntax could not be parsed cleanly.')

        dynamic_notes = self._dynamic_construct_confidence_notes(code, language)
        notes.extend(dynamic_notes)

        unknown_calls = self._unknown_call_names(code, language)
        if unknown_calls:
            preview = ', '.join(unknown_calls[:5])
            suffix = '...' if len(unknown_calls) > 5 else ''
            notes.append(f'External/library call(s) modeled by fallback estimate: {preview}{suffix}.')

        if 'unknown' in str(time_result.get('complexity') or '').lower():
            reason = ' '.join(notes) if notes else 'External/library call needs a fallback estimate.'
            return {'time': 'medium', 'space': 'medium', 'reason': reason, 'notes': notes or [reason]}

        graph = self.detect_graph_algorithm(code)
        if graph.get('detected') and not notes:
            reason = f"Matched graph algorithm pattern: {graph.get('algorithm', 'graph traversal')}."
            return {'time': 'high', 'space': 'high', 'reason': reason, 'notes': [reason]}

        if self.detect_materialized_subarray_serialization(code, language).get('detected') and not notes:
            reason = 'Matched explicit nested subarray serialization/storage pattern.'
            return {'time': 'high', 'space': 'high', 'reason': reason, 'notes': [reason]}

        if self.detect_implicit_iteration_complexity(code, language).get('detected'):
            notes.append('Implicit iteration was detected heuristically.')
            return {
                'time': 'medium',
                'space': 'medium',
                'reason': ' '.join(notes),
                'notes': notes,
            }

        if notes:
            return {
                'time': 'medium',
                'space': 'medium',
                'reason': ' '.join(notes),
                'notes': notes,
            }

        reason = 'Matched explicit loops, recursion, or known patterns.'
        return {'time': 'high', 'space': 'high', 'reason': reason, 'notes': [reason]}

    def analyze_semantic_assumptions(self, code, language, input_schema=None, concrete_inputs=None, time_result=None, memory_analysis=None):
        items = []
        input_schema = input_schema or {}
        time_result = time_result or {}
        memory_analysis = memory_analysis or {}

        parameters = input_schema.get('parameters') or []
        if parameters:
            names = ', '.join(p.get('name', '') for p in parameters if p.get('name'))
            if concrete_inputs:
                items.append({
                    'category': 'runtime_inputs',
                    'severity': 'info',
                    'title': 'Concrete inputs are examples',
                    'message': 'Provided values are used for concrete estimates; symbolic Big-O still describes growth when inputs vary.',
                    'evidence': names,
                })
            else:
                items.append({
                    'category': 'runtime_inputs',
                    'severity': 'medium',
                    'title': 'Input constraints not provided',
                    'message': 'Big-O assumes input-sized parameters can grow according to their detected roles. Tighter constraints can lower the effective bound.',
                    'evidence': names,
                })
        else:
            items.append({
                'category': 'runtime_inputs',
                'severity': 'low',
                'title': 'No analyzable parameters detected',
                'message': 'The analyzer uses code structure only because no public input parameters were detected.',
                'evidence': input_schema.get('reason', ''),
            })

        unknown_calls = self._unknown_call_names(code, language)
        if unknown_calls:
            preview = ', '.join(unknown_calls[:6])
            suffix = '...' if len(unknown_calls) > 6 else ''
            items.append({
                'category': 'libraries',
                'severity': 'medium',
                'title': 'External helper calls',
                'message': 'Calls without local definitions are modeled with a deterministic fallback estimate, but their internal implementation can add cost.',
                'evidence': f'{preview}{suffix}',
            })

        for item in self._library_semantic_items(code, language, time_result):
            items.append(item)
        for item in self._side_effect_semantic_items(code, language):
            items.append(item)

        if memory_analysis.get('total_allocated_space') and memory_analysis.get('total_allocated_space') != memory_analysis.get('peak_live_auxiliary_space'):
            items.append({
                'category': 'memory_model',
                'severity': 'info',
                'title': 'Peak memory differs from allocation churn',
                'message': 'Total allocated/copied memory is cumulative over the run and is not the same as peak live space.',
                'evidence': f"peak={memory_analysis.get('peak_live_auxiliary_space')}, total={memory_analysis.get('total_allocated_space')}",
            })

        confidence = 'high'
        if any(item['severity'] == 'high' for item in items):
            confidence = 'low'
        elif any(item['severity'] == 'medium' for item in items):
            confidence = 'medium'

        return {
            'available': True,
            'confidence': confidence,
            'items': items,
            'summary': self._semantic_summary(confidence, items),
        }

    def _semantic_summary(self, confidence, items):
        if confidence == 'high':
            return 'No major semantic blockers were detected; the Big-O is based on visible code and known runtime models.'
        if confidence == 'medium':
            return 'Some input or runtime assumptions affect how the Big-O should be interpreted.'
        return 'External helper behavior or side effects may change the real cost beyond the visible code.'

    def _library_semantic_items(self, code, language, time_result):
        compact = self._compact_ws(code)
        items = []
        if re.search(r'\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\(', compact):
            items.append({
                'category': 'libraries',
                'severity': 'medium',
                'title': 'Sort complexity is runtime/library dependent',
                'message': 'The analyzer uses the language runtime model for built-in sorting; constants and auxiliary space can vary by implementation and data type.',
                'evidence': 'sort/sorted call',
            })
        if re.search(r'\b(?:HashMap|HashSet|unordered_map|unordered_set|new\s+Map\s*\(|new\s+Set\s*\()', compact):
            items.append({
                'category': 'libraries',
                'severity': 'medium',
                'title': 'Hash table cost depends on collisions',
                'message': 'Reported hash-table bounds separate average/amortized behavior from collision-heavy worst cases when the pattern is visible.',
                'evidence': 'hash table usage',
            })
        if re.search(r'\b(?:TreeMap|TreeSet|(?:std::)?(?:multi)?(?:map|set)\s*<)', compact):
            items.append({
                'category': 'libraries',
                'severity': 'info',
                'title': 'Ordered tree runtime model',
                'message': 'Ordered map/set operations are modeled with logarithmic tree costs unless a more specific standard guarantee is required.',
                'evidence': 'ordered tree container',
            })
        if re.search(r'\.(?:stream|parallelStream)\s*\(', compact):
            items.append({
                'category': 'libraries',
                'severity': 'medium',
                'title': 'Stream pipeline laziness matters',
                'message': 'Java Stream cost depends on terminal operations: count() can be lazy, while collect()/toList()/toArray() materialize output.',
                'evidence': 'Java Stream pipeline',
            })
        if 'unknown' in str(time_result.get('complexity') or '').lower():
            items.append({
                'category': 'libraries',
                'severity': 'medium',
                'title': 'Fallback complexity estimate',
                'message': 'A required operation used the deterministic fallback model instead of a local implementation body.',
                'evidence': time_result.get('reason', ''),
            })
        return items

    def _side_effect_semantic_items(self, code, language):
        compact = self._compact_ws(code)
        checks = [
            (r'\bprint\s*\(|System\.out\.|console\.', 'io', 'Output side effect', 'Printing/logging cost depends on output size and runtime sink.'),
            (r'\bopen\s*\(|\bFiles\.|FileInputStream|FileOutputStream|fs\.|readFile|writeFile', 'io', 'File I/O side effect', 'File I/O can dominate CPU Big-O and depends on external storage.'),
            (r'\bfetch\s*\(|axios\.|requests\.|HttpClient|URLConnection|socket', 'io', 'Network side effect', 'Network calls have external latency and payload costs outside pure algorithmic Big-O.'),
            (r'executeQuery|executeUpdate|PreparedStatement|Statement\s*\(|sqlite|cursor\.execute', 'io', 'Database side effect', 'Database queries depend on indexes, query plans, data volume, and remote latency.'),
            (r'\bThread\b|synchronized|CompletableFuture|async\s+|await\s+', 'concurrency', 'Concurrency/runtime scheduling', 'Parallel or asynchronous execution can change wall-clock behavior without changing total work.'),
            (r'\b(?:random|Math\.random|Random\s*\(|time\.time|System\.currentTimeMillis|Date\s*\()', 'runtime', 'Runtime-dependent value', 'Random/time-dependent branches can make behavior input-distribution dependent.'),
        ]
        items = []
        for pattern, category, title, message in checks:
            if re.search(pattern, compact, re.IGNORECASE):
                items.append({
                    'category': category,
                    'severity': 'medium',
                    'title': title,
                    'message': message,
                    'evidence': pattern,
                })

        if self._mutates_input_parameters(code, language):
            items.append({
                'category': 'intended_behavior',
                'severity': 'medium',
                'title': 'Function mutates input state',
                'message': 'Same-behavior optimizations must preserve mutations and observable side effects, not only return values.',
                'evidence': 'input container mutation',
            })
        return items

    def _mutates_input_parameters(self, code, language):
        signature = self._primary_function_signature(code, language)
        if not signature:
            return False
        param_names = [p.get('name') for p in signature.get('params', []) if p.get('name')]
        if not param_names:
            return False
        compact = self._compact_ws(code)
        mutators = (
            r'(?:append|extend|insert|remove|pop|clear|sort|reverse|add|delete|set|put|erase|push|splice)'
        )
        for name in param_names:
            escaped = re.escape(name)
            if re.search(rf'\b{escaped}\s*\.\s*{mutators}\s*\(', compact):
                return True
            if re.search(rf'\b{escaped}\s*\[[^\]]+\]\s*(?:=|\+=|-=|\+\+|--)', compact):
                return True
        return False

    def _dynamic_construct_confidence_notes(self, code, language):
        checks = [
            (r'\beval\s*\(', 'Dynamic eval can hide runtime work.'),
            (r'\bexec\s*\(', 'Dynamic exec can hide runtime work.'),
            (r'\bgetattr\s*\(', 'Dynamic attribute lookup can hide called behavior.'),
            (r'\bglobals\s*\(|\blocals\s*\(', 'Dynamic namespace access can hide called behavior.'),
            (r'\bClass\.forName\s*\(|\.getMethod\s*\(|\.invoke\s*\(', 'Reflection can hide called behavior.'),
            (r'\brequire\s*\([^)]*[^"\']', 'Dynamic require/import can hide library behavior.'),
        ]
        if language in ('cpp', 'c') and re.search(r'^\s*#\s*define\b', code, re.MULTILINE):
            return ['Preprocessor macros can hide repeated work from static pattern analysis.']
        return [message for pattern, message in checks if re.search(pattern, code)]

    def _fallback_unresolved_call_time(self, code, language, unknown_calls):
        unknown_calls = [str(call) for call in (unknown_calls or []) if call]
        signature = self._primary_function_signature(code, language) or {}
        param_names = [
            str(param.get('name'))
            for param in signature.get('params', [])
            if param.get('name')
        ]
        compact = self._compact_ws(code)
        receives_input_parameter = False
        for call in unknown_calls:
            call_pattern = re.search(rf'\b{re.escape(call)}\s*\(([^)]*)\)', compact)
            if not call_pattern:
                continue
            args = call_pattern.group(1)
            if any(re.search(rf'\b{re.escape(param)}\b', args) for param in param_names):
                receives_input_parameter = True
                break

        calls_text = ', '.join(unknown_calls)
        if receives_input_parameter:
            return {
                'complexity': 'O(n)',
                'reason': (
                    f"External call(s) {calls_text} receive input-sized data, so CodeScope reports "
                    "a conservative O(n) estimate instead of leaving the call unresolved."
                ),
                'recursion': None,
            }

        return {
            'complexity': 'O(1)',
            'reason': (
                f"External call(s) {calls_text} have no visible input-sized loop or recursion, "
                "so CodeScope reports O(1) dispatch cost instead of leaving the call unresolved."
            ),
            'recursion': None,
        }

    def build_overall_complexity_summary(self, time_complexity, space_complexity, memory_analysis=None):
        memory_analysis = memory_analysis or {}
        total_allocation = memory_analysis.get('total_allocated_space', space_complexity)
        peak_live = memory_analysis.get('peak_live_auxiliary_space', space_complexity)
        if total_allocation and total_allocation != space_complexity:
            headline = (
                f'{time_complexity} time, {space_complexity} space, '
                f'{total_allocation} total allocation'
            )
            memory_model = (
                f'Space complexity is reported as {space_complexity}. Peak live auxiliary memory is {peak_live}; '
                f'total allocated/copied memory over the full run is {total_allocation}.'
            )
        else:
            headline = f'{time_complexity} time, {space_complexity} space'
            if peak_live != space_complexity:
                memory_model = (
                    f'Space complexity is reported as {space_complexity}. '
                    f'Peak live auxiliary memory is {peak_live}.'
                )
            else:
                memory_model = f'Space complexity is {space_complexity}.'
        return {
            'time': time_complexity,
            'space': space_complexity,
            'peak_space': peak_live,
            'total_allocation': total_allocation,
            'headline': headline,
            'memory_model': memory_model,
            'space_label': 'Space Complexity',
            'allocation_label': 'Total Allocated/Copied Memory'
        }

    def _build_recurrence_analysis(self, time_result):
        recursion = time_result.get('recursion') if isinstance(time_result, dict) else None
        if not isinstance(recursion, dict) or not recursion.get('is_recursive'):
            return None

        structured = recursion.get('recurrence_analysis')
        if structured:
            return {
                **structured,
                'function': recursion.get('func_name'),
                'confidence': 'high',
            }

        reason = recursion.get('reason') or time_result.get('reason') or ''
        if 'Master' in reason or 'recurrence' in reason or 'T(n)' in reason:
            return {
                'method': 'recurrence-pattern',
                'function': recursion.get('func_name'),
                'recurrence': reason,
                'branch_count': recursion.get('branches'),
                'complexity': recursion.get('complexity') or time_result.get('complexity'),
                'confidence': 'medium',
                'reason': 'CodeScope matched this recursive function to a known recurrence pattern.',
            }
        return None

    # ─────────────────────────────────────────────
    # MAIN TIME COMPLEXITY DETECTION
    # ─────────────────────────────────────────────

    def detect_time_complexity(self, code, language, extra_known_defs=None):
        detection_code = self._strip_string_literals(code)
        if extra_known_defs:
            detection_code = self._mask_known_call_names(detection_code, extra_known_defs)

        graph = self.detect_graph_algorithm(detection_code)
        if graph['detected']:
            return {'complexity': graph['complexity'], 'reason': graph['reason'], 'graph': graph, 'recursion': None}

        known = self.detect_known_algorithm(detection_code)
        if known['detected'] and known.get('algorithm') != 'Dynamic Programming':
            return {'complexity': known['complexity'], 'reason': known['reason'], 'known': known, 'recursion': None}

        bit_clear = self._find_bit_clear_function(detection_code, language)
        if bit_clear:
            return {
                'complexity': 'O(popcount(n)), worst-case O(log n)',
                'reason': 'The loop uses n = n & (n - 1), so it runs once per set bit; worst case is the word/input bit length.',
                'known': None, 'recursion': None, 'graph': None
            }

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_cpp_vector_string_memo_recursion(name, body, code):
                return {
                    'complexity': f'{self._quadratic()} average, {self._cubic()} worst',
                    'reason': (
                        'C++ recursive vector split with string-key memoization: vector copies and '
                        'serialized key construction are conservatively counted as quadratic on average; '
                        'unordered_map collision chains can add another factor.'
                    ),
                    'known': None, 'recursion': None, 'graph': None
                }
            if self._looks_like_structural_tree_recursion(name, body):
                return {
                    'complexity': 'O(n)',
                    'reason': 'Tree traversal recursion visits each node once; recursion depth is the tree height',
                    'known': None, 'recursion': None, 'graph': None
                }
            if self._looks_like_memoized_scalar_recursion(name, body, code):
                return {
                    'complexity': 'O(n)',
                    'reason': 'Memoization/cache computes each scalar subproblem once',
                    'known': None, 'recursion': None, 'graph': None
                }

        recursion = self.analyze_recursion(code, language)
        mutual_recursion = self.detect_mutual_recursion(code, language)

        if known['detected']:
            return {'complexity': known['complexity'], 'reason': known['reason'], 'known': known, 'recursion': None}

        if mutual_recursion['detected']:
            return {
                'complexity': mutual_recursion['complexity'],
                'reason': mutual_recursion['reason'],
                'known': None, 'recursion': mutual_recursion, 'graph': None
            }

        regex = self.detect_catastrophic_regex(code)
        if regex['detected']:
            return {'complexity': regex['complexity'], 'reason': regex['reason'], 'known': None, 'recursion': None, 'graph': None}

        for detector in (
            self.detect_recursive_ordered_map_access,
            self.detect_ordered_map_access,
            self.detect_ordered_tree_drain,
            self.detect_hash_table_access,
            self.detect_dynamic_execution_complexity,
            self.detect_binary_search_pattern,
            self.detect_sqrt_iteration_complexity,
            self.detect_priority_queue_operations,
            self.detect_linear_front_insert,
            self.detect_immutable_string_concat,
            self.detect_linear_membership_scan,
            self.detect_bulk_allocation_complexity,
            self.detect_nested_key_count,
            self.detect_materialized_subarray_serialization,
            self.detect_bitmask_subset_enumeration,
            self.detect_reduce_accumulator_copy,
            self.detect_java_stream_pipeline,
            self.detect_file_io_complexity,
            self.detect_implicit_iteration_complexity,
        ):
            detected = detector(code, language)
            if detected.get('detected'):
                return {
                    'complexity': detected['complexity'],
                    'reason': detected['reason'],
                    'known': None, 'recursion': None, 'graph': None
                }

        special_loop = self.detect_special_loop_patterns(code, language)
        if special_loop['detected']:
            return {'complexity': special_loop['complexity'], 'reason': special_loop['reason'], 'known': None, 'recursion': None, 'graph': None}

        loops = self.extract_loop_tree(code, language)
        loop_complexity = self.compute_loop_complexity(loops)
        sorting_complexity = self._sorting_complexity(detection_code)

        if not loops and not recursion['is_recursive'] and not sorting_complexity:
            unknown_calls = self._unknown_call_names(code, language, extra_known_defs=extra_known_defs)
            if unknown_calls:
                return self._fallback_unresolved_call_time(code, language, unknown_calls)
            return {'complexity': 'O(1)', 'reason': 'No loops or recursion found', 'recursion': None}

        candidates = []
        reasons = []
        if loop_complexity:
            candidates.append(loop_complexity)
            reasons.append(f'Loop analysis: {loop_complexity}')
        if recursion['is_recursive']:
            candidates.append(recursion['complexity'])
            reasons.append(recursion['reason'])
        if sorting_complexity:
            candidates.append(sorting_complexity)
            reasons.append(f'Sorting detected: {sorting_complexity}')

        if not candidates:
            return {'complexity': 'O(1)', 'reason': 'No significant operations', 'recursion': None}

        return {
            'complexity': self._max_complexity(candidates),
            'reason': ' | '.join(reasons),
            'recursion': recursion if recursion['is_recursive'] else None,
            'graph': None
        }

    # ─────────────────────────────────────────────
    # SPACE COMPLEXITY
    # ─────────────────────────────────────────────

    def detect_space_complexity(self, code, language):
        graph = self.detect_graph_algorithm(code)
        if graph['detected']:
            return graph.get('space', 'O(V + E)')

        known = self.detect_known_algorithm(code)
        if known['detected']:
            return known.get('space', 'O(n)')

        regex = self.detect_catastrophic_regex(code)
        if regex['detected']:
            return regex.get('space', 'O(n)')

        mutual_recursion = self.detect_mutual_recursion(code, language)
        if mutual_recursion['detected']:
            return mutual_recursion.get('space', 'O(n)')

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_cpp_vector_string_memo_recursion(name, body, code):
                return self._quadratic()
            if self.detect_binary_search_pattern(body, language).get('detected'):
                return 'O(1)'
            if self._looks_like_structural_tree_recursion(name, body):
                return 'O(h)'
            if self._looks_like_memoized_scalar_recursion(name, body, code):
                return 'O(n)'
            if self._looks_like_looped_halving_recursion(name, body):
                return 'O(log n)'
            if self._looks_like_matrix_power_recursion(
                name,
                body,
                getattr(self, 'last_func_own_complexities', {}) or getattr(self, 'last_func_complexities', {})
            ):
                return 'O(k²)'
            if self._looks_like_memoized_recursive_slice_keys(name, body):
                return 'O(n log n)'
            if self._looks_like_recursive_slice_partition(name, body):
                return 'O(n log n)'

        detected_spaces = []
        for detector in (
            self.detect_recursive_shared_collection_growth,
            self.detect_recursive_ordered_map_access,
            self.detect_ordered_map_access,
            self.detect_ordered_tree_drain,
            self.detect_hash_table_access,
            self.detect_dynamic_execution_complexity,
            self.detect_binary_search_pattern,
            self.detect_sqrt_iteration_complexity,
            self.detect_priority_queue_operations,
            self.detect_linear_front_insert,
            self.detect_immutable_string_concat,
            self.detect_linear_membership_scan,
            self.detect_bulk_allocation_complexity,
            self.detect_nested_key_count,
            self.detect_materialized_subarray_serialization,
            self.detect_bitmask_subset_enumeration,
            self.detect_reduce_accumulator_copy,
            self.detect_java_stream_pipeline,
            self.detect_file_io_complexity,
            self.detect_implicit_iteration_complexity,
            self.detect_mutable_container_growth,
        ):
            detected = detector(code, language)
            if detected.get('detected') and detected.get('space'):
                detected_spaces.append(detected['space'])
        if detected_spaces:
            return self._max_complexity(detected_spaces)

        has_2d = bool(re.search(r'\[\s*\[|\[\s*\]\s*\*\s*n', code))
        has_dict = bool(re.search(r'\{\}|new\s+HashMap|new\s+Map\(\)|new\s+Set\s*\(|dict\(\)|set\(\)', code))
        has_array = bool(re.search(
            r'=\s*\[\]|new\s+Array|new\s+ArrayList|new\s+\w+\s*\[|Arrays\.copyOf|copyOf\s*\(|\.append\(',
            code, re.MULTILINE
        ))
        has_cpp_vector_alloc = any(
            re.search(r'\b(?:std::)?vector\s*<[^;{}()=]+>\s+\w+\s*(?:[;=({]|$)', line.strip())
            for line in code.split('\n')
        )
        if self._sorting_complexity(code) and re.search(r'\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\(', code):
            return self._sorting_space_complexity(code, language, has_array, has_dict, has_cpp_vector_alloc)

        recursion = self.analyze_recursion(code, language)
        has_recursion = bool(recursion['is_recursive'])
        has_dp = bool(re.search(r'dp\s*=\s*\[|memo\s*=\s*\{|cache\s*=', code))
        func_complexities = self._extract_all_function_complexities(code, language)
        materialized_complexity = self._materialized_generator_complexity(code, func_complexities)

        # Two-pointer / sliding window → O(1) if no auxiliary data structures
        if self._looks_like_two_pointers(code) and not has_array and not has_dict:
            return 'O(1)'
        if self._looks_like_sliding_window(code) and not has_2d:
            return 'O(n)' if (has_array or has_dict) else 'O(1)'

        if materialized_complexity:
            return materialized_complexity
        if has_recursion and recursion.get('type') == 'ackermann':
            return 'O(A(m, n))'
        if has_recursion and self._has_recursive_shrinking_substring_calls(recursion.get('func_name', ''), code):
            return 'O(n²)'
        if has_dp and has_2d: return 'O(n²)'
        if has_dp: return 'O(n)'
        if has_2d: return 'O(n²)'
        if has_recursion and recursion.get('type') == 'quasi_polynomial':
            return 'O(n)'
        if has_recursion and re.search(r'\/\s*2|>>\s*1|mid\s*=|Math\.floor\s*\(\s*\w+\s*\/\s*2', code):
            return 'O(n)' if has_array else 'O(log n)'
        if has_recursion: return 'O(n)'
        if has_array or has_dict or has_cpp_vector_alloc: return 'O(n)'
        return 'O(1)'

    def _materialized_generator_complexity(self, code, func_complexities):
        for func_name, complexity in func_complexities.items():
            materialized = re.search(rf'\[\s*\.\.\.\s*{func_name}\s*\(', code)
            if materialized and complexity in ('O(n^((log n + 1)/2))', 'O(n^log n)', 'O((log n)!)', 'O(2^n)', 'O(3^n)'):
                return complexity
        return None

    # ─────────────────────────────────────────────
    # ISSUE DETECTION
    # ─────────────────────────────────────────────

    def detect_issues(self, code, language):
        issues = []
        lines = code.split('\n')

        loops = self.extract_loop_tree(code, language)
        self._check_nested_loop_issues(loops, issues, lines)

        recursion = self.analyze_recursion(code, language)
        if recursion['is_recursive'] and recursion.get('type') in ('exponential', 'fibonacci_exponential'):
            issues.append({
                'line': self._find_recursive_func_line(code, lines),
                'type': 'performance', 'severity': 'high',
                'message': f'Exponential recursion ({recursion["complexity"]}) — add memoization or use dynamic programming'
            })

        regex = self.detect_catastrophic_regex(code)
        if regex['detected']:
            issues.append({
                'line': self._find_regex_line(lines),
                'type': 'performance', 'severity': 'high',
                'message': 'Catastrophic regex backtracking can cause O(2^n) time on adversarial input'
            })

        known = self.detect_known_algorithm(code)
        if known.get('detected') and known.get('can_optimize'):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'high',
                'message': f'{known["algorithm"]} detected ({known["complexity"]}) — can be optimized to {known.get("optimized_to", "better complexity")}'
            })

        graph = self.detect_graph_algorithm(code)
        if graph.get('detected') and graph.get('can_optimize'):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'medium',
                'message': f'{graph["algorithm"]} ({graph["complexity"]}) — {graph.get("note", "")}'
            })

        if self.detect_immutable_string_concat(code, language).get('detected'):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'high',
                'message': 'immutable string concatenation inside a loop repeatedly copies the growing string'
            })

        if self.detect_linear_front_insert(code, language).get('detected'):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'high',
                'message': 'Repeated front insertion shifts existing elements each time'
            })

        if self.detect_reduce_accumulator_copy(code, language).get('detected'):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'high',
                'message': 'reduce() copies the growing accumulator on every iteration'
            })

        java_stream = self.detect_java_stream_pipeline(code, language)
        if java_stream.get('detected') and java_stream.get('pattern') == 'java_nested_stream_pipeline':
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'high',
                'message': 'Nested Java Stream pipeline performs repeated inner scans'
            })

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_cpp_vector_string_memo_recursion(name, body, code):
                issues.append({
                    'line': 1, 'type': 'performance', 'severity': 'medium',
                    'message': 'C++ recursive vector copies and string memo keys can create quadratic average work and cubic collision-worst risk'
                })
            if self._looks_like_recursive_slice_partition(name, body):
                issues.append({
                    'line': 1, 'type': 'performance', 'severity': 'medium',
                    'message': 'Recursive slice/copy work allocates copied slices at each level'
                })
            if self._looks_like_memoized_recursive_slice_keys(name, body):
                issues.append({
                    'line': 1, 'type': 'memory', 'severity': 'medium',
                    'message': 'memo table stores serialized keys for sliced subarrays'
                })

        hash_access = self.detect_hash_table_access(code, language)
        if hash_access.get('detected') and 'worst' in hash_access.get('complexity', ''):
            issues.insert(0, {
                'line': 1, 'type': 'performance', 'severity': 'medium',
                'message': 'crafted/adversarial hash keys can trigger collision-heavy worst-case behavior'
            })
        elif hash_access.get('detected') and re.search(r'\*\s*16|cluster', code, re.IGNORECASE):
            issues.append({
                'line': 1, 'type': 'performance', 'severity': 'low',
                'message': 'power-of-two key patterns can cause hash bucket clustering'
            })

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.search(r'==\s*\d{3,}|>=\s*\d{3,}|<=\s*\d{3,}', stripped):
                issues.append({
                    'line': i, 'type': 'maintainability', 'severity': 'low',
                    'message': f'Magic number at line {i} — use a named constant instead'
                })
            if stripped.startswith('global '):
                issues.append({
                    'line': i, 'type': 'design', 'severity': 'medium',
                    'message': f'Global variable at line {i} — pass as parameter instead'
                })

        return issues

    def _check_nested_loop_issues(self, loops, issues, lines, depth=0):
        if depth == 0:
            code = '\n'.join(lines)
            if self._looks_like_dynamic_array_doubling(code):
                return
            if self._looks_like_naive_matrix_multiplication(code):
                first_loop = next((lp for lp in loops if lp.get('children')), loops[0] if loops else {'header': ''})
                issues.append({
                    'line': self._find_loop_line(first_loop['header'], lines),
                    'type': 'performance', 'severity': 'medium',
                    'message': (
                        'Naive matrix multiplication core — three nested loops cost O(k³). '
                        'This is expected for the basic algorithm; for large matrices use NumPy/BLAS, blocking, or Strassen where appropriate.'
                    )
                })
                return
        for loop in loops:
            if loop['children']:
                linear_children = [c for c in loop['children'] if c['type'] == 'linear']
                if loop['type'] == 'linear' and linear_children:
                    issues.append({
                        'line': self._find_loop_line(loop['header'], lines),
                        'type': 'performance', 'severity': 'high',
                        'message': (
                            'Nested linear loops — causes O(n²) or worse. '
                            'The right optimization depends on the operation: hashing, sorting/two pointers, '
                            'prefix sums, pruning, or DP may apply.'
                        )
                    })
                    continue
                self._check_nested_loop_issues(loop['children'], issues, lines, depth + 1)

    def _find_loop_line(self, header, lines):
        for i, line in enumerate(lines, 1):
            if header[:20] in line:
                return i
        return 1

    def _find_recursive_func_line(self, code, lines):
        for i, line in enumerate(lines, 1):
            if re.search(self._function_def_regex(), line.strip()):
                return i
        return 1

    def _find_regex_line(self, lines):
        for i, line in enumerate(lines, 1):
            if re.search(r'/.+/[gimsuy]*|RegExp\s*\(|re\.compile\s*\(', line):
                return i
        return 1

    # ─────────────────────────────────────────────
    # OPTIMIZATIONS
    # ─────────────────────────────────────────────

    def generate_optimizations(self, code, language, time_result):
        optimizations = []
        complexity = time_result['complexity']
        recursion = time_result.get('recursion')
        graph = time_result.get('graph')
        known = time_result.get('known')

        if self.detect_immutable_string_concat(code, language).get('detected'):
            return [{
                'title': 'Build string with a buffer',
                'problem': 'Immutable string concatenation copies the growing prefix each iteration.',
                'solution': 'Append parts to a list/array and join once.',
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'example': 'parts = []\nfor item in items:\n    parts.append(str(item))\nresult = "".join(parts)'
            }]

        if self.detect_linear_front_insert(code, language).get('detected'):
            return [{
                'title': 'Avoid repeated front insertion',
                'problem': 'Front insertion shifts existing elements on every iteration.',
                'solution': 'Append at the end, then reverse if front order is required.',
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'example': 'items.append(value)\n# reverse once at the end if needed'
            }]

        nested_keys = self.detect_nested_key_count(code, language)
        if nested_keys.get('detected'):
            return [{
                'title': 'Count key pairs directly',
                'problem': 'Nested key loops count every pair of keys.',
                'solution': 'Count keys once and multiply.',
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'example': 'const keyCount = Object.keys(obj).length;\nreturn keyCount * keyCount;'
            }]

        ordered_map = self.detect_ordered_map_access(code, language)
        if ordered_map.get('detected'):
            return [{
                'title': 'Use hash map when ordering is unnecessary',
                'problem': 'Ordered map access adds an O(log n) factor.',
                'solution': 'Use an unordered/hash map if sorted iteration is not required.',
                'complexity_before': ordered_map['complexity'],
                'complexity_after': self._quadratic() if ordered_map['complexity'] == self._tuple_to_string(('n2_log', 1)) else 'O(n)',
                'example': 'Use unordered_map / HashMap / Map for average O(1) updates.'
            }]

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_recursive_resort_merge(name, body):
                return [{
                    'title': 'Merge sorted halves without re-sorting',
                    'problem': 'sorted(left + right) sorts again at every merge level.',
                    'solution': 'Use a linear merge step.',
                    'complexity_before': self._tuple_to_string(('n_log2', 1)),
                    'complexity_after': 'O(n log n)',
                    'example': 'merge(left, right)  # linear merge instead of sorted(left + right)'
                }]
            if self._looks_like_recursive_slice_partition(name, body):
                return [{
                    'title': 'Pass index ranges instead of slicing',
                    'problem': 'Recursive slices copy subarrays at every level.',
                    'solution': 'Pass start/end indexes over the original array.',
                    'complexity_before': 'O(n log n)', 'complexity_after': 'O(n)',
                    'example': 'function solve(arr, lo, hi) { /* recurse on index ranges */ }'
                }]
            if self._looks_like_looped_halving_recursion(name, body):
                return [{
                    'title': 'Collapse repeated identical recursive calls',
                    'problem': 'The loop repeats the same halving recursive call n times.',
                    'solution': 'Call once and multiply by n.',
                    'complexity_before': 'O(n^((log n + 1)/2))', 'complexity_after': 'O(log n)',
                    'example': f'return n * {name}(n / 2);'
                }]

        if graph and graph.get('can_optimize'):
            optimizations.append({
                'title': f'Optimize {graph["algorithm"]} — {graph["complexity"]} → {graph.get("optimized_to", "better")}',
                'problem': f'Current algorithm: {graph["algorithm"]} runs at {graph["complexity"]}',
                'solution': graph.get('note', ''),
                'complexity_before': graph['complexity'],
                'complexity_after': graph.get('optimized_to', 'better'),
                'example': self._get_graph_optimization_example(graph, language)
            })

        if known and known.get('can_optimize') and 'Generator recursion' not in known.get('algorithm', ''):
            optimizations.append({
                'title': f'Replace {known["algorithm"]} — {known["complexity"]} → {known.get("optimized_to", "better")}',
                'problem': f'{known["algorithm"]} runs at {known["complexity"]}',
                'solution': known.get('note', ''),
                'complexity_before': known['complexity'],
                'complexity_after': known.get('optimized_to', 'better'),
                'example': self._get_known_algorithm_example(known, language)
            })

        if known and 'Generator recursion' in known.get('algorithm', ''):
            optimizations.append({
                'title': f'Replace {known["algorithm"]} — {known["complexity"]} → {known.get("optimized_to", "O(n)")}',
                'problem': 'Generator recursion recomputes overlapping subproblems exponentially',
                'solution': known.get('note', 'Use a memoized plain function.'),
                'complexity_before': known['complexity'],
                'complexity_after': known.get('optimized_to', 'O(n)'),
                'example': self._get_generator_memo_example(language)
            })

        if recursion and recursion.get('type') in ('exponential', 'fibonacci_exponential'):
            optimizations.append({
                'title': f'Add Memoization — {recursion["complexity"]} → O(n)',
                'problem': f'Exponential recursion with {recursion["branches"]} branches per call',
                'solution': 'Cache results of subproblems to avoid recomputation',
                'complexity_before': recursion['complexity'],
                'complexity_after': 'O(n) or O(n × target)',
                'example': self._get_memo_example(code, recursion, language)
            })

        if complexity == 'O(n²)' and not graph and not known and self._hashmap_optimization_applicable(code):
            optimizations.append({
                'title': 'Replace Nested Loops with Hash Map — O(n²) → O(n)',
                'problem': 'Nested linear loops check every pair — quadratic time',
                'solution': 'Use a hash map to store and look up values in O(1)',
                'complexity_before': 'O(n²)', 'complexity_after': 'O(n)',
                'example': self._get_hashmap_example(language)
            })
        elif complexity == 'O(n²)' and not graph and not known:
            optimizations.append({
                'title': 'Review Nested Loops — O(n²) may be reducible',
                'problem': 'Nested linear loops perform pairwise or repeated work.',
                'solution': (
                    'Choose the optimization that matches the problem: '
                    'hashing for lookup, sorting/two-pointers for ordered pairs, '
                    'prefix sums for range queries, DP/memoization for repeated states.'
                ),
                'complexity_before': 'O(n²)', 'complexity_after': 'problem-dependent',
                'example': self._get_nested_loop_strategy_example(language)
            })

        if complexity == 'O(n³)' and not known:
            optimizations.append({
                'title': 'Reduce Triple Loops — O(n³) → O(n²)',
                'problem': 'Triple nested loops are extremely slow',
                'solution': 'Fix outer two loops, use hash set for third lookup',
                'complexity_before': 'O(n³)', 'complexity_after': 'O(n²)',
                'example': self._get_triple_loop_example(language)
            })

        return optimizations

    def _hashmap_optimization_applicable(self, code):
        compact = self._compact_ws(code)
        name_hint = bool(re.search(
            r'two.?sum|pair.?sum|contains.?duplicate|duplicate|frequency|complement|target',
            code, re.IGNORECASE
        ))
        pair_sum_shape = bool(re.search(
            r'\b\w+\s*\[[^\]]+\]\s*\+\s*\w+\s*\[[^\]]+\]\s*==\s*\w+|'
            r'\b\w+\s*==\s*\w+\s*\[[^\]]+\]\s*\+\s*\w+\s*\[[^\]]+\]', compact
        ))
        membership_scan = bool(re.search(r'if\s+.*(?:==|in|contains|includes|has)\s+.*:', code, re.IGNORECASE))
        has_nested_loop = len(re.findall(r'\b(?:for|while)\b', code)) >= 2
        return has_nested_loop and (name_hint or pair_sum_shape or membership_scan)

    def _get_graph_optimization_example(self, graph, language):
        if 'Repeated DFS' in graph['algorithm']:
            if language == 'python':
                return '''# Share one visited set across all starts:
def run_all_nodes(graph):
    visited = set()
    for node in graph:
        if node not in visited:
            dfs(graph, node, visited)
# Time: O(V+E), Space: O(V)'''
            if language == 'javascript':
                return '''// Share one visited set across all starts:
function runAllNodes(graph) {
    const visited = new Set();
    for (const node of graph.keys()) {
        if (!visited.has(node)) dfs(graph, node, visited);
    }
}
// Time: O(V+E), Space: O(V)'''
            return '// Reuse one visited set across the outer graph loop: O(V * (V+E)) -> O(V+E).'

        if 'Bellman-Ford' in graph['algorithm']:
            if language == 'python':
                return '''# Replace Bellman-Ford with Dijkstra (no negative weights):
import heapq

def dijkstra(graph, source):
    dist = {node: float('inf') for node in graph}
    dist[source] = 0
    pq = [(0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                heapq.heappush(pq, (dist[v], v))
    return dist
# Time: O((V+E) log V) vs Bellman-Ford O(V×E)'''
            else:
                return '''// Replace Bellman-Ford with Dijkstra:
function dijkstra(graph, source) {
    const dist = new Array(graph.length).fill(Infinity);
    dist[source] = 0;
    const pq = [[0, source]];
    while (pq.length) {
        pq.sort((a,b) => a[0]-b[0]);
        const [d, u] = pq.shift();
        if (d > dist[u]) continue;
        for (const [v, w] of graph[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                pq.push([dist[v], v]);
            }
        }
    }
    return dist;
}
// Time: O((V+E) log V) vs Bellman-Ford O(V×E)'''
        return '// Use a more efficient algorithm for this graph problem.'

    def _get_known_algorithm_example(self, known, language):
        if 'Generator recursion' in known.get('algorithm', ''):
            return self._get_generator_memo_example(language)
        if any(x in known.get('algorithm', '') for x in ['Bubble', 'Selection', 'Insertion']):
            if language == 'python':
                return '# Replace with built-in sort — O(n log n) Tim Sort:\narr.sort()\n# or: sorted_arr = sorted(arr)'
            elif language == 'javascript':
                return '// Replace with built-in sort — O(n log n):\narr.sort((a, b) => a - b);'
            elif language == 'java':
                return '// Replace with Arrays.sort — O(n log n):\nArrays.sort(arr);\nCollections.sort(list);'
        if 'LIS' in known.get('algorithm', '') and 'DP' in known.get('algorithm', ''):
            if language == 'python':
                return '''# O(n²) DP → O(n log n) with patience sorting:
import bisect

def lis_length(nums):
    tails = []
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)
# Time: O(n²) → O(n log n)'''
        return '// Use a more efficient algorithm.'

    def _get_generator_memo_example(self, language):
        return '''// O(2^n) -> O(n) with memoization:
function genMemo(n, memo = new Map()) {
    if (n <= 1) return 1;
    if (memo.has(n)) return memo.get(n);
    const result = genMemo(n - 1, memo) + genMemo(Math.floor(n / 2), memo);
    memo.set(n, result);
    return result;
}'''

    def _get_memo_example(self, code, recursion, language):
        name = recursion.get('func_name', 'func')
        if language == 'python':
            return f'''from functools import lru_cache

@lru_cache(maxsize=None)
def {name}(arr, target, index=0):
    if target == 0: return True
    if index >= len(arr): return False
    include = {name}(arr, target - arr[index], index + 1)
    exclude = {name}(arr, target, index + 1)
    return include or exclude

# Note: Convert list to tuple: {name}(tuple(arr), target)
# Complexity: {recursion["complexity"]} → O(n × target)'''
        elif language == 'javascript':
            return f'''function {name}(arr, target, index = 0, memo = {{}}) {{
    const key = `${{index}}-${{target}}`;
    if (key in memo) return memo[key];
    if (target === 0) return true;
    if (index >= arr.length) return false;
    memo[key] = {name}(arr, target - arr[index], index + 1, memo) ||
                {name}(arr, target, index + 1, memo);
    return memo[key];
}}
// Complexity: {recursion["complexity"]} → O(n × target)'''
        return '// Add memoization to cache subproblem results.'

    def _get_hashmap_example(self, language):
        if language == 'python':
            return '''# Use O(n) hash map instead of O(n²) nested loops:
def twoSum(arr, target):
    seen = {}
    for i, num in enumerate(arr):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
# Time: O(n²) → O(n)'''
        elif language == 'javascript':
            return '''// Use O(n) hash map instead of O(n²) nested loops:
function twoSum(arr, target) {
    const seen = new Map();
    for (let i = 0; i < arr.length; i++) {
        const complement = target - arr[i];
        if (seen.has(complement))
            return [seen.get(complement), i];
        seen.set(arr[i], i);
    }
}
// Time: O(n²) → O(n)'''
        elif language == 'java':
            return '''// Use HashMap instead of nested loops:
public int[] twoSum(int[] arr, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < arr.length; i++) {
        int complement = target - arr[i];
        if (seen.containsKey(complement))
            return new int[]{seen.get(complement), i};
        seen.put(arr[i], i);
    }
    return new int[]{};
}
// Time: O(n²) → O(n)'''
        return '// Use a hash map for O(1) lookups instead of nested loops.'

    def _get_nested_loop_strategy_example(self, language):
        if language == 'python':
            return '''# Nested loops — choose the right optimization:
# - lookup / two-sum: use dict or set → O(n)
# - sorted pair search: sort + two pointers → O(n log n)
# - range sums: prefix sums → O(n)
# - repeated states: memoization / DP
# - all-pairs output required: O(n²) may be unavoidable'''
        if language == 'javascript':
            return '''// Nested loops — choose the right optimization:
// - lookup / two-sum: Map or Set → O(n)
// - sorted pair search: sort + two pointers → O(n log n)
// - range sums: prefix sums → O(n)
// - repeated states: memoization / DP
// - all-pairs output required: O(n²) may be unavoidable'''
        return '// Nested-loop optimization is problem-specific: hashing, two pointers, prefix sums, DP, or no safe reduction.'

    def _get_triple_loop_example(self, language):
        if language == 'python':
            return '''# Use O(n²) with hash set instead of O(n³):
def threeSum(arr, target):
    results = set()
    for i in range(len(arr)):
        seen = set()
        for j in range(i+1, len(arr)):
            complement = target - arr[i] - arr[j]
            if complement in seen:
                results.add(tuple(sorted([arr[i], complement, arr[j]])))
            seen.add(arr[j])
    return list(results)
# Time: O(n³) → O(n²)'''
        return '// Fix two outer loops and use hash set for third lookup.'

    # ─────────────────────────────────────────────
    # TRANSFORMED CODE
    # ─────────────────────────────────────────────

    def generate_transformed_code(self, code, language, time_result):
        complexity = time_result['complexity']
        recursion = time_result.get('recursion')
        known = time_result.get('known')
        graph = time_result.get('graph')

        if self.detect_immutable_string_concat(code, language).get('detected'):
            return {
                'available': True,
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'description': 'Use a buffer and join once',
                'code': 'parts = []\nfor item in items:\n    parts.append(str(item))\nresult = "".join(parts)'
            }

        if self.detect_linear_front_insert(code, language).get('detected'):
            return {
                'available': True,
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'description': 'Append at the end and reverse once if needed',
                'code': 'items.append(value)\n# reverse once at the end if front order is required'
            }

        if self.detect_nested_key_count(code, language).get('detected'):
            return {
                'available': True,
                'complexity_before': self._quadratic(), 'complexity_after': 'O(n)',
                'description': 'Count object keys once, then multiply',
                'code': 'let keyCount = 0;\nfor (const key in obj) keyCount++;\nreturn keyCount * keyCount;'
            }

        if self.detect_ordered_map_access(code, language).get('detected'):
            return {
                'available': True,
                'complexity_before': time_result['complexity'], 'complexity_after': 'O(n)',
                'description': 'Use a hash map when sorted order is unnecessary',
                'code': '// Replace ordered map/tree map with an unordered/hash map for average O(1) updates.'
            }

        for name in self._function_names(code, language):
            body = self._extract_function_body(code, name, language)
            if self._looks_like_recursive_resort_merge(name, body):
                return {
                    'available': True,
                    'complexity_before': self._tuple_to_string(('n_log2', 1)),
                    'complexity_after': 'O(n log n)',
                    'description': 'Use a linear merge instead of sorting merged halves',
                    'code': 'return merge(left, right)  # linear merge, not sorted(left + right)'
                }
            if self._looks_like_recursive_slice_partition(name, body):
                return {
                    'available': True,
                    'complexity_before': 'O(n log n)', 'complexity_after': 'O(n)',
                    'description': 'Pass index ranges instead of copying slices',
                    'code': 'function solve(arr, lo, hi) {\n  // recurse over [lo, hi) without arr.slice(...)\n}'
                }
            if self._looks_like_looped_halving_recursion(name, body):
                return {
                    'available': True,
                    'complexity_before': 'O(n^((log n + 1)/2))', 'complexity_after': 'O(log n)',
                    'description': 'Replace repeated identical recursive calls with multiplication',
                    'code': f'return n * {name}(n / 2);'
                }

        already_optimal = [
            'O(1)', 'O(log n)', 'O(n)', 'O(n log n)',
            'O(α(n))', 'O(√n)', 'O(log log n)', 'O(log² n)', 'O(log³ n)',
        ]
        if complexity in already_optimal:
            if not (known and known.get('can_optimize')) and not (graph and graph.get('can_optimize')):
                return {
                    'available': False,
                    'reason': f'Your code is already at {complexity} — no transformation needed.',
                    'complexity_before': complexity, 'complexity_after': complexity, 'code': None
                }

        if known and 'Generator recursion' in known.get('algorithm', ''):
            return {
                'available': True,
                'complexity_before': known['complexity'],
                'complexity_after': known.get('optimized_to', 'O(n)'),
                'description': 'Replaced generator recursion with a memoized plain function',
                'code': self._get_generator_memo_example(language)
            }

        if recursion and recursion.get('type') in ('exponential', 'fibonacci_exponential'):
            transformed = self._transform_recursive_to_memo(code, recursion, language)
            if transformed:
                return {
                    'available': True,
                    'complexity_before': recursion['complexity'],
                    'complexity_after': 'O(n × subproblems)',
                    'description': 'Added memoization to eliminate redundant recursive calls',
                    'code': transformed
                }

        if known and known.get('can_optimize') and known['algorithm'] in ['Bubble Sort', 'Selection Sort', 'Insertion Sort']:
            transformed = self._transform_sort_to_builtin(code, language)
            if transformed:
                return {
                    'available': True,
                    'complexity_before': known['complexity'], 'complexity_after': 'O(n log n)',
                    'description': f'Replaced {known["algorithm"]} with built-in O(n log n) sort',
                    'code': transformed
                }

        if known and known.get('can_optimize') and 'LIS' in known.get('algorithm', '') and 'DP' in known.get('algorithm', ''):
            if language == 'python':
                return {
                    'available': True,
                    'complexity_before': 'O(n²)', 'complexity_after': 'O(n log n)',
                    'description': 'Replaced quadratic LIS DP with patience sorting (O(n log n))',
                    'code': '''import bisect

def lis_length(nums):
    """Longest Increasing Subsequence in O(n log n)."""
    tails = []
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)
# Complexity: O(n²) → O(n log n)'''
                }

        if graph and graph.get('can_optimize') and 'Bellman' in graph.get('algorithm', ''):
            return {
                'available': True,
                'complexity_before': graph['complexity'], 'complexity_after': 'O((V+E) log V)',
                'description': 'Replace Bellman-Ford with Dijkstra for non-negative weights',
                'code': self._get_dijkstra_template(language)
            }

        if graph and graph.get('can_optimize') and 'Repeated DFS' in graph.get('algorithm', ''):
            return {
                'available': True,
                'complexity_before': graph['complexity'], 'complexity_after': 'O(V + E)',
                'description': 'Reuse one visited set instead of restarting DFS with a fresh set for every node',
                'code': self._get_graph_optimization_example(graph, language)
            }

        return {
            'available': False,
            'reason': 'Automatic transformation not available for this pattern. See optimizations above for manual guidance.',
            'complexity_before': complexity, 'complexity_after': 'varies', 'code': None
        }

    def _transform_recursive_to_memo(self, code, recursion, language):
        func_name = recursion.get('func_name', '')
        if not func_name:
            return None

        if language == 'python':
            lines = code.split('\n')
            new_lines = []
            added_import = False
            for line in lines:
                if not added_import and (line.strip().startswith('def ') or line.strip().startswith('import') or line.strip().startswith('from')):
                    if 'lru_cache' not in code:
                        new_lines.append('from functools import lru_cache')
                        new_lines.append('')
                    added_import = True
                if re.match(rf'\s*def\s+{func_name}\s*\(', line):
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + '@lru_cache(maxsize=None)')
                new_lines.append(line)
            new_lines.append('')
            new_lines.append(f'# NOTE: Convert list arguments to tuple when calling:')
            new_lines.append(f'# {func_name}(tuple(arr), target)')
            new_lines.append(f'# Complexity: {recursion["complexity"]} → O(n × subproblems)')
            return '\n'.join(new_lines)

        elif language == 'javascript':
            lines = code.split('\n')
            new_lines = []
            func_found = False
            for i, line in enumerate(lines):
                if re.match(rf'\s*function\s+{func_name}\s*\(', line) and not func_found:
                    func_found = True
                    modified = re.sub(
                        rf'(function\s+{func_name}\s*\()([^)]*)\)',
                        lambda m: m.group(1) + (m.group(2).rstrip() + (', ' if m.group(2).strip() else '') + 'memo = {}') + ')',
                        line
                    )
                    new_lines.append(modified)
                    new_lines.append('  const _key = JSON.stringify(Array.from(arguments).slice(0, -1));')
                    new_lines.append('  if (_key in memo) return memo[_key];')
                    continue
                if func_found and re.search(r'\breturn\b', line):
                    indent = len(line) - len(line.lstrip())
                    ret_val = re.search(r'return\s+(.+);', line)
                    if ret_val:
                        new_lines.append(' ' * indent + f'const _result = {ret_val.group(1)};')
                        new_lines.append(' ' * indent + 'memo[_key] = _result;')
                        new_lines.append(' ' * indent + 'return _result;')
                        continue
                new_lines.append(line)
            new_lines.append(f'// Complexity: {recursion["complexity"]} → O(n × subproblems)')
            return '\n'.join(new_lines)

        return None

    def _transform_sort_to_builtin(self, code, language):
        if language == 'python':
            return '''# Optimized using built-in Timsort — O(n log n):
def sort_array(arr):
    return sorted(arr)

def sort_array_inplace(arr):
    arr.sort()
    return arr
# Original: O(n²) → New: O(n log n)'''
        elif language == 'javascript':
            return '''// Optimized using built-in sort — O(n log n):
function sortArray(arr) {
    return [...arr].sort((a, b) => a - b);
}
// Original: O(n²) → New: O(n log n)'''
        elif language == 'java':
            return '''// Optimized using Arrays.sort — O(n log n):
import java.util.Arrays;
public static int[] sortArray(int[] arr) {
    int[] copy = Arrays.copyOf(arr, arr.length);
    Arrays.sort(copy);
    return copy;
}
// Original: O(n²) → New: O(n log n)'''
        return None

    def _get_dijkstra_template(self, language):
        if language == 'python':
            return '''import heapq

def dijkstra(graph, source):
    """graph: {node: [(neighbor, weight), ...]}"""
    dist = {node: float('inf') for node in graph}
    dist[source] = 0
    pq = [(0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, weight in graph[u]:
            if dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                heapq.heappush(pq, (dist[v], v))
    return dist
# Time: O((V+E) log V) vs Bellman-Ford O(V×E)'''
        elif language == 'java':
            return '''import java.util.*;
public static int[] dijkstra(List<List<int[]>> graph, int source) {
    int n = graph.size();
    int[] dist = new int[n];
    Arrays.fill(dist, Integer.MAX_VALUE);
    dist[source] = 0;
    PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(a -> a[1]));
    pq.offer(new int[]{source, 0});
    while (!pq.isEmpty()) {
        int[] curr = pq.poll();
        int node = curr[0], d = curr[1];
        if (d > dist[node]) continue;
        for (int[] edge : graph.get(node)) {
            if (dist[node] + edge[1] < dist[edge[0]]) {
                dist[edge[0]] = dist[node] + edge[1];
                pq.offer(new int[]{edge[0], dist[edge[0]]});
            }
        }
    }
    return dist;
}
// Time: O((V+E) log V)'''
        return '// Replace with Dijkstra algorithm for better performance.'

    # ─────────────────────────────────────────────
    # SUGGESTIONS
    # ─────────────────────────────────────────────

    def generate_suggestions(self, result):
        suggestions = []
        tc = result['time_complexity']
        sc = result['space_complexity']
        optimizations = result['optimizations']
        transformed = result.get('transformed_code', {})

        complexity_messages = {
            'O(1)':             '✅ Excellent! Constant time — as efficient as possible.',
            'O(α(n))':          '✅ Excellent! Inverse-Ackermann amortized — practically O(1) for all realistic n.',
            'O(log log n)':     '✅ Excellent! Log-log time — virtually constant for any real-world input.',
            'O(log log U)':     '✅ Excellent! Van Emde Boas log-log time — faster than any polynomial.',
            'O(log n)':         '✅ Great! Logarithmic time — scales very well.',
            'O(log n) amortized': '✅ Great! Amortized logarithmic time — excellent for dynamic structures.',
            'O(log_t n)':       '✅ Great! Log base t — optimal for B-Tree operations.',
            'O(log³ n)':        '✅ Good! Polylogarithmic time — very scalable even with several nested logarithmic loops.',
            'O(√n)':            '✅ Good! Square-root time — efficient for n up to 10^12.',
            'O(n)':             '✅ Good! Linear time — efficient for most use cases.',
            'O(n log log n)':   '✅ Near-linear — optimal for sieve-class algorithms.',
            'O(n log n)':       '✅ Good! Optimal for comparison-based sorting and many divide-and-conquer algorithms.',
            'O(n log n) worst, O(n) best': '✅ Good! Tim Sort — adaptive, O(n) on nearly-sorted data.',
            'O(n log² n)':      '⚠️  Fair. Slightly above linearithmic — acceptable for most cases.',
            'O(n^1.585)':       '✅ Karatsuba — subquadratic integer multiplication.',
            'O(n²)':            '⚠️  Warning! Quadratic — slow for large inputs (n > 10,000). Consider optimizing.',
            'O(n^2.807)':       '⚠️  Strassen — better than O(n³) but still heavy. Impractical for small matrices.',
            'O(n³)':            '🔴 Critical! Cubic — extremely slow for n > 1,000. Optimize urgently.',
            'O(n² log n)':      '🔴 Heavy. Quadratic work repeated across logarithmic steps.',
            'O(n³ log n)':      '🔴 Critical! Sorting repeated inside nested loops.',
            'O(φⁿ)':            '🔴 Critical! Fibonacci-exponential — add memoization immediately.',
            'O(2^n)':           '🔴 Critical! Exponential — times out for n > 30. Optimize immediately.',
            'O(2ⁿ)':            '🔴 Critical! Exponential — times out for n > 30. Optimize immediately.',
            'O(2^(n/2))':       '⚠️  Meet-in-middle exponential — much better than O(2^n) but still grows fast.',
            'O(3^n)':           '🔴 Critical! Exponential — times out for n > 20. Optimize immediately.',
            'O(3ⁿ)':            '🔴 Critical! Exponential — times out for n > 20. Optimize immediately.',
            'O(n!)':            '🔴 Critical! Factorial growth — only practical for n ≤ 12.',
            'O(n * n!)':        '🔴 Critical! Super-factorial — only practical for n ≤ 11.',
            'O(n * 2^n)':       '🔴 Critical! Exponential output growth — consider DP if searching, not enumerating.',
            'O((log n)!)':      '🔴 Critical! Quasi-polynomial — consider DP/memoisation.',
            'O(A(m, n))':       '🔴 Ackermann growth — only feasible for very small m, n.',
            'O((V + E) log V)': '✅ Optimal for graph shortest path with priority queue.',
            'O(V + E)':         '✅ Optimal graph traversal complexity.',
            'O(E log V)':       '✅ Optimal for heuristic-guided graph search.',
            'O(E√V)':           '✅ Optimal for bipartite matching (Hopcroft-Karp).',
            'O(V × E)':         '⚠️  Can be improved — consider Dijkstra if no negative weights.',
            'O(V * (V + E))':   '⚠️  Repeated graph traversal — a fresh visited set makes DFS repeat from every start node.',
            'O(V³)':            '⚠️  Cubic graph complexity — use Dijkstra per vertex for sparse graphs.',
            'O(n log n) average, O(n²) worst': '⚠️  Worst case is O(n²) — use randomized pivot or Merge Sort.',
            'O(9^m)':           '🔴 Critical! Exponential Sudoku search — add constraint propagation to prune.',
            'O(1) amortized':   '✅ Excellent! Amortized constant time per operation.',
            'O(m)':             '✅ Linear in key length — optimal for trie operations.',
            'O(k)':             '✅ Linear in hash functions — optimal for Bloom filter.',
            'O(n + k)':         '✅ Excellent! Linear-time sort — optimal for bounded integer keys.',
            'O(n + m + z)':     '✅ Optimal for multi-pattern search with Aho-Corasick.',
            'O(n + m)':         '✅ Linear — optimal for string search (KMP/Z-algorithm).',
            'O(k³ log n)':      '✅ Matrix exponentiation — logarithmic in the exponent, with cubic k×k matrix multiplies.',
        }

        msg = complexity_messages.get(tc)
        if msg:
            suggestions.append(msg)
        elif tc:
            if any(x in tc for x in ['^n)', 'n!', '2^n', '3^n', 'ⁿ)', 'factorial', 'φⁿ']):
                suggestions.append(f'🔴 Critical! {tc} — exponential or worse. Optimize urgently.')
            elif re.fullmatch(r'O\(n\^0\.\d+\)', tc):
                suggestions.append(f'✅ Sublinear polynomial time {tc} — faster than linear growth.')
            elif re.fullmatch(r'O\(n\^1\.\d+\)', tc):
                suggestions.append(f'✅ Subquadratic time {tc} — better than O(n²), often from uneven divide-and-conquer.')
            elif any(x in tc for x in ['n²', 'n^2', 'n³', 'n^3']):
                suggestions.append(f'⚠️  Warning! {tc} — polynomial but heavy. Consider optimizing.')

        if sc == 'O(n²)':
            suggestions.append('⚠️  High memory O(n²) — try in-place algorithms or rolling arrays.')
        elif sc in ('O(1)', 'O(α(n))'):
            suggestions.append('✅ Constant space — memory usage is optimal.')
        elif sc == 'O(log n)':
            suggestions.append('✅ Logarithmic space — excellent (typically recursion stack only).')

        if optimizations:
            suggestions.append(
                f'💡 {len(optimizations)} optimization(s) available — check the Optimizations section for code examples.'
            )

        if transformed and transformed.get('available'):
            suggestions.append(
                f'🔄 Optimized code available — complexity reduced from {transformed["complexity_before"]} to {transformed["complexity_after"]}. See Transformed Code section.'
            )

        if not suggestions:
            suggestions.append('✅ No major issues found. Your code looks clean and efficient.')

        return suggestions

    # ─────────────────────────────────────────────
    # RATING
    # ─────────────────────────────────────────────

    def calculate_rating(self, result):
        score = 10
        deductions = {
            'O(1)': 0, 'O(α(n))': 0, 'O(1) amortized': 0,
            'O(log log n)': 0, 'O(log log U)': 0,
            'O(log n)': 0.5,
            'O(log n) amortized': 0.5,
            'O(log log n)': 0,
            'O(log³ n)': 0.7,
            'O(√n)': 1,
            'O(n)': 1, 'O(n log log n)': 1.5,
            'O(n log n)': 2, 'O(n log n) worst, O(n) best': 2,
            'O(n log² n)': 2.5,
            'O(n^1.585)': 3,
            'O(n^2.807)': 3.5,
            'O(n²)': 4, 'O(n² log n)': 5, 'O(n³)': 7,
            'O(φⁿ)': 7.5,
            'O(2ⁿ)': 8, 'O(2^n)': 8, 'O(2^(n/2))': 5,
            'O(n * 2^n)': 8.5, 'O(3ⁿ)': 9, 'O(3^n)': 9,
            'O(n!)': 9, 'O(n * n!)': 9.5, 'O(A(m, n))': 10,
            'O((V + E) log V)': 1, 'O(V + E)': 0,
            'O(E log V)': 1, 'O(E√V)': 3,
            'O(V × E)': 4, 'O(V * (V + E))': 5, 'O(V³)': 6, 'O(V²E)': 7,
            'O(n log n) average, O(n²) worst': 3,
            'O(9^m)': 8,
            'O(1) amortized': 0, 'O(α(n))': 0,
            'O(m)': 0, 'O(k)': 0,
            'O(n + k)': 1, 'O(n + m)': 1, 'O(n + m + z)': 1,
            'O(iterations × n)': 3,
            'O(epochs × n × L × w)': 4,
            'O(k³)': 7,
            'O(n × W)': 4, 'O(n² × m)': 7,
            'O(n × d²)': 4,
            'O(k × n log n × d)': 2,
            'O(n log n × d)': 2,
            'O(k³ log n)': 4,
        }
        score -= deductions.get(result['time_complexity'], 2)
        fractional = re.fullmatch(r'O\(n\^([0-9]+(?:\.[0-9]+)?)\)', result['time_complexity'])
        if result['time_complexity'] not in deductions and fractional:
            score += 2
            exponent = float(fractional.group(1))
            score -= min(6, max(0.5, exponent * 2))
        if result['space_complexity'] == 'O(n²)': score -= 2
        elif result['space_complexity'] == 'O(n)': score -= 0.5

        for issue in result['issues']:
            if issue['severity'] == 'high': score -= 1.5
            elif issue['severity'] == 'medium': score -= 0.5
            elif issue['severity'] == 'low': score -= 0.2

        return max(1, round(score))

    # ─────────────────────────────────────────────
    # AMORTIZED ANALYSIS
    # ─────────────────────────────────────────────

    def explain_amortized_complexity(self, code, language):
        """
        Detects dynamic-array doubling, union-find, splay tree, and
        monotonic-stack patterns and explains their amortized cost.
        Returns an amortized analysis dict or None.
        """
        # Dynamic array doubling
        doubling = self._looks_like_dynamic_array_doubling(code) or bool(re.search(
            r'capacity\s*\*=\s*2|capacity\s*=\s*capacity\s*\*\s*2|'
            r'new_cap\s*=\s*\w+\s*\*\s*2|reserve.*\*\s*2|'
            r'if\s+len\s*\(\s*\w+\s*\)\s*==\s*capacity',
            code, re.IGNORECASE
        ))
        if doubling:
            return {
                'detected': True,
                'pattern': 'dynamic_array_doubling',
                'per_operation_worst': 'O(n)',
                'amortized_per_operation': 'O(1)',
                'total_for_n_ops': 'O(n)',
                'reason': (
                    'Doubling strategy: starting from capacity 1, resizing at 1,2,4,8,…,n '
                    'costs 1+2+4+…+n = O(2n) = O(n) total copy work across n appends. '
                    'Amortized cost per append = O(n)/n = O(1).'
                ),
                'note': 'Pre-reserve final capacity with reserve(n) if known to eliminate all resizes.'
            }

        hash_access = self.detect_hash_table_access(code, language)
        if hash_access.get('detected'):
            worst_total = hash_access.get('collision_worst_total')
            if not worst_total:
                worst_total = self._quadratic() if 'worst' in hash_access.get('complexity', '') else 'O(n)'
            return {
                'detected': True,
                'pattern': 'hash_table_access',
                'per_operation_worst': hash_access.get(
                    'per_operation_worst',
                    'O(n)' if worst_total != 'O(n)' else 'O(1)'
                ),
                'amortized_per_operation': 'O(1)',
                'total_for_n_ops': 'O(n)',
                'worst_total_for_n_ops': worst_total,
                'reason': hash_access.get('reason', 'Hash table operations are O(1) average/amortized.'),
                'note': 'Use robust hashing and avoid adversarial key distributions for worst-case safety.'
            }

        # Union-Find / DSU with path compression
        union_find = self._looks_like_union_find(code) or bool(re.search(
            r'path.?compress|find_parent|find_root|union.?by.?rank|union.?by.?size',
            code, re.IGNORECASE
        ))
        if union_find:
            return {
                'detected': True,
                'pattern': 'union_find_path_compression',
                'per_operation_worst': 'O(log n)',
                'amortized_per_operation': 'O(α(n))',
                'total_for_n_ops': 'O(n α(n))',
                'reason': (
                    'Path compression + union by rank/size gives amortized O(α(n)) per operation '
                    'where α is the inverse Ackermann function — effectively O(1) for all practical n.'
                ),
                'note': 'α(n) ≤ 4 for n < 10^600. Already optimal — no further improvement possible.'
            }

        # Monotonic stack
        mono_stack = bool(re.search(
            r'while\s+stack\s+and|while\s*\(?\s*!?\s*(?:stack|mono)\s*\.isEmpty',
            code, re.IGNORECASE
        ))
        if mono_stack:
            return {
                'detected': True,
                'pattern': 'monotonic_stack',
                'per_operation_worst': 'O(n)',
                'amortized_per_operation': 'O(1)',
                'total_for_n_ops': 'O(n)',
                'reason': (
                    'Each element is pushed onto the stack at most once and popped at most once '
                    'across the entire traversal — O(2n) total push+pop operations = O(n) amortized.'
                ),
                'note': 'Already optimal for next-greater-element, histogram, and span problems.'
            }

        # Splay tree / self-adjusting structure
        splay = bool(re.search(r'splay\s*\(|zig.?zig|zig.?zag', code, re.IGNORECASE))
        if splay:
            return {
                'detected': True,
                'pattern': 'splay_tree',
                'per_operation_worst': 'O(n)',
                'amortized_per_operation': 'O(log n)',
                'total_for_n_ops': 'O(n log n)',
                'reason': (
                    'Splay trees use the access lemma: each splay brings the accessed node to root. '
                    'Potential function argument shows amortized O(log n) per access over any sequence.'
                ),
                'note': 'O(log n) amortized, O(n) worst-case per op. Good cache locality for non-uniform access.'
            }

        return None

    # ─────────────────────────────────────────────
    # BITWISE COMPLEXITY CLASSIFIER
    # ─────────────────────────────────────────────

    def classify_bitwise_loop(self, code):
        """
        Identifies the complexity of common bitwise loop idioms.
        Returns a dict with complexity and explanation, or None.
        """
        if re.search(r'\bn\s*&\s*\(\s*n\s*-\s*1\s*\)|\bx\s*&=\s*\(\s*x\s*-\s*1\s*\)', code):
            return {
                'pattern': 'clear_lowest_set_bit',
                'complexity': 'O(popcount(n))',
                'worst_case': 'O(log n)',
                'note': 'Iterates exactly popcount(n) times — each iteration clears one set bit.'
            }
        if re.search(r'while\s*\(?\s*\w+\s*>\s*0.*(?:>>=\s*1|>>\s*=\s*1|\w+\s*=\s*\w+\s*>>\s*1)', code):
            return {
                'pattern': 'right_shift_loop',
                'complexity': 'O(log n)',
                'note': 'Shifts right by 1 each step — iterates floor(log₂n)+1 times.'
            }
        if re.search(r'bit.?revers|reverse.?bits|swap.*bits', code, re.IGNORECASE):
            return {
                'pattern': 'bit_reversal',
                'complexity': 'O(log w)',
                'note': 'O(log w) where w is word size (constant 32 or 64) — effectively O(1).'
            }
        if re.search(r'n\s*\|\s*\(n\s*-\s*1\)', code):
            return {
                'pattern': 'set_lowest_zero_bit',
                'complexity': 'O(1)',
                'note': 'n | (n-1) sets all trailing zeros in one operation — O(1).'
            }
        if re.search(r'\bpopcount\s*\(|\b__builtin_popcount\s*\(', code):
            return {
                'pattern': 'hardware_popcount',
                'complexity': 'O(1)',
                'note': 'Hardware popcount instruction — single CPU cycle regardless of n.'
            }
        return None

    # ─────────────────────────────────────────────
    # COMPLEXITY CLASS DESCRIPTOR
    # ─────────────────────────────────────────────

    def describe_complexity_class(self, complexity_string):
        """
        Returns a human-readable description of a complexity class
        including typical algorithm examples and practical input size limits.
        """
        descriptions = {
            'O(1)':         {'class': 'Constant',           'practical_limit': 'Unlimited',   'examples': ['Array index lookup', 'Hash table get (avg)', 'Stack push/pop', 'Bloom filter query']},
            'O(α(n))':      {'class': 'Inverse-Ackermann',  'practical_limit': 'Unlimited',   'examples': ['Union-Find with path compression', 'DSU operations']},
            'O(log log n)': {'class': 'Log-Logarithmic',    'practical_limit': 'n ~ 10^30',   'examples': ['Van Emde Boas tree ops', 'Interpolation search (uniform data)']},
            'O(log n)':     {'class': 'Logarithmic',        'practical_limit': 'n ~ 10^15',   'examples': ['Binary search', 'AVL/Red-Black tree ops', 'Fast exponentiation', 'Heap push/pop']},
            'O(log² n)':    {'class': 'Polylogarithmic',    'practical_limit': 'n ~ 10^9',    'examples': ['Some skip list ops', '2D segment tree query', 'HLD query']},
            'O(log³ n)':    {'class': 'Polylogarithmic',    'practical_limit': 'n ~ 10^8',    'examples': ['Nested logarithmic loops', 'Some multi-level data-structure queries']},
            'O(√n)':        {'class': 'Square-root',        'practical_limit': 'n ~ 10^12',   'examples': ["Mo's algorithm", 'Sqrt decomposition', 'Trial division primality', "Hopcroft-Karp inner"]},
            'O(n)':         {'class': 'Linear',              'practical_limit': 'n ~ 10^8',    'examples': ['Linear scan', 'BFS/DFS', 'Counting sort', 'KMP', 'Z-Algorithm', 'Manacher']},
            'O(n log log n)':{'class': 'Near-linear',        'practical_limit': 'n ~ 5×10^7',  'examples': ['Sieve of Eratosthenes', 'Segmented sieve']},
            'O(n log n)':   {'class': 'Linearithmic',       'practical_limit': 'n ~ 10^6',    'examples': ['Merge sort', 'FFT', 'NTT', 'Heap sort', 'Convex hull Graham scan']},
            'O(n log² n)':  {'class': 'Super-linearithmic', 'practical_limit': 'n ~ 5×10^5',  'examples': ['HLD + segment tree', 'Some divide-and-conquer']},
            'O(n^1.585)':   {'class': 'Karatsuba',          'practical_limit': 'n ~ 10^5',    'examples': ['Karatsuba integer multiplication']},
            'O(n²)':        {'class': 'Quadratic',           'practical_limit': 'n ~ 10^4',    'examples': ['Bubble sort', 'Naive string matching', 'LIS DP', 'Floyd-Warshall (dense)']},
            'O(n^2.807)':   {'class': 'Strassen',            'practical_limit': 'n ~ 10^3',    'examples': ["Strassen matrix multiplication"]},
            'O(n³)':        {'class': 'Cubic',               'practical_limit': 'n ~ 500',     'examples': ['Gaussian elimination', 'Floyd-Warshall', 'Matrix chain DP', 'LU decomposition']},
            'O(n³ log n)':  {'class': 'Super-cubic',         'practical_limit': 'n ~ 200',     'examples': ['Sorting inside triple-nested loops']},
            'O(2^(n/2))':   {'class': 'Meet-in-middle exp.', 'practical_limit': 'n ~ 50',     'examples': ['Meet-in-the-middle subset sum', 'Baby-step giant-step']},
            'O(φⁿ)':        {'class': 'Fibonacci-exponential','practical_limit': 'n ~ 35',    'examples': ['Naive Fibonacci T(n)=T(n-1)+T(n-2)', 'Fibonacci number without memo']},
            'O(2^n)':       {'class': 'Exponential',         'practical_limit': 'n ~ 30',     'examples': ['Subset enumeration', 'Naive Fibonacci', 'TSP brute force', 'Bitmask DP']},
            'O(n * 2^n)':   {'class': 'Exp × linear',        'practical_limit': 'n ~ 25',     'examples': ['Printing all subsets with their contents', 'Held-Karp TSP']},
            'O(3^n)':       {'class': 'Tripling exponential', 'practical_limit': 'n ~ 20',    'examples': ['Coloring with 3 colors', 'Some set-cover DP']},
            'O(n!)':        {'class': 'Factorial',            'practical_limit': 'n ~ 12',     'examples': ['Permutation generation', 'N-Queens brute force', 'Branch-and-bound TSP']},
            'O(n * n!)':    {'class': 'Super-Factorial',      'practical_limit': 'n ~ 11',     'examples': ['Generating all permutations with output', 'Permutation backtracking']},
            'O(A(m, n))':   {'class': 'Ackermann',            'practical_limit': 'n ~ 4',      'examples': ['Ackermann function itself', 'Some inverse-Ackermann problems']},
        }
        return descriptions.get(complexity_string, {
            'class': 'Unknown',
            'practical_limit': 'Unknown',
            'examples': ['Complexity class not catalogued — add it to describe_complexity_class()']
        })

    # ─────────────────────────────────────────────
    # MASTER THEOREM EXPLAINER (public API)
    # ─────────────────────────────────────────────

    def explain_master_theorem(self, a, b, f_complexity='O(1)'):
        """
        Public wrapper around MasterTheoremEngine.
        a = number of subproblems, b = divisor (shrink factor), f_complexity = work per level.
        Returns a full explanation dict.
        """
        ft, fp = self._body_work_to_ft_fp(f_complexity)
        result, case, reason = self.master_theorem.solve(a, b, ft, fp)
        import math
        return {
            'recurrence': f'T(n) = {a}T(n/{b}) + {f_complexity}',
            'log_b_a': round(math.log(a, b), 4) if a > 0 and b > 1 else 'N/A',
            'f_complexity': f_complexity,
            'theorem_case': case,
            'result': result,
            'reason': reason,
        }

    # ─────────────────────────────────────────────
    # RECURRENCE DETECTOR (explicit T(n) strings)
    # ─────────────────────────────────────────────

    def detect_recurrence_from_string(self, recurrence_str):
        """
        Parse a recurrence like 'T(n) = 3T(n/2) + O(n)' and return complexity.
        Useful for testing or educational explanations.
        """
        pattern = re.match(
            r'T\s*\(\s*n\s*\)\s*=\s*(\d+)\s*T\s*\(\s*n\s*/\s*(\d+)\s*\)'
            r'(?:\s*\+\s*(O\([^)]+\)))?',
            recurrence_str.strip(), re.IGNORECASE
        )
        if not pattern:
            return {'available': False, 'reason': 'Could not parse recurrence string. Expected format: T(n) = aT(n/b) + O(f)'}
        a = int(pattern.group(1))
        b = int(pattern.group(2))
        f = pattern.group(3) or 'O(1)'
        return {
            'available': True,
            'parsed': {'a': a, 'b': b, 'f': f},
            **self.explain_master_theorem(a, b, f)
        }

    # ─────────────────────────────────────────────
    # PROBABILISTIC / RANDOMIZED ANALYSIS
    # ─────────────────────────────────────────────

    def analyze_probabilistic_complexity(self, code):
        """
        Detects randomized algorithms and returns expected vs worst-case complexity.
        """
        results = []

        if re.search(r'random.*pivot|rand.*partition|randomized.*quick', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Randomized QuickSort',
                'expected': 'O(n log n)',
                'worst_case': 'O(n²)',
                'probability_of_worst': 'O(1/n!) — exponentially unlikely with random pivot',
                'note': 'Expected O(n log n) with high probability. Use Introsort for strict O(n log n) guarantee.'
            })

        if re.search(r'miller.?rabin|strong.*witness|fermat.*prime', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Miller-Rabin Primality Test',
                'expected': 'O(k log² n)',
                'worst_case': 'O(k log² n)',
                'error_probability': 'at most 4^(-k)',
                'note': 'k=40 gives error probability < 10^(-24). Deterministic for n < 3.3×10²⁴ with k=7 fixed witnesses.'
            })

        if re.search(r'bloom.?filter|bloomfilter', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Bloom Filter',
                'expected': 'O(k) per op',
                'worst_case': 'O(k) per op',
                'false_positive_rate': '(1 - e^(-kn/m))^k ≈ 0.6185^(m/n) with optimal k',
                'note': 'No false negatives. Optimal k = (m/n) ln 2.'
            })

        if re.search(r'skip.?list|skiplist', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Skip List',
                'expected': 'O(log n)',
                'worst_case': 'O(n)',
                'probability_of_worst': 'O(1/n^c) for constant c — with high probability O(log n)',
                'note': 'Expected O(log n) with O(n log n) space. Randomized but practically reliable.'
            })

        if re.search(r'treap|tree.*heap.*rand', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Treap',
                'expected': 'O(log n)',
                'worst_case': 'O(n)',
                'probability_of_worst': 'Exponentially small — random priorities give O(log n) w.h.p.',
                'note': 'O(log n) expected height. Much simpler than Red-Black Trees with same bounds.'
            })

        if re.search(r'monte.?carlo|random.*sample', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Monte Carlo Sampling',
                'expected': 'O(n)',
                'worst_case': 'O(n)',
                'accuracy': 'Error ε with probability δ requires n = O(log(1/δ) / ε²) samples (Chernoff)',
                'note': 'Always terminates in O(n). May produce wrong answer — increase samples for accuracy.'
            })

        if re.search(r'las.?vegas|always.?correct.*rand', code, re.IGNORECASE):
            results.append({
                'algorithm': 'Las Vegas Algorithm',
                'expected': 'O(expected)',
                'worst_case': 'Unbounded (but probability of long runs decays exponentially)',
                'note': 'Always correct. Expected runtime finite — geometric distribution of success per trial.'
            })

        return results if results else []

    # ─────────────────────────────────────────────
    # PARALLEL / CONCURRENT COMPLEXITY HINTS
    # ─────────────────────────────────────────────

    def detect_parallelism_hints(self, code):
        """
        Detects patterns that suggest parallelizable work and estimates
        potential parallel complexity (span / work model).
        """
        hints = []

        if re.search(r'map\s*\(|filter\s*\(|reduce\s*\(|\.map\s*\(|\.filter\s*\(', code):
            hints.append({
                'pattern': 'map/filter/reduce',
                'sequential': 'O(n)',
                'parallel_work': 'O(n)',
                'parallel_span': 'O(log n)',
                'speedup': 'O(n / log n) with n processors',
                'note': 'Embarrassingly parallel — trivially maps to GPU or SIMD.'
            })

        if re.search(r'merge.?sort|mergeSort', code, re.IGNORECASE):
            hints.append({
                'pattern': 'merge sort',
                'sequential': 'O(n log n)',
                'parallel_work': 'O(n log n)',
                'parallel_span': 'O(log² n)',
                'note': 'Parallel merge sort achieves O(log² n) span using Cole\'s algorithm.'
            })

        if re.search(r'prefix.?sum|prefix_sum|cumulative.?sum', code, re.IGNORECASE):
            hints.append({
                'pattern': 'prefix sum',
                'sequential': 'O(n)',
                'parallel_work': 'O(n)',
                'parallel_span': 'O(log n)',
                'note': 'Parallel prefix (scan) achieves O(log n) span with n processors — standard GPU primitive.'
            })

        if re.search(r'matrix.*mul|matmul|dot.*product', code, re.IGNORECASE):
            hints.append({
                'pattern': 'matrix multiplication',
                'sequential': 'O(n³)',
                'parallel_work': 'O(n³)',
                'parallel_span': 'O(log n)',
                'speedup': 'O(n³ / log n) with n³ processors',
                'note': 'Inner products are independent — highly parallelizable on GPU (cuBLAS).'
            })

        if re.search(r'for\s+.*\s+in\s+.*:\n.*\bsort\b|\bsorted\b', code, re.IGNORECASE | re.DOTALL):
            hints.append({
                'pattern': 'independent sorts',
                'note': 'Multiple independent sort calls can be parallelized — each on a separate thread.'
            })

        return hints

    # ─────────────────────────────────────────────
    # CACHE / MEMORY COMPLEXITY HINTS
    # ─────────────────────────────────────────────

    def detect_cache_complexity(self, code):
        """
        Detects cache-oblivious or cache-unfriendly patterns and
        estimates cache miss complexity (I/O model).
        """
        hints = []

        # Column-major access on row-major array (cache unfriendly in C/C++)
        col_major = bool(re.search(
            r'for\s+\w+\s+in\s+range.*:\s*\n\s*for\s+\w+\s+in\s+range.*:\s*\n\s*.*\[\s*\w+\s*\]\s*\[\s*\w+\s*\]',
            code, re.DOTALL
        )) or bool(re.search(r'arr\s*\[j\]\s*\[i\]|matrix\s*\[j\]\s*\[i\]', code))
        if col_major:
            hints.append({
                'pattern': 'column-major access on row-major array',
                'cache_misses': 'O(n²) — every access is a cache miss for large n',
                'fix': 'Transpose the loop order: iterate rows in outer loop, columns in inner loop.',
                'severity': 'high'
            })

        # Merge sort — cache-oblivious optimal
        if re.search(r'merge.?sort|mergeSort', code, re.IGNORECASE):
            hints.append({
                'pattern': 'merge sort',
                'cache_complexity': 'O((n/B) log_{M/B}(n/B)) I/Os',
                'note': 'Cache-oblivious optimal for sorting. B=block size, M=cache size.'
            })

        # Random access patterns (hash tables)
        if re.search(r'hash.*table|dict\[|map\[|\{\}', code, re.IGNORECASE):
            hints.append({
                'pattern': 'hash table random access',
                'cache_complexity': 'O(n) cache misses for n lookups (poor locality)',
                'note': 'Hash tables have poor cache locality. For sequential access, sorted arrays + binary search may be faster in practice.'
            })

        # Sequential array access (cache friendly)
        if re.search(r'for\s+\w+\s+in\s+range.*arr\[', code) or re.search(r'for\s*\(.*;\s*\w+\s*<\s*n.*arr\[', code):
            hints.append({
                'pattern': 'sequential array access',
                'cache_complexity': 'O(n/B) cache misses — optimal sequential scan',
                'note': 'Sequential access is cache-friendly — hardware prefetcher will predict next cache line.'
            })

        return hints

    # ─────────────────────────────────────────────
    # COMPREHENSIVE FULL ANALYSIS (extended API)
    # ─────────────────────────────────────────────

    def full_analysis(self, code, filename=None, concrete_inputs=None):
        """
        Runs all analyses and returns a unified report dict including
        standard analysis, Master Theorem, probabilistic hints,
        parallelism hints, and cache complexity hints.
        """
        base = self.analyze(code, filename, concrete_inputs)
        language = base.get('language', 'unknown')

        master_info = None
        recursion = self.analyze_recursion(code, language)
        if recursion.get('is_recursive'):
            body = self._extract_function_body(code, recursion.get('func_name', ''), language) or ''
            call_count = len(re.findall(rf'\b{recursion.get("func_name", "_")}\s*\(', body))
            has_halving = bool(re.search(r'\/\s*2|>>\s*1|Math\.floor\s*\(', body))
            if call_count >= 2 and has_halving:
                ft, fp = self._body_work_to_ft_fp(
                    self.compute_loop_complexity(self.extract_loop_tree(body, language)) or 'O(1)'
                )
                result, case, reason = self.master_theorem.solve(call_count, 2, ft, fp)
                master_info = {
                    'recurrence': f'T(n) = {call_count}T(n/2) + {self._tuple_to_string((ft, fp))}',
                    'theorem_case': case,
                    'result': result,
                    'reason': reason,
                }

        prob = self.analyze_probabilistic_complexity(code)
        parallel = self.detect_parallelism_hints(code)
        cache = self.detect_cache_complexity(code)
        bitwise = self.classify_bitwise_loop(code)
        complexity_class = self.describe_complexity_class(base['time_complexity'])

        return {
            **base,
            'master_theorem': master_info,
            'probabilistic_analysis': prob,
            'parallelism_hints': parallel,
            'cache_complexity_hints': cache,
            'bitwise_analysis': bitwise,
            'complexity_class_description': complexity_class,
        }
