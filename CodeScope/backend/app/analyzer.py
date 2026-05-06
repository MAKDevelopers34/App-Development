import ast
import re
from collections import defaultdict, deque


class CallGraphAnalyzer:
    """
    Tracks which functions call which other functions
    and chains their complexities together.
    """

    def __init__(self):
        self.call_graph = defaultdict(set)
        self.func_complexities = {}

    def build_call_graph(self, code, language):
        """
        Builds a map of function → set of functions it calls.
        Example: {'main': {'helper', 'sort'}, 'helper': {'search'}}
        """
        self.call_graph = defaultdict(set)
        lines = code.split('\n')
        current_func = None

        for line in lines:
            stripped = line.strip()

            # Detect function definition
            func_def = re.match(
                r'(?:def\s+|function\s*\*?\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:void|int|long|double|float|boolean|bool|char|String|List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+)(\w+)\s*\(',
                stripped
            )
            if func_def:
                current_func = func_def.group(1)
                self.call_graph[current_func]  # ensure it exists

            # Detect function calls inside current function
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
        """
        For a given function, finds the worst complexity
        in its entire call chain.
        """
        if visited is None:
            visited = set()

        if func_name in visited:
            return complexities.get(func_name, 'O(1)')

        visited.add(func_name)

        own = complexities.get(func_name, 'O(1)')
        worst = own

        for called_func in self.call_graph.get(func_name, set()):
            if called_func in complexities:
                child = self.compute_chained_complexity(
                    called_func, complexities, visited)
                worst = self._worse_of(worst, child)

        return worst

    def _worse_of(self, a, b):
        rank = {
            'O(1)': 0, 'O(log log n)': 0.5, 'O(log n)': 1, 'O(log² n)': 2,
            'O(n)': 3, 'O(n log n)': 4, 'O(n log² n)': 5,
            'O(n²)': 6, 'O(n² log n)': 7, 'O(n³)': 8,
            'O((log n)!)': 8.5,
            'O(2ⁿ)': 9, 'O(3ⁿ)': 10,
            'O((V + E) log V)': 4, 'O(V + E)': 3,
            'O(V × E)': 6, 'O(V³)': 8,
        }
        return a if rank.get(a, 3) >= rank.get(b, 3) else b

    def get_call_chain_report(self, code, func_complexities, language):
        """
        Returns a report of which functions affect overall complexity
        and through which call chain.
        """
        self.build_call_graph(code, language)
        report = []

        for func, calls in self.call_graph.items():
            if not calls:
                continue
            own = func_complexities.get(func, 'O(1)')
            chained = self.compute_chained_complexity(
                func, func_complexities)

            if chained != own:
                chain_path = self._find_chain_path(
                    func, func_complexities, chained)
                report.append({
                    'function': func,
                    'own_complexity': own,
                    'effective_complexity': chained,
                    'chain': chain_path,
                    'message': (
                        f"'{func}' has own complexity {own} but calls "
                        f"'{chain_path}' which is {chained} — "
                        f"effective complexity is {chained}"
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


class CodeAnalyzer:
    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'java', 'cpp', 'c']
        self.call_graph_analyzer = CallGraphAnalyzer()
        self.last_func_complexities = {}

    def _function_def_regex(self):
        return (
            r'(?:def\s+|function\s*\*?\s+|'
            r'(?:(?:public|private|protected)\s+)?(?:static\s+)?'
            r'(?:void|int|long|double|float|boolean|bool|char|String|'
            r'List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|'
            r'Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|'
            r'vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+)'
            r'(\w+)\s*\('
        )

    def detect_language(self, code, filename=None):
        if filename:
            ext = filename.split('.')[-1].lower()
            lang_map = {
                'py': 'python',
                'js': 'javascript',
                'java': 'java',
                'cpp': 'cpp',
                'c': 'c',
                'ts': 'javascript',
                'jsx': 'javascript',
                'tsx': 'javascript'
            }
            return lang_map.get(ext, 'unknown')
        return 'unknown'

    def analyze(self, code, filename=None, concrete_inputs=None):
        language = self.detect_language(code, filename)
        input_schema = self.infer_input_schema(code, language)
        self.last_func_complexities = self._extract_all_function_complexities(code, language)
        time_result = self.detect_time_complexity(code, language)
        if self.last_func_complexities:
            function_worst = self._max_complexity(self.last_func_complexities.values())
            current_rank = self._complexity_rank(
                self._parse_complexity_string(time_result['complexity'])
            )
            function_rank = self._complexity_rank(
                self._parse_complexity_string(function_worst)
            )
            if function_rank > current_rank:
                time_result = {
                    **time_result,
                    'complexity': function_worst,
                    'reason': f"{time_result['reason']} | Function/call-chain analysis: {function_worst}"
                }
        space = self.detect_space_complexity(code, language)
        issues = self.detect_issues(code, language)
        optimizations = self.generate_optimizations(code, language, time_result)
        transformed = self.generate_transformed_code(code, language, time_result)
        concrete = self.detect_concrete_analysis(code, language, concrete_inputs)

        result = {
            'language': language,
            'time_complexity': time_result['complexity'],
            'time_complexity_reason': time_result['reason'],
            'space_complexity': space,
            'issues': issues,
            'suggestions': [],
            'optimizations': optimizations,
            'transformed_code': transformed,
            'rating': 0,
            'lines_of_code': len(code.strip().split('\n')),
            'input_schema': input_schema,
        }
        if concrete_inputs:
            result['provided_inputs'] = concrete_inputs
        if concrete:
            result['concrete_analysis'] = concrete
        result['suggestions'] = self.generate_suggestions(result)
        result['rating'] = self.calculate_rating(result)
        return result

    def infer_input_schema(self, code, language=None):
        language = language or self.detect_language(code)
        signature = self._primary_function_signature(code, language)
        if not signature:
            return {
                'available': False,
                'language': language,
                'function': None,
                'parameters': [],
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

        if language == 'javascript':
            patterns = [
                r'function\s*\*?\s+(\w+)\s*\(([^)]*)\)',
                r'(?:const|let|var)\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>',
                r'(?:const|let|var)\s+(\w+)\s*=\s*([A-Za-z_]\w*)\s*=>',
            ]
            for pattern in patterns:
                match = re.search(pattern, code)
                if match:
                    raw_params = match.group(2)
                    return {
                        'name': match.group(1),
                        'params': self._parse_signature_params(raw_params, language)
                    }
            return None

        match = re.search(
            r'(?:public|private|protected)?\s*(?:static\s+)?'
            r'(?:[\w:<>\[\], ?&*]+\s+)'
            r'(\w+)\s*\(([^)]*)\)',
            code
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


    def _extract_all_function_complexities(self, code, language):
        """
        Extracts complexity for every individual function in the code.
        """
        complexities = {}
        func_pattern = self._function_def_regex()
        func_names = re.findall(func_pattern, code)

        for name in func_names:
            body = self._extract_function_body(code, name, language)
            if body:
                recursion_result = self._detect_body_recursion_complexity(
                    name, body)
                if recursion_result:
                    complexities[name] = recursion_result['complexity']
                else:
                    time_result = self.detect_time_complexity(body, language)
                    complexities[name] = time_result['complexity']

        for _ in range(max(1, len(complexities))):
            changed = False
            for name in func_names:
                body = self._extract_function_body(code, name, language)
                if not body:
                    continue
                call_complexities = self._called_function_complexities(
                    body, complexities, current_func=name)
                if not call_complexities:
                    continue
                combined = self._max_complexity(
                    [complexities.get(name, 'O(1)')] + call_complexities)
                if combined != complexities.get(name):
                    complexities[name] = combined
                    changed = True
            if not changed:
                break

        return complexities

    def _detect_body_recursion_complexity(self, func_name, body):
        call_count = len(re.findall(rf'\b{func_name}\s*\(', body))
        if call_count == 0:
            return None

        is_generator = bool(re.search(r'yield\s*\*', body))
        has_memo = bool(re.search(
            r'memo|cache|@lru_cache|@cache|memoize|dp\s*=\s*\{|dp\s*=\s*\[',
            body,
            re.IGNORECASE
        ))
        has_halving = bool(re.search(
            r'\/\s*2|>>\s*1|mid\s*=|Math\.floor\s*\(\s*\w+\s*\/\s*2',
            body
        ))
        has_ackermann = self._has_ackermann_recursion(func_name, body)
        has_decrement = self._has_recursive_decrement_call(func_name, body)
        has_balanced_partition = self._has_balanced_partition_recursion(func_name, body)
        has_shrinking_substring = self._has_recursive_shrinking_substring_calls(func_name, body)
        loop_complexity = self.compute_loop_complexity(
            self.extract_loop_tree(body, 'unknown'))
        recursive_multiplier = self._recursive_call_multiplier(func_name, body)
        body_work = loop_complexity or 'O(1)'

        if has_memo:
            return {
                'complexity': 'O(n)',
                'reason': 'Memoized recursion inside function body'
            }
        if has_ackermann:
            return {
                'complexity': 'O(A(m, n))',
                'reason': 'Ackermann-style nested recursion f(m - 1, f(m, n - 1))'
            }
        if recursive_multiplier == 'O(log n)' and has_halving:
            complexity = body_work if body_work != 'O(1)' else 'O(log² n)'
            return {
                'complexity': complexity,
                'reason': (
                    f'Log-loop of T(n/2) calls: T(n)=log(n)*T(n/2)+{body_work}. '
                    'The geometric series is dominated by the body work.'
                )
            }
        if recursive_multiplier == 'O(n)' and has_halving:
            return {
                'complexity': 'O(2^n)',
                'reason': 'Linear number of recursive half-size calls per level'
            }
        if call_count >= 2 and has_balanced_partition:
            complexity = self._divide_and_conquer_complexity(call_count, body_work)
            return {
                'complexity': complexity,
                'reason': f'Balanced partition recursion: T(n)={call_count}T(n/2)+{body_work}'
            }
        if call_count >= 2 and has_decrement and has_halving:
            return {
                'complexity': 'O(2^n)',
                'reason': (
                    'Mixed recurrence T(n)=T(n-1)+T(n/2): the T(n-1) branch '
                    'dominates and spawns exponentially many recursive calls'
                )
            }
        if is_generator and call_count == 2 and has_decrement and has_halving:
            return {
                'complexity': 'O(2^n)',
                'reason': 'Generator recursion T(n)=T(n-1)+T(n/2) is exponential'
            }
        if call_count >= 2 and has_shrinking_substring:
            return {
                'complexity': 'O(n * 2^n)',
                'reason': 'Branching recursion on length n-1 substrings gives T(n) = 2T(n-1) + O(n)'
            }
        if call_count == 1 and has_halving:
            complexity = self._max_complexity(['O(log n)', loop_complexity])
            return {
                'complexity': complexity,
                'reason': 'Single recursive call with halving plus body work'
            }
        if call_count == 1:
            complexity = self._max_complexity(['O(n)', loop_complexity])
            return {
                'complexity': complexity,
                'reason': 'Single recursive call per level plus body work'
            }
        if call_count == 2 and has_halving:
            complexity = self._divide_and_conquer_complexity(call_count, body_work)
            return {
                'complexity': complexity,
                'reason': f'Divide-and-conquer recurrence T(n) = 2T(n/2) + {body_work}'
            }
        if call_count > 2 and has_halving:
            complexity = self._divide_and_conquer_complexity(call_count, body_work)
            return {
                'complexity': complexity,
                'reason': f'Divide-and-conquer recurrence T(n) = {call_count}T(n/2) + {body_work}'
            }
        return {
            'complexity': f'O({call_count}^n)',
            'reason': f'{call_count} recursive calls per level'
        }

    def _has_ackermann_recursion(self, func_name, body):
        nested_call = re.search(
            rf'\b{func_name}\s*\([^;\n]*\b{func_name}\s*\(',
            body
        )
        if not nested_call:
            return False

        has_first_param_decrement = bool(re.search(
            rf'\b{func_name}\s*\(\s*\w+\s*-\s*1\s*,',
            body
        ))
        has_second_param_decrement = bool(re.search(
            rf'\b{func_name}\s*\(\s*\w+\s*,\s*\w+\s*-\s*1\s*\)',
            body
        ))
        return has_first_param_decrement and has_second_param_decrement

    def detect_concrete_analysis(self, code, language, concrete_inputs=None):
        dfs = self._find_dfs_function(code, language)
        if dfs:
            graph_inputs = self._parse_graph_concrete_inputs(concrete_inputs, dfs)
            if graph_inputs:
                return self._concrete_dfs_analysis(dfs, graph_inputs)

        bit_clear = self._find_bit_clear_function(code, language)
        if bit_clear:
            value = self._parse_single_concrete_input(
                concrete_inputs,
                bit_clear['name'],
                bit_clear['param']
            )
            if value is None:
                value = self._find_literal_single_call_value(code, bit_clear['name'])
            if value is not None:
                return self._concrete_bit_clear_analysis(bit_clear, value)

        ackermann = self._find_ackermann_function(code, language)
        if not ackermann:
            return None

        values = self._parse_concrete_input_values(
            concrete_inputs,
            ackermann['name'],
            ackermann['params']
        )
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
            'available': True,
            'kind': 'ackermann_exact',
            'function': ackermann['name'],
            'inputs': {param_a: m, param_b: n},
            'return_value': exact['return_value'],
            'calls': exact['calls'],
            'max_stack_depth': exact['max_stack_depth'],
            'time': f"{exact['calls']} function calls",
            'space': f"{exact['max_stack_depth']} stack frames",
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': 'O(A(m, n))',
            'symbolic_space_complexity': 'O(A(m, n))',
            'reason': 'Exact concrete-input simulation for fixed Ackermann inputs'
        }

    def _find_dfs_function(self, code, language):
        for name in re.findall(self._function_def_regex(), code):
            body = self._extract_function_body(code, name, language)
            if not body:
                continue

            adjacency_loop = re.search(
                r'for\s+(\w+)\s+in\s+(\w+)\s*\[\s*(\w+)\s*\]',
                body
            )
            visited_add = re.search(r'(\w+)\.add\s*\(\s*(\w+)\s*\)', body)
            recursive_neighbor_call = bool(re.search(
                rf'\b{name}\s*\([^)]*\b{adjacency_loop.group(1)}\b[^)]*\)',
                body
            )) if adjacency_loop else False
            visited_guard = bool(re.search(
                r'if\s+\w+\s+not\s+in\s+\w+|if\s*\(\s*!\s*\w+\.has\s*\(',
                body
            ))

            if adjacency_loop and visited_add and recursive_neighbor_call and visited_guard:
                params = self._function_param_names(code, name)
                return {
                    'name': name,
                    'graph_param': adjacency_loop.group(2),
                    'node_param': visited_add.group(2),
                    'visited_param': visited_add.group(1),
                    'neighbor_var': adjacency_loop.group(1),
                    'params': params,
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
                'available': False,
                'kind': 'dfs_exact',
                'function': dfs['name'],
                'reason': f'Concrete DFS exceeds safe simulation limit of {limit} steps'
            }

        return {
            'available': True,
            'kind': 'dfs_exact',
            'function': dfs['name'],
            'inputs': {
                dfs['node_param']: start,
                dfs['visited_param']: list(initial_visited),
                'graph_vertices': len(graph),
            },
            'return_value': None,
            'calls': calls,
            'max_stack_depth': max_depth,
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
        for name in re.findall(self._function_def_regex(), code):
            body = self._extract_function_body(code, name, language)
            if not body:
                continue
            match = re.search(
                r'while\s*\(?\s*(\w+)\s*>\s*0\s*\)?:?'
                r'(?:(?!\n\s*(?:def|function|public|private|protected)\b).)*?'
                r'(?:\b\1\s*=\s*\1\s*&\s*\(?\s*\1\s*-\s*1\s*\)?|\b\1\s*&=\s*\(?\s*\1\s*-\s*1\s*\)?)',
                body,
                re.IGNORECASE | re.DOTALL
            )
            if match:
                return {'name': name, 'param': match.group(1)}
        return None

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
            if 'n' in named:
                return self._one_int(named['n'])
            numbers = re.findall(r'-?\d+', concrete_inputs)
            if numbers:
                return self._one_int(numbers[0])

        return None

    def _find_literal_single_call_value(self, code, func_name):
        match = re.search(rf'\b{func_name}\s*\(\s*(-?\d+)\s*\)', code)
        if not match:
            return None
        return self._one_int(match.group(1))

    def _one_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _concrete_bit_clear_analysis(self, bit_clear, value):
        iterations = value.bit_count() if value > 0 else 0
        return {
            'available': True,
            'kind': 'bit_clear_exact',
            'function': bit_clear['name'],
            'inputs': {bit_clear['param']: value},
            'return_value': iterations,
            'calls': iterations,
            'max_stack_depth': 1,
            'time': f"{iterations} loop iterations",
            'space': '1 counter/input variable',
            'fixed_input_time_complexity': 'O(1)',
            'fixed_input_space_complexity': 'O(1)',
            'symbolic_time_complexity': 'O(popcount(n)), worst-case O(log n)',
            'symbolic_space_complexity': 'O(1)',
            'reason': 'Exact simulation for n = n & (n - 1), which removes one set bit per loop'
        }

    def _find_ackermann_function(self, code, language):
        for name in re.findall(self._function_def_regex(), code):
            body = self._extract_function_body(code, name, language)
            if body and self._has_ackermann_recursion(name, body):
                return {
                    'name': name,
                    'params': self._function_param_names(code, name)
                }
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
            call_match = re.search(
                rf'\b{func_name}\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)',
                concrete_inputs
            )
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
        if not match:
            return None
        return self._two_ints(match.group(1), match.group(2))

    def _two_ints(self, first, second):
        try:
            return int(first), int(second)
        except (TypeError, ValueError):
            return None

    def _simulate_ackermann(self, m, n, call_limit=100000):
        if m < 0 or n < 0:
            return {
                'available': False,
                'reason': 'Ackermann exact simulation requires non-negative integer inputs'
            }

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
                'available': False,
                'kind': 'ackermann_exact',
                'inputs': {'m': m, 'n': n},
                'reason': f'Concrete Ackermann input exceeds the safe simulation limit of {call_limit} calls'
            }

        return {
            'available': True,
            'return_value': value,
            'calls': calls,
            'max_stack_depth': max_depth
        }

    def _has_recursive_decrement_call(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(([^)]*)\)', body)
        for args in calls:
            if re.search(r'\b\w+\s*-\s*1\b|\b\w+\s*--|--\s*\w+', args):
                return True
        return False

    def _has_balanced_partition_recursion(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(([^)]*)\)', body)
        if len(calls) < 2:
            return False

        has_mid_definition = bool(re.search(
            r'\bmid\s*=\s*\(?\s*\w+\s*\+\s*\w+\s*\)?\s*(?://|/|>>)\s*2|'
            r'\bmid\s*=\s*\w+\s*\+\s*\(?\s*\w+\s*-\s*\w+\s*\)?\s*(?://|/)\s*2|'
            r'\bmid\s*=\s*Math\.floor\s*\(',
            body
        ))
        uses_left_half = any(re.search(r'\bmid\s*-\s*1\b|,\s*mid\s*[),]', call) for call in calls)
        uses_right_half = any(re.search(r'\bmid\s*\+\s*1\b|\bmid\s*,', call) for call in calls)
        direct_half_calls = sum(
            1 for call in calls
            if re.search(r'//\s*2|/\s*2|>>\s*1|Math\.floor', call)
        )

        return (has_mid_definition and uses_left_half and uses_right_half) or direct_half_calls >= 2

    def _has_recursive_shrinking_substring_calls(self, func_name, body):
        calls = re.findall(rf'\b{func_name}\s*\(', body)
        if len(calls) < 2:
            return False

        substring_shrink = bool(re.search(
            r'\.substring\s*\([^;\n]*(?:length\s*\(\)\s*-\s*1|,\s*[^)]*length\s*\(\s*\))',
            body
        ))
        slicing_shrink = bool(re.search(
            r'\[[^:\]]*(?::\s*-1|1\s*:|:\s*len\s*\([^)]*\)\s*-\s*1)',
            body
        ))
        return substring_shrink or slicing_shrink

    def _divide_and_conquer_complexity(self, branches, body_work):
        """
        Master Theorem approximation for T(n) = aT(n/2) + f(n).
        """
        import math

        body = self._parse_complexity_string(body_work)
        body_type, body_power = body
        critical_degree = math.log2(branches)

        body_degree = {
            'const': 0,
            'log': 0.5,
            'log2': 0.7,
            'n': body_power,
            'n_log': body_power + 0.5,
            'n_log2': body_power + 0.7,
            'n2_log': 2.5,
            'n3_log': 3.5,
        }.get(body_type, 1)

        if branches == 1:
            if body_type == 'const':
                return 'O(log n)'
            return body_work

        epsilon = 0.01
        if body_degree < critical_degree - epsilon:
            return self._tuple_to_string(('n', round(critical_degree)))
        if abs(body_degree - critical_degree) <= epsilon:
            base = self._tuple_to_string(('n', round(critical_degree)))
            return base.replace(')', ' log n)')
        return body_work
    # ─────────────────────────────────────────────
    # GRAPH ALGORITHM DETECTION
    # ─────────────────────────────────────────────

    def detect_graph_algorithm(self, code):
        """
        Detects known graph algorithms and returns their complexity.
        """
        code_lower = code.lower()

        # Dijkstra
        if re.search(r'dijkstra|priorityqueue|priority_queue', code, re.IGNORECASE):
            if re.search(r'dist|distance', code, re.IGNORECASE):
                return {
                    'detected': True,
                    'algorithm': 'Dijkstra\'s Shortest Path',
                    'complexity': 'O((V + E) log V)',
                    'space': 'O(V + E)',
                    'reason': 'Priority queue based graph traversal — O((V+E) log V)',
                    'can_optimize': False,
                    'note': 'This is already optimal for sparse graphs. For dense graphs, use Floyd-Warshall O(V³) only if V is small.'
                }

        # Bellman-Ford
        if re.search(r'bellman.?ford|relax', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Bellman-Ford',
                'complexity': 'O(V × E)',
                'space': 'O(V)',
                'reason': 'V-1 relaxation passes over all E edges',
                'can_optimize': True,
                'optimized_to': 'O((V + E) log V)',
                'note': 'If graph has no negative weights, replace with Dijkstra for O((V+E) log V).'
            }

        # Floyd-Warshall
        if re.search(r'floyd|warshall|all.?pairs', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Floyd-Warshall',
                'complexity': 'O(V³)',
                'space': 'O(V²)',
                'reason': 'Triple nested loop over all vertex pairs',
                'can_optimize': True,
                'optimized_to': 'O((V + E) log V)',
                'note': 'For sparse graphs, run Dijkstra from each vertex for better performance.'
            }

        # BFS
        if re.search(r'\bqueue\b|deque|bfs|breadth.?first', code, re.IGNORECASE):
            if re.search(r'visited|seen|graph|adj', code, re.IGNORECASE):
                return {
                    'detected': True,
                    'algorithm': 'Breadth-First Search (BFS)',
                    'complexity': 'O(V + E)',
                    'space': 'O(V)',
                    'reason': 'Each vertex and edge visited once',
                    'can_optimize': False,
                    'note': 'BFS is already optimal for unweighted shortest paths.'
                }

        # DFS
        if re.search(r'\bdfs\b|depth.?first|visited\s*=', code, re.IGNORECASE):
            if re.search(r'graph|adj|neighbor', code, re.IGNORECASE):
                return {
                    'detected': True,
                    'algorithm': 'Depth-First Search (DFS)',
                    'complexity': 'O(V + E)',
                    'space': 'O(V)',
                    'reason': 'Each vertex and edge visited once',
                    'can_optimize': False,
                    'note': 'DFS is already optimal for graph traversal.'
                }

        # Kruskal MST
        if re.search(r'kruskal|union.?find|disjoint', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': "Kruskal's MST",
                'complexity': 'O(E log E)',
                'space': 'O(V)',
                'reason': 'Sorting edges O(E log E) + Union-Find operations',
                'can_optimize': False,
                'note': 'Already optimal. Prim\'s algorithm is better for dense graphs: O(V²).'
            }

        # Prim MST
        if re.search(r'prim|minimum.?spanning', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': "Prim's MST",
                'complexity': 'O((V + E) log V)',
                'space': 'O(V)',
                'reason': 'Priority queue based MST construction',
                'can_optimize': False,
                'note': 'Already optimal for sparse graphs.'
            }

        # Topological sort
        if re.search(r'topological|topo.?sort|in.?degree', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Topological Sort',
                'complexity': 'O(V + E)',
                'space': 'O(V)',
                'reason': 'Each vertex and edge processed once',
                'can_optimize': False,
                'note': 'Already optimal for DAG ordering.'
            }

        return {'detected': False}

    # ─────────────────────────────────────────────
    # KNOWN ALGORITHM DETECTION
    # ─────────────────────────────────────────────

    def detect_known_algorithm(self, code):
        """
        Detects well-known algorithms beyond graphs.
        """
        # Generator T(n)=T(n-1)+T(n/2) must be checked before generic patterns.
        if re.search(r'yield\s*\*', code, re.IGNORECASE):
            for name in re.findall(r'function\s*\*\s*(\w+)', code):
                body = self._extract_function_body(code, name, 'javascript')
                if not body:
                    continue
                has_decrement = bool(re.search(rf'yield\s*\*\s*{name}\s*\([^)]*-\s*1', body))
                has_half = bool(re.search(rf'yield\s*\*\s*{name}\s*\([^)]*(?:Math\.floor|/\s*2)', body))
                if has_decrement and has_half:
                    return {
                        'detected': True,
                        'algorithm': 'Generator recursion T(n)=T(n-1)+T(n/2)',
                        'complexity': 'O(2^n)',
                        'space': 'O(2^n)',
                        'reason': 'T(n-1) dominates and creates exponentially many generator frames',
                        'can_optimize': True,
                        'optimized_to': 'O(n)',
                        'note': 'Replace the generator with a memoized plain function.'
                    }

        # Backtracking permutations / factorial search
        if self._looks_like_permutation_backtracking(code):
            return {
                'detected': True,
                'algorithm': 'Permutation Backtracking',
                'complexity': 'O(n * n!)',
                'space': 'O(n * n!)',
                'reason': 'Backtracking generates n! permutations and copies/builds each length-n result',
                'can_optimize': False,
                'note': 'If all permutations are required, factorial time is unavoidable. Stream results to reduce output memory.'
            }

        if self._looks_like_subset_generation(code):
            return {
                'detected': True,
                'algorithm': 'Subset / Power Set Generation',
                'complexity': 'O(n * 2^n)',
                'space': 'O(n * 2^n)',
                'reason': 'Generates all 2^n subsets and copies/builds subsets whose total size is n*2^(n-1)',
                'can_optimize': False,
                'note': 'Unavoidable if every subset must be returned. Stream subsets to reduce peak output memory.'
            }

        if self._looks_like_subset_backtracking(code):
            return {
                'detected': True,
                'algorithm': 'Subset Backtracking',
                'complexity': 'O(2^n)',
                'space': 'O(n)',
                'reason': 'Backtracking explores every subset',
                'can_optimize': True,
                'optimized_to': 'O(n × target) with DP',
                'note': 'Use memoization or tabulation when the target/state space is bounded.'
            }

        if re.search(r'sieve|eratosthenes|is_prime\s*=\s*\[', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Sieve of Eratosthenes',
                'complexity': 'O(n log log n)',
                'space': 'O(n)',
                'reason': 'The prime harmonic series gives n/2+n/3+n/5+... = O(n log log n)',
                'can_optimize': False,
                'note': 'Already optimal for finding all primes up to n.'
            }

        # Binary search
        if re.search(r'binary.?search|bisect|binarySearch', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Binary Search',
                'complexity': 'O(log n)',
                'space': 'O(1)',
                'reason': 'Input halved on each step',
                'can_optimize': False
            }

        # Merge sort
        if re.search(r'merge.?sort|mergeSort', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Merge Sort',
                'complexity': 'O(n log n)',
                'space': 'O(n)',
                'reason': 'Divide and conquer with linear merge step',
                'can_optimize': False
            }

        # Quick sort
        if re.search(r'quick.?sort|quickSort|partition', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Quick Sort',
                'complexity': 'O(n log n) average, O(n²) worst',
                'space': 'O(log n)',
                'reason': 'Partition-based divide and conquer',
                'can_optimize': True,
                'optimized_to': 'O(n log n) guaranteed',
                'note': 'Use randomized pivot or switch to Merge Sort/Tim Sort for O(n log n) guaranteed.'
            }

        # Bubble sort
        if re.search(r'bubble.?sort|bubbleSort', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Bubble Sort',
                'complexity': 'O(n²)',
                'space': 'O(1)',
                'reason': 'Nested comparison passes over array',
                'can_optimize': True,
                'optimized_to': 'O(n log n)',
                'note': 'Replace with built-in sort() or Merge Sort for O(n log n).'
            }

        if re.search(r'counting.?sort|countingSort|radix.?sort|radixSort', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Counting/Radix Sort',
                'complexity': 'O(n + k)',
                'space': 'O(n + k)',
                'reason': 'Linear-time sorting for bounded integer keys',
                'can_optimize': False
            }

        if re.search(r'kmp|knuth.?morris|failure.?function|lps\s*=', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'KMP String Search',
                'complexity': 'O(n + m)',
                'space': 'O(m)',
                'reason': 'Linear preprocessing plus linear scan',
                'can_optimize': False
            }

        if re.search(r'rabin.?karp|rolling.?hash', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Rabin-Karp',
                'complexity': 'O(n + m) average',
                'space': 'O(1)',
                'reason': 'Rolling hash comparison',
                'can_optimize': False
            }

        if re.search(r'\bz.?array\b|z.?function|z\s*\[', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Z-Algorithm',
                'complexity': 'O(n)',
                'space': 'O(n)',
                'reason': 'Linear Z-array construction',
                'can_optimize': False
            }

        if re.search(r'\blcs\b|longest.?common.?sub|edit.?distance|levenshtein', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'LCS / Edit Distance (DP)',
                'complexity': 'O(n × m)',
                'space': 'O(n × m)',
                'reason': 'DP table over two strings',
                'can_optimize': False,
                'note': 'Space can often be reduced to O(min(n,m)) with rolling rows.'
            }

        if re.search(r'matrix.?chain|matrixChain|mcm', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Matrix Chain Multiplication',
                'complexity': 'O(n³)',
                'space': 'O(n²)',
                'reason': 'DP over all subchains, O(n²) cells with O(n) split choices',
                'can_optimize': False
            }

        if re.search(r'\btsp\b|travelling.?salesman|traveling.?salesman', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Travelling Salesman (DP/Bitmask)',
                'complexity': 'O(n² × 2^n)',
                'space': 'O(n × 2^n)',
                'reason': 'Bitmask DP over all subsets and ending cities',
                'can_optimize': False,
                'note': 'NP-hard; heuristics trade exactness for speed.'
            }

        if re.search(r'\bnqueens\b|n.?queens|queen.?place', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'N-Queens Backtracking',
                'complexity': 'O(n!)',
                'space': 'O(n)',
                'reason': 'Permutation search with pruning',
                'can_optimize': False
            }

        if re.search(r'sqrt.?decomp|mos.?algo|block.?size.*sqrt|math\.sqrt.*block', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': "Sqrt Decomposition / Mo's Algorithm",
                'complexity': 'O((n + q) √n)',
                'space': 'O(√n)',
                'reason': 'Queries grouped by square-root sized blocks',
                'can_optimize': False
            }

        if re.search(r'segment.?tree|segTree|seg_tree|build.*seg|query.*seg', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Segment Tree',
                'complexity': 'O(n) build, O(log n) query/update',
                'space': 'O(n)',
                'reason': 'Binary tree over range segments',
                'can_optimize': False
            }

        if re.search(r'fenwick|bit\s*\[|binary.?indexed', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Fenwick Tree (BIT)',
                'complexity': 'O(log n) query/update',
                'space': 'O(n)',
                'reason': 'Low-bit jumps update/query logarithmically',
                'can_optimize': False
            }

        # Selection sort
        if re.search(r'selection.?sort|selectionSort', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Selection Sort',
                'complexity': 'O(n²)',
                'space': 'O(1)',
                'reason': 'Finds minimum n times over shrinking array',
                'can_optimize': True,
                'optimized_to': 'O(n log n)',
                'note': 'Replace with built-in sort() or Heap Sort for O(n log n).'
            }

        # Insertion sort
        if re.search(r'insertion.?sort|insertionSort', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Insertion Sort',
                'complexity': 'O(n²)',
                'space': 'O(1)',
                'reason': 'Each element shifted into correct position',
                'can_optimize': True,
                'optimized_to': 'O(n log n)',
                'note': 'Good for small/nearly-sorted arrays. Use Merge Sort for large inputs.'
            }

        # Dynamic programming
        if re.search(r'dp\s*=\s*\[|memo\s*=\s*\{|@lru_cache|knapsack', code, re.IGNORECASE):
            return {
                'detected': True,
                'algorithm': 'Dynamic Programming',
                'complexity': 'O(n) to O(n²) depending on subproblems',
                'space': 'O(n)',
                'reason': 'Memoized subproblem solutions',
                'can_optimize': False,
                'note': 'DP is already optimized. Space can sometimes be reduced using rolling arrays.'
            }

        return {'detected': False}

    def _looks_like_permutation_backtracking(self, code):
        code_lower = code.lower()
        has_permutation_name = bool(re.search(
            r'\b(permute|permutation|permutations|backtrack)\b',
            code_lower
        ))
        has_used_flags = bool(re.search(
            r'boolean\s*\[\]\s*used|used\s*=\s*\[|visited\s*=\s*\[|used\[.*?\]\s*=',
            code,
            re.IGNORECASE
        ))
        has_result_copy = bool(re.search(
            r'new\s+ArrayList\s*<|result\.add|results\.append|res\.append|\[\.\.\.current\]',
            code,
            re.IGNORECASE
        ))
        has_backtrack_call = len(re.findall(r'\bbacktrack\s*\(', code, re.IGNORECASE)) >= 2
        has_full_length_base = bool(re.search(
            r'current\.size\s*\(\)\s*==\s*\w+\.length|len\s*\(\s*current\s*\)\s*==\s*len\s*\(',
            code,
            re.IGNORECASE
        ))

        return (
            has_permutation_name and
            has_used_flags and
            has_result_copy and
            (has_backtrack_call or has_full_length_base)
        )

    def _looks_like_subset_generation(self, code):
        has_subset_name = bool(re.search(
            r'\b(subset|subsets|power.?set|powerset|combination|combinations)\b',
            code,
            re.IGNORECASE
        ))
        returns_list_of_lists = bool(re.search(
            r'return\s+\[\s*\[\s*\]\s*\]|return\s+new\s+ArrayList\s*<|return\s+result|return\s+res|return\s+ans',
            code,
            re.IGNORECASE
        ))
        recursive_step = bool(re.search(
            r'\b\w+\s*=\s*(\w+)\s*\([^)]*(?:\+\s*1|-\s*1)[^)]*\)',
            code
        ))
        iterates_previous_results = bool(re.search(
            r'for\s+\w+\s+in\s+\w+|for\s*\([^;]*:[^)]*\)|for\s*\([^;]*of\s+\w+',
            code,
            re.IGNORECASE
        ))
        duplicates_or_prepends = bool(re.search(
            r'\.append\s*\(\s*\[|\.append\s*\(\s*\w+\s*\)|\.append\s*\([^)]*\+\s*\w+\)|'
            r'\[\s*\w+\[[^]]+\]\s*\]\s*\+\s*\w+|'
            r'\.add\s*\(\s*new\s+ArrayList|\.push\s*\(\s*\[|'
            r'\[\s*\.\.\.\w+|concat\s*\(',
            code,
            re.IGNORECASE
        ))

        return (
            has_subset_name and
            returns_list_of_lists and
            recursive_step and
            iterates_previous_results and
            duplicates_or_prepends
        )

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
        func_pattern = self._function_def_regex()
        func_names = re.findall(func_pattern, code)

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
            if complexity == 'O(n)':
                rec_type = 'linear'
            elif complexity == 'O(log n)':
                rec_type = 'divide_conquer_single'
            elif complexity == 'O(n log n)':
                rec_type = 'divide_conquer'
            elif complexity in ('O((log n)!)', 'O(n^log n)'):
                rec_type = 'quasi_polynomial'
            elif complexity == 'O(A(m, n))':
                rec_type = 'ackermann'
            elif '^n)' in complexity:
                rec_type = 'exponential'
            return {
                'is_recursive': True,
                'type': rec_type,
                'branches': call_count,
                'func_name': name,
                'complexity': complexity,
                'reason': recursion_result['reason']
            }

        return {'is_recursive': False}

    def detect_mutual_recursion(self, code, language):
        func_pattern = self._function_def_regex()
        func_names = re.findall(func_pattern, code)
        bodies = {
            name: self._extract_function_body(code, name, language)
            for name in func_names
        }

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
                        'detected': True,
                        'complexity': 'O(log log n)',
                        'space': 'O(log log n)',
                        'functions': [caller, callee],
                        'reason': (
                            f"Mutual recursion cycle {caller} -> {callee} -> {caller} "
                            "shrinks by square root, giving O(log log n) depth"
                        )
                    }
                if re.search(r'\b\w+\s*-\s*1\b', cycle_text):
                    return {
                        'detected': True,
                        'complexity': 'O(n)',
                        'space': 'O(n)',
                        'functions': [caller, callee],
                        'reason': (
                            f"Mutual recursion cycle {caller} <-> {callee} decreases "
                            "the input linearly"
                        )
                    }

        return {'detected': False}

    def _mutual_cycle_has_sqrt_shrink(self, caller, callee, caller_body, callee_body):
        call_patterns = [
            rf'\b{callee}\s*\([^)]*(?:sqrt|Math\.sqrt)[^)]*\)',
            rf'\b{caller}\s*\([^)]*(?:sqrt|Math\.sqrt)[^)]*\)',
        ]
        if any(re.search(pattern, caller_body) or re.search(pattern, callee_body) for pattern in call_patterns):
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
        contexts = []
        loop_stack = []
        lines = body.split('\n')

        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            indent = self._get_indent(line)
            loop_stack = [item for item in loop_stack if item['indent'] < indent]

            for name in target_names:
                if name == current_func:
                    continue
                if re.search(rf'\b{name}\s*\(', stripped):
                    multiplier = ('const', 0)
                    for loop in loop_stack:
                        multiplier = self._multiply_complexity(multiplier, loop['complexity'])
                    contexts.append((name, self._tuple_to_string(multiplier)))

            is_loop = (
                re.match(r'for\s*[\(\s]', stripped) or
                re.match(r'while\s*[\(\s]', stripped)
            )
            if is_loop:
                body_after_header = lines[index + 1:]
                loop_type = (
                    self.classify_for_loop(stripped, body_after_header, lines, 'unknown')
                    if stripped.startswith('for')
                    else self.classify_while_loop(stripped, body_after_header, lines, 'unknown')
                )
                loop_stack.append({
                    'indent': indent,
                    'complexity': ('log', 1) if loop_type == 'logarithmic' else ('n', 1)
                })

        return contexts

    def _extract_function_body(self, code, func_name, language):
        if language in ('java', 'cpp', 'c', 'javascript'):
            signature = re.search(
                rf'(?:def\s+|function\s*\*?\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:void|int|long|double|float|boolean|bool|char|String|List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+){func_name}\s*\([^)]*\)',
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
                                return self._brace_code_to_indented_lines(code[open_brace + 1:pos])

        lines = code.split('\n')
        in_func = False
        body_lines = []
        base_indent = None

        for line in lines:
            stripped = line.strip()
            if re.match(rf'(?:def\s+|function\s*\*?\s+|(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:void|int|long|double|float|boolean|bool|char|String|List[\w<>\[\], ?]*|ArrayList[\w<>\[\], ?]*|Map[\w<>\[\], ?]*|HashMap[\w<>\[\], ?]*|vector[\w<>\[\], ?&*]*|[A-Z]\w*(?:<[^)]*>)?)\s+){func_name}\s*\(', stripped):
                in_func = True
                base_indent = len(line) - len(line.lstrip())
                continue
            if in_func:
                if not stripped:
                    body_lines.append(line)
                    continue
                curr_indent = len(line) - len(line.lstrip())
                if curr_indent <= base_indent and stripped:
                    break
                body_lines.append(line)

        return '\n'.join(body_lines)

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
                paren_depth += 1
                current.append(char)
            elif char == ')':
                paren_depth = max(0, paren_depth - 1)
                current.append(char)
            elif char == '{':
                flush()
                indent += 1
            elif char == '}':
                flush()
                indent = max(0, indent - 1)
            elif char == ';' and paren_depth == 0:
                current.append(char)
                flush()
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
        """
        Handles loop families where plain nesting over/under-estimates:
        geometric prefix sums and harmonic step loops.
        """
        compact = re.sub(r'\s+', ' ', code)

        shifted_log_sum = bool(re.search(
            r'while\s+(\w+)\s*<\s*(\w+).*?\b(\w+)\s*=\s*\1\s+'
            r'while\s+\3\s*<\s*\2.*?'
            r'(?:\3\s*\*=\s*2|\3\s*=\s*\3\s*\*\s*2|\3\s*<<=\s*1).*?'
            r'(?:\1\s*\+=\s*1|\1\s*=\s*\1\s*\+\s*1|\1\+\+|\+\+\1)',
            compact,
            re.IGNORECASE
        ))
        shifted_log_for_sum = bool(re.search(
            r'for\s+(\w+)\s+in\s+range\s*\(\s*(?:1\s*,\s*)?(\w+)\s*\).*?'
            r'\b(\w+)\s*=\s*\1\s+while\s+\3\s*<\s*\2.*?'
            r'(?:\3\s*\*=\s*2|\3\s*=\s*\3\s*\*\s*2|\3\s*<<=\s*1)',
            compact,
            re.IGNORECASE
        ))
        shifted_log_js_sum = bool(re.search(
            r'for\s*\([^;]*(\w+)\s*=\s*1\s*;\s*\1\s*<\s*(\w+)[^;]*;[^)]*\).*?'
            r'(?:let|var|const)?\s*(\w+)\s*=\s*\1\s*;.*?'
            r'while\s*\(?\s*\3\s*<\s*\2\s*\)?.*?'
            r'(?:\3\s*\*=\s*2|\3\s*=\s*\3\s*\*\s*2|\3\s*<<=\s*1)',
            compact,
            re.IGNORECASE
        ))
        if shifted_log_sum or shifted_log_for_sum or shifted_log_js_sum:
            return {
                'detected': True,
                'complexity': 'O(n)',
                'reason': 'Shifted logarithmic inner loop: sum_i log(n/i) = O(n)'
            }

        harmonic_while_python = bool(re.search(
            r'for\s+(\w+)\s+in\s+range\s*\(\s*1\s*,\s*(\w+)(?:\s*\+\s*1)?\s*\).*?'
            r'\b(\w+)\s*=\s*(?:0|1)\s+while\s+\3\s*(?:<|<=)\s*\2\s*:?.*?'
            r'\b\3\s*\+=\s*\1\b',
            compact,
            re.IGNORECASE
        ))
        harmonic_while_js = bool(re.search(
            r'for\s*\(\s*(?:let|var|const|int|long)?\s*(\w+)\s*=\s*1\s*;'
            r'\s*\1\s*<=?\s*(\w+)[^;]*;[^)]*(?:\1\+\+|\+\+\1|\1\s*\+=\s*1)[^)]*\).*?'
            r'(?:let|var|const|int|long)?\s*(\w+)\s*=\s*(?:0|1)\s*;?\s*'
            r'while\s*\(?\s*\3\s*<=?\s*\2\s*\)?.*?'
            r'\b\3\s*\+=\s*\1\b',
            compact,
            re.IGNORECASE
        ))
        if harmonic_while_python or harmonic_while_js:
            return {
                'detected': True,
                'complexity': 'O(n log n)',
                'reason': 'Harmonic step loop: inner work sums n/1 + n/2 + ... + n/n = O(n log n)'
            }

        geometric_prefix_linear = bool(re.search(
            r'while\s+(\w+)\s*<\s*\w+.*?for\s+\w+\s+in\s+range\s*\(\s*\1\s*\).*?(?:\1\s*\*=\s*2|\1\s*=\s*\1\s*\*\s*2|\1\s*<<=\s*1)',
            compact,
            re.IGNORECASE
        ))
        if geometric_prefix_linear:
            return {
                'detected': True,
                'complexity': 'O(n)',
                'reason': 'Geometric prefix sum detected: 1 + 2 + 4 + ... + n is O(n)'
            }

        geometric_prefix = bool(re.search(
            r'while\s+\w+\s*<\s*\w+.*?for\s+\w+\s+in\s+range\s*\(\s*\w+\s*\).*?while\s+\w+\s*<\s*\w+.*?\*=\s*2.*?\*=\s*2',
            compact,
            re.IGNORECASE
        ))
        if geometric_prefix:
            return {
                'detected': True,
                'complexity': 'O(n log n)',
                'reason': 'Geometric outer loop sums inner ranges to O(n), with an inner logarithmic loop'
            }

        harmonic_step_js = bool(re.search(
            r'for\s*\(\s*(?:let|var|const)?\s*(\w+)\s*=[^;]*;\s*\1\s*\*\s*\1\s*<=?\s*\w+[^;]*;\s*\1\+\+.*?for\s*\([^;]*;[^;]*<\s*\w+[^;]*;\s*\w+\s*\+=\s*\1\s*\)',
            compact,
            re.IGNORECASE
        ))
        harmonic_step_python = bool(re.search(
            r'for\s+\w+\s+in\s+range\s*\(\s*1\s*,.*?\).*?for\s+\w+\s+in\s+range\s*\(\s*0\s*,\s*\w+\s*,\s*\w+\s*\)',
            compact,
            re.IGNORECASE
        ))
        if harmonic_step_js or harmonic_step_python:
            return {
                'detected': True,
                'complexity': 'O(n log n)',
                'reason': 'Harmonic loop detected: inner work is n/1 + n/2 + ... = O(n log n)'
            }

        return {'detected': False}

    def detect_catastrophic_regex(self, code):
        """
        Detects regexes with nested ambiguous quantifiers that can cause
        catastrophic backtracking in engines such as JavaScript RegExp.
        """
        regex_patterns = []

        regex_patterns.extend(re.findall(
            r'/(.+?)/[gimsuy]*',
            code
        ))
        regex_patterns.extend(re.findall(
            r'RegExp\s*\(\s*[\'"](.+?)[\'"]',
            code
        ))
        regex_patterns.extend(re.findall(
            r're\.compile\s*\(\s*[rR]?[\'"](.+?)[\'"]',
            code
        ))

        if not regex_patterns:
            return {'detected': False}

        regex_is_used = bool(re.search(
            r'\.test\s*\(|\.match\s*\(|\.search\s*\(|\.exec\s*\(|re\.(?:match|search|fullmatch)\s*\(',
            code
        ))
        if not regex_is_used:
            return {'detected': False}

        for pattern in regex_patterns:
            if self._has_catastrophic_regex_shape(pattern):
                return {
                    'detected': True,
                    'complexity': 'O(2^n)',
                    'space': 'O(n)',
                    'pattern': pattern,
                    'reason': (
                        'Catastrophic regex backtracking detected: nested ambiguous '
                        'quantifiers can try exponentially many matches'
                    )
                }

        return {'detected': False}

    def _has_catastrophic_regex_shape(self, pattern):
        nested_quantifier = bool(re.search(
            r'\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*[+*{]',
            pattern
        ))
        overlapping_alternation = bool(re.search(
            r'\(([^|()]+)\|(\1[^()]*)\)\s*[+*{]',
            pattern
        ))
        repeated_wildcard = bool(re.search(
            r'\((?:\.\*|\.\+|\[[^\]]+\][+*])\)\s*[+*{]',
            pattern
        ))
        return nested_quantifier or overlapping_alternation or repeated_wildcard

    def _is_sorting_call(self, line):
        return bool(re.search(
            r'\.sort\s*\(|\bsorted\s*\(|Arrays\.sort|Collections\.sort|\bsort\s*\(',
            line
        ))

    def _sorting_complexity(self, code):
        if not any(self._is_sorting_call(line) for line in code.split('\n')):
            return None

        max_depth = self._max_sorting_loop_depth(code)
        if max_depth <= 0:
            return 'O(n log n)'
        if max_depth == 1:
            return 'O(n² log n)'
        if max_depth == 2:
            return 'O(n³ log n)'
        return f'O(n^{max_depth + 1} log n)'

    def _max_sorting_loop_depth(self, code):
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

        return max_depth

    def classify_loop(self, body_lines, all_lines, lang):
        body = '\n'.join(body_lines) if isinstance(body_lines, list) else body_lines
        log_patterns = [
            r'\*=\s*2', r'\/=\s*2', r'>>=\s*1', r'<<=\s*1',
            r'Math\.floor\s*\(\s*\w+\s*\/\s*2\s*\)',
            r'\w+\s*=\s*\w+\s*\*\s*2',
            r'\w+\s*=\s*\w+\s*\/\s*2',
            r'\b(\w+)\s*\+=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
            r'\b(\w+)\s*-=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
            r'\b(\w+)\s*=\s*\1\s*[+-]\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
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
        control_growth_patterns = [
            rf'\b{control}\s*\*=\s*2\b',
            rf'\b{control}\s*=\s*{control}\s*\*\s*2\b',
            rf'\b{control}\s*=\s*2\s*\*\s*{control}\b',
            rf'\b{control}\s*<<=\s*1\b',
            rf'\b{control}\s*(?://|/)=\s*2\b',
            rf'\b{control}\s*=\s*{control}\s*(?://|/)\s*2\b',
            rf'\b{control}\s*>>=\s*1\b',
            rf'\b{control}\s*\+=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*-=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*[+-]\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*&\s*\(?\s*{control}\s*-\s*1\s*\)?',
            rf'\b{control}\s*&=\s*\(?\s*{control}\s*-\s*1\s*\)?',
        ]
        if any(re.search(pattern, body) for pattern in control_growth_patterns):
            return 'logarithmic'
        return 'linear'

    def classify_for_loop(self, header, body_lines, all_lines, lang):
        js_for = re.search(r'for\s*\([^;]*;[^;]*;([^)]*)\)', header)
        if js_for:
            update = js_for.group(1).strip()
            for p in [
                r'\*=\s*2',
                r'\/=\s*2',
                r'>>=\s*1',
                r'=\s*\w+\s*\*\s*2',
                r'=\s*\w+\s*\/\s*2',
                r'\b(\w+)\s*\+=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
                r'\b(\w+)\s*-=\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
                r'\b(\w+)\s*=\s*\1\s*[+-]\s*\(?\s*\1\s*&\s*-\s*\1\s*\)?',
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

        for_match = re.search(
            r'for\s*\(\s*(?:(?:let|var|const|int|long|size_t)\s+)?(\w+)\s*=',
            header
        )
        if for_match:
            return for_match.group(1)

        return None

    def _loop_growth_variable(self, header, body_lines):
        control = self._loop_control_variable(header)
        if not control:
            return None

        body = '\n'.join(body_lines) if isinstance(body_lines, list) else str(body_lines)
        growth_patterns = [
            rf'\b{control}\s*\*=\s*2\b',
            rf'\b{control}\s*=\s*{control}\s*\*\s*2\b',
            rf'\b{control}\s*=\s*2\s*\*\s*{control}\b',
            rf'\b{control}\s*<<=\s*1\b',
            rf'\b{control}\s*(?://|/)=\s*2\b',
            rf'\b{control}\s*=\s*{control}\s*(?://|/)\s*2\b',
            rf'\b{control}\s*>>=\s*1\b',
            rf'\b{control}\s*\+=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*-=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*[+-]\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
            rf'\b{control}\s*=\s*{control}\s*&\s*\(?\s*{control}\s*-\s*1\s*\)?',
            rf'\b{control}\s*&=\s*\(?\s*{control}\s*-\s*1\s*\)?',
        ]
        if any(re.search(pattern, body) for pattern in growth_patterns):
            return control

        js_for = re.search(r'for\s*\([^;]*;[^;]*;([^)]*)\)', header)
        if js_for:
            update = js_for.group(1)
            update_patterns = [
                rf'\b{control}\s*\*=\s*2\b',
                rf'\b{control}\s*=\s*{control}\s*\*\s*2\b',
                rf'\b{control}\s*=\s*2\s*\*\s*{control}\b',
                rf'\b{control}\s*<<=\s*1\b',
                rf'\b{control}\s*(?://|/)=\s*2\b',
                rf'\b{control}\s*=\s*{control}\s*(?://|/)\s*2\b',
                rf'\b{control}\s*>>=\s*1\b',
                rf'\b{control}\s*\+=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
                rf'\b{control}\s*-=\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
                rf'\b{control}\s*=\s*{control}\s*[+-]\s*\(?\s*{control}\s*&\s*-\s*{control}\s*\)?',
                rf'\b{control}\s*=\s*{control}\s*&\s*\(?\s*{control}\s*-\s*1\s*\)?',
                rf'\b{control}\s*&=\s*\(?\s*{control}\s*-\s*1\s*\)?',
            ]
            if any(re.search(pattern, update) for pattern in update_patterns):
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
            if power:
                return ('n', power)

        js_match = re.search(r'for\s*\([^;]*;([^;]*);[^)]*\)', header)
        if js_match:
            control = self._loop_control_variable(header)
            condition = js_match.group(1)
            if control:
                bound = self._condition_bound_expression(condition, control)
                power = self._polynomial_bound_power(bound)
                if power:
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
            is_loop = (
                re.match(r'for\s*[\(\s]', stripped) or
                re.match(r'while\s*[\(\s]', stripped)
            )
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
                    'type': loop_type,
                    'header': header,
                    'children': children,
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
        if type_a in ('quasi_log_fact', 'quasi_poly') or type_b in ('quasi_log_fact', 'quasi_poly'):
            return ('quasi_poly', 1)
        if type_a == 'log' and type_b == 'n':
            if pow_b == 2:
                return ('n2_log', 1)
            if pow_b == 3:
                return ('n3_log', 1)
            return ('n_log', 1)
        if type_a == 'n' and type_b == 'log':
            if pow_a == 2:
                return ('n2_log', 1)
            if pow_a == 3:
                return ('n3_log', 1)
            return ('n_log', 1)
        combos = {
            ('n', 'n'): ('n', pow_a + pow_b),
            ('n', 'log'): ('n_log', 1),
            ('log', 'n'): ('n_log', 1),
            ('log', 'log'): ('log2', 1),
            ('n', 'n_log'): ('n2_log', 1),
            ('n_log', 'n'): ('n2_log', 1),
            ('n', 'log2'): ('n_log2', 1),
            ('log2', 'n'): ('n_log2', 1),
            ('n_log', 'log'): ('n_log2', 1),
            ('log', 'n_log'): ('n_log2', 1),
        }
        result = combos.get((type_a, type_b))
        if result:
            return result
        if type_a == 'n' and type_b == 'n':
            return ('n', pow_a + pow_b)
        return ('n', pow_a + pow_b)

    def _complexity_rank(self, c):
        type_c, pow_c = c
        ranks = {
            'const': 0, 'loglog': 0.5, 'log': 1, 'log2': 2, 'sqrt': 2.5,
            'n': 10, 'n_log': 20, 'n_log2': 25,
            'n2_log': 35, 'n3_log': 45, 'factorial': 110,
            'n_factorial': 120, 'ackermann': 140, 'exp': 100, 'n_exp': 105,
            'quasi_log_fact': 90, 'quasi_poly': 90
        }
        if type_c == 'n':
            if pow_c == 1: return 10
            if pow_c == 2: return 30
            if pow_c == 3: return 40
            return 40 + pow_c
        return ranks.get(type_c, 10)

    def _max_complexity_tuple(self, complexities):
        return max(complexities, key=self._complexity_rank)

    def _max_complexity(self, complexities):
        tuples = [self._parse_complexity_string(c) for c in complexities if c]
        if not tuples:
            return 'O(1)'
        best = self._max_complexity_tuple(tuples)
        return self._tuple_to_string(best)

    def _parse_complexity_string(self, s):
        if not s:
            return ('const', 0)
        if isinstance(s, tuple):
            return s
        mapping = {
            'O(1)': ('const', 0),
            'O(log log n)': ('loglog', 1),
            'O(log n)': ('log', 1),
            'O(log² n)': ('log2', 1),
            'O(√n)': ('sqrt', 1),
            'O(n)': ('n', 1),
            'O(n log log n)': ('n', 1),
            'O(n log n)': ('n_log', 1),
            'O(n log² n)': ('n_log2', 1),
            'O(n²)': ('n', 2),
            'O(n^2)': ('n', 2),
            'O(n² log n)': ('n2_log', 1),
            'O(n^2 log n)': ('n2_log', 1),
            'O(n³)': ('n', 3),
            'O(n^3)': ('n', 3),
            'O(n³ log n)': ('n3_log', 1),
            'O(n^3 log n)': ('n3_log', 1),
            'O(n!)': ('factorial', 1),
            'O((log n)!)': ('quasi_log_fact', 1),
            'O(n^log n)': ('quasi_poly', 1),
            'O(n × n!)': ('n_factorial', 1),
            'O(n * n!)': ('n_factorial', 1),
            'O(A(m, n))': ('ackermann', 1),
            'O(2ⁿ)': ('exp', 2),
            'O(2^n)': ('exp', 2),
            'O(n * 2^n)': ('n_exp', 2),
            'O(n × 2^n)': ('n_exp', 2),
            'O(n² × 2^n)': ('n_exp', 2),
            'O(3ⁿ)': ('exp', 3),
            'O(3^n)': ('exp', 3),
            'O((V + E) log V)': ('n_log', 1),
            'O(V + E)': ('n', 1),
            'O(V × E)': ('n', 2),
            'O(V³)': ('n', 3),
            'O(n + k)': ('n', 1),
            'O(n + m)': ('n', 1),
            'O(n × m)': ('n', 2),
            'O(log n) query/update': ('log', 1),
            'O(n) build, O(log n) query/update': ('n', 1),
            'O((n + q) √n)': ('n', 2),
            'O(n log n) average, O(n²) worst': ('n', 2),
            'O(n + m) average': ('n', 1),
        }
        return mapping.get(s, ('n', 1))

    def _tuple_to_string(self, c):
        type_c, pow_c = c
        mapping = {
            'const': 'O(1)', 'loglog': 'O(log log n)', 'log': 'O(log n)', 'log2': 'O(log² n)', 'sqrt': 'O(√n)',
            'n_log': 'O(n log n)', 'n_log2': 'O(n log² n)',
            'n2_log': 'O(n² log n)', 'n3_log': 'O(n³ log n)',
            'factorial': 'O(n!)', 'n_factorial': 'O(n * n!)',
            'ackermann': 'O(A(m, n))',
            'quasi_log_fact': 'O((log n)!)', 'quasi_poly': 'O(n^log n)',
            'n_exp': f'O(n * {pow_c}^n)', 'exp': f'O({pow_c}^n)',
        }
        if type_c in mapping:
            return mapping[type_c]
        if type_c == 'n':
            if pow_c == 1: return 'O(n)'
            if pow_c == 2: return 'O(n²)'
            if pow_c == 3: return 'O(n³)'
            return f'O(n^{pow_c})'
        return 'O(n)'

    # ─────────────────────────────────────────────
    # MAIN TIME COMPLEXITY DETECTION
    # ─────────────────────────────────────────────

    def detect_time_complexity(self, code, language):
        # 1. Check graph algorithms first
        graph = self.detect_graph_algorithm(code)
        if graph['detected']:
            return {
                'complexity': graph['complexity'],
                'reason': graph['reason'],
                'graph': graph,
                'recursion': None
            }

        # 2. Check known algorithms that should override structural loop analysis
        known = self.detect_known_algorithm(code)
        if known['detected'] and known.get('algorithm') != 'Dynamic Programming':
            return {
                'complexity': known['complexity'],
                'reason': known['reason'],
                'known': known,
                'recursion': None
            }

        # 3. Analyze recursion
        recursion = self.analyze_recursion(code, language)
        mutual_recursion = self.detect_mutual_recursion(code, language)

        if known['detected']:
            return {
                'complexity': known['complexity'],
                'reason': known['reason'],
                'known': known,
                'recursion': None
            }

        if mutual_recursion['detected']:
            return {
                'complexity': mutual_recursion['complexity'],
                'reason': mutual_recursion['reason'],
                'known': None,
                'recursion': mutual_recursion,
                'graph': None
            }

        # 4. Regex engine behavior can dominate ordinary loop structure
        regex = self.detect_catastrophic_regex(code)
        if regex['detected']:
            return {
                'complexity': regex['complexity'],
                'reason': regex['reason'],
                'known': None,
                'recursion': None,
                'graph': None,
                'regex': regex
            }

        # 5. Analyze special loop summations before generic nesting
        special_loop = self.detect_special_loop_patterns(code, language)
        if special_loop['detected']:
            return {
                'complexity': special_loop['complexity'],
                'reason': special_loop['reason'],
                'known': None,
                'recursion': None,
                'graph': None
            }

        # 6. Analyze loops
        loops = self.extract_loop_tree(code, language)
        loop_complexity = self.compute_loop_complexity(loops)

        sorting_complexity = self._sorting_complexity(code)
        has_sorting = sorting_complexity is not None

        if not loops and not recursion['is_recursive'] and not has_sorting:
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

        has_2d = bool(re.search(r'\[\s*\[|\[\s*\]\s*\*\s*n', code))
        has_dict = bool(re.search(r'\{\}|new\s+HashMap|new\s+Map\(\)|dict\(\)', code))
        has_array = bool(re.search(
            r'=\s*\[\]|new\s+Array|new\s+ArrayList|new\s+\w+\s*\[|Arrays\.copyOf|copyOf\s*\(|\.append\(',
            code,
            re.MULTILINE
        ))
        has_cpp_vector_alloc = any(
            re.search(r'\bvector\s*<[^>]+>\s+\w+\s*(?:\(|=|\{)', line.strip()) and
            not re.search(self._function_def_regex(), line.strip())
            for line in code.split('\n')
        )
        recursion = self.analyze_recursion(code, language)
        has_recursion = bool(recursion['is_recursive'])
        has_dp = bool(re.search(r'dp\s*=\s*\[|memo\s*=\s*\{|cache\s*=', code))
        func_complexities = self._extract_all_function_complexities(code, language)
        materialized_complexity = self._materialized_generator_complexity(code, func_complexities)

        if materialized_complexity:
            return materialized_complexity
        if has_recursion and recursion.get('type') == 'ackermann':
            return 'O(A(m, n))'
        if has_recursion and self._has_recursive_shrinking_substring_calls(
            recursion.get('func_name', ''), code
        ):
            return 'O(n²)'
        if has_dp and has_2d: return 'O(n²)'
        if has_dp: return 'O(n)'
        if has_2d: return 'O(n²)'
        if has_recursion and recursion.get('type') == 'quasi_polynomial':
            return 'O(n)'
        if has_recursion and re.search(r'\/\s*2|>>\s*1|mid\s*=|Math\.floor\s*\(\s*\w+\s*\/\s*2', code):
            return 'O(log n)'
        if has_recursion: return 'O(n)'
        if has_array or has_dict or has_cpp_vector_alloc: return 'O(n)'
        return 'O(1)'

    def _materialized_generator_complexity(self, code, func_complexities):
        for func_name, complexity in func_complexities.items():
            materialized = re.search(rf'\[\s*\.\.\.\s*{func_name}\s*\(', code)
            if materialized and complexity in ('O(n^log n)', 'O((log n)!)', 'O(2^n)', 'O(3^n)'):
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
        if recursion['is_recursive'] and recursion.get('type') == 'exponential':
            issues.append({
                'line': self._find_recursive_func_line(code, lines),
                'type': 'performance',
                'severity': 'high',
                'message': f'Exponential recursion ({recursion["complexity"]}) — add memoization or use dynamic programming'
            })

        regex = self.detect_catastrophic_regex(code)
        if regex['detected']:
            issues.append({
                'line': self._find_regex_line(lines),
                'type': 'performance',
                'severity': 'high',
                'message': 'Catastrophic regex backtracking can cause O(2^n) time on adversarial input'
            })

        known = self.detect_known_algorithm(code)
        if known.get('detected') and known.get('can_optimize'):
            issues.append({
                'line': 1,
                'type': 'performance',
                'severity': 'high',
                'message': f'{known["algorithm"]} detected ({known["complexity"]}) — can be optimized to {known.get("optimized_to", "better complexity")}'
            })

        graph = self.detect_graph_algorithm(code)
        if graph.get('detected') and graph.get('can_optimize'):
            issues.append({
                'line': 1,
                'type': 'performance',
                'severity': 'medium',
                'message': f'{graph["algorithm"]} ({graph["complexity"]}) — {graph.get("note", "")}'
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
        for loop in loops:
            if loop['children']:
                linear_children = [c for c in loop['children'] if c['type'] == 'linear']
                if loop['type'] == 'linear' and linear_children:
                    issues.append({
                        'line': self._find_loop_line(loop['header'], lines),
                        'type': 'performance',
                        'severity': 'high',
                        'message': 'Nested linear loops — causes O(n²) or worse. Use hash map to reduce to O(n).'
                    })
                self._check_nested_loop_issues(loop['children'], issues, lines, depth+1)

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

        # Graph algorithm optimizations
        if graph and graph.get('can_optimize'):
            optimizations.append({
                'title': f'Optimize {graph["algorithm"]} — {graph["complexity"]} → {graph.get("optimized_to", "better")}',
                'problem': f'Current algorithm: {graph["algorithm"]} runs at {graph["complexity"]}',
                'solution': graph.get('note', ''),
                'complexity_before': graph['complexity'],
                'complexity_after': graph.get('optimized_to', 'better'),
                'example': self._get_graph_optimization_example(graph, language)
            })

        # Known algorithm optimizations
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

        # Exponential recursion
        if recursion and recursion.get('type') == 'exponential':
            optimizations.append({
                'title': f'Add Memoization — {recursion["complexity"]} → O(n)',
                'problem': f'Exponential recursion with {recursion["branches"]} branches per call',
                'solution': 'Cache results of subproblems to avoid recomputation',
                'complexity_before': recursion['complexity'],
                'complexity_after': 'O(n) or O(n × target)',
                'example': self._get_memo_example(code, recursion, language)
            })

        # Nested loops
        if complexity == 'O(n²)' and not graph and not known:
            optimizations.append({
                'title': 'Replace Nested Loops with Hash Map — O(n²) → O(n)',
                'problem': 'Nested linear loops check every pair — quadratic time',
                'solution': 'Use a hash map to store and look up values in O(1)',
                'complexity_before': 'O(n²)',
                'complexity_after': 'O(n)',
                'example': self._get_hashmap_example(language)
            })

        if complexity == 'O(n³)':
            optimizations.append({
                'title': 'Reduce Triple Loops — O(n³) → O(n²)',
                'problem': 'Triple nested loops are extremely slow',
                'solution': 'Fix outer two loops, use hash set for third lookup',
                'complexity_before': 'O(n³)',
                'complexity_after': 'O(n²)',
                'example': self._get_triple_loop_example(language)
            })

        return optimizations

    def _get_graph_optimization_example(self, graph, language):
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
        if 'Generator recursion' in known['algorithm']:
            return self._get_generator_memo_example(language)
        if 'Bubble' in known['algorithm'] or 'Selection' in known['algorithm'] or 'Insertion' in known['algorithm']:
            if language == 'python':
                return '''# Replace with built-in sort — O(n log n) Tim Sort:
arr = [5, 3, 1, 4, 2]
arr.sort()  # In-place O(n log n)
# or
sorted_arr = sorted(arr)  # Returns new list O(n log n)'''
            elif language == 'javascript':
                return '''// Replace with built-in sort — O(n log n):
arr.sort((a, b) => a - b);  // Ascending
arr.sort((a, b) => b - a);  // Descending'''
            elif language == 'java':
                return '''// Replace with Arrays.sort — O(n log n):
Arrays.sort(arr);  // For primitives
Collections.sort(list);  // For objects'''
        return '// Use a more efficient algorithm.'

    def _get_generator_memo_example(self, language):
        return '''// O(2^n) -> O(n) with memoization:
function genMemo(n, memo = new Map()) {
    if (n <= 1) return 1;
    if (memo.has(n)) return memo.get(n);
    const result = genMemo(n - 1, memo) + genMemo(Math.floor(n / 2), memo);
    memo.set(n, result);
    return result;
}

function solution(n) {
    return genMemo(n);
}'''

    def _get_memo_example(self, code, recursion, language):
        name = recursion.get('func_name', 'func')
        if language == 'python':
            return f'''from functools import lru_cache

# Add @lru_cache decorator for automatic memoization:
@lru_cache(maxsize=None)
def {name}(arr, target, index=0):
    if target == 0: return True
    if index >= len(arr): return False
    include = {name}(arr, target - arr[index], index + 1)
    exclude = {name}(arr, target, index + 1)
    return include or exclude

# Note: Convert list to tuple when calling:
# {name}(tuple(arr), target)
# Complexity: O(2ⁿ) → O(n × target)'''
        elif language == 'javascript':
            return f'''// Add memo object for memoization:
function {name}(arr, target, index = 0, memo = {{}}) {{
    const key = `${{index}}-${{target}}`;
    if (key in memo) return memo[key];
    if (target === 0) return true;
    if (index >= arr.length) return false;
    const include = {name}(arr, target - arr[index], index + 1, memo);
    const exclude = {name}(arr, target, index + 1, memo);
    memo[key] = include || exclude;
    return memo[key];
}}
// Complexity: O(2ⁿ) → O(n × target)'''
        return '// Add memoization to cache subproblem results.'

    def _get_hashmap_example(self, language):
        if language == 'python':
            return '''# Instead of O(n²) nested loops:
# for i in range(n):
#     for j in range(i+1, n):
#         if arr[i] + arr[j] == target: ...

# Use O(n) hash map:
def twoSum(arr, target):
    seen = {}
    for i, num in enumerate(arr):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
# Time: O(n²) → O(n)'''
        elif language == 'javascript':
            return '''// Instead of O(n²) nested loops:
// for (let i=0; i<n; i++)
//   for (let j=i+1; j<n; j++)
//     if (arr[i]+arr[j]===target) ...

// Use O(n) hash map:
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

    def _get_triple_loop_example(self, language):
        if language == 'python':
            return '''# Instead of O(n³):
# for i in range(n):
#   for j in range(i+1, n):
#     for k in range(j+1, n):
#       if arr[i]+arr[j]+arr[k]==target: ...

# Use O(n²) with hash set:
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
    # TRANSFORMED CODE — KEY NEW FEATURE
    # ─────────────────────────────────────────────

    def generate_transformed_code(self, code, language, time_result):
        """
        Generates the actual transformed version of the user's code
        with lower time complexity where possible.
        """
        complexity = time_result['complexity']
        recursion = time_result.get('recursion')
        known = time_result.get('known')
        graph = time_result.get('graph')

        # Already optimal
        if complexity in ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)']:
            if not (known and known.get('can_optimize')) and not (graph and graph.get('can_optimize')):
                return {
                    'available': False,
                    'reason': f'Your code is already at {complexity} — no transformation needed.',
                    'complexity_before': complexity,
                    'complexity_after': complexity,
                    'code': None
                }

        if known and 'Generator recursion' in known.get('algorithm', ''):
            return {
                'available': True,
                'complexity_before': known['complexity'],
                'complexity_after': known.get('optimized_to', 'O(n)'),
                'description': 'Replaced generator recursion with a memoized plain function',
                'code': self._get_generator_memo_example(language)
            }

        # Exponential recursion → memoized version
        if recursion and recursion.get('type') == 'exponential':
            transformed = self._transform_recursive_to_memo(code, recursion, language)
            if transformed:
                return {
                    'available': True,
                    'complexity_before': recursion['complexity'],
                    'complexity_after': 'O(n × subproblems)',
                    'description': 'Added memoization to eliminate redundant recursive calls',
                    'code': transformed
                }

        # Bubble/Selection/Insertion sort → built-in sort
        if known and known.get('can_optimize') and known['algorithm'] in [
            'Bubble Sort', 'Selection Sort', 'Insertion Sort'
        ]:
            transformed = self._transform_sort_to_builtin(code, language)
            if transformed:
                return {
                    'available': True,
                    'complexity_before': known['complexity'],
                    'complexity_after': 'O(n log n)',
                    'description': f'Replaced {known["algorithm"]} with built-in O(n log n) sort',
                    'code': transformed
                }

        # Bellman-Ford → Dijkstra
        if graph and graph.get('can_optimize') and 'Bellman' in graph.get('algorithm', ''):
            return {
                'available': True,
                'complexity_before': graph['complexity'],
                'complexity_after': 'O((V+E) log V)',
                'description': 'Replace Bellman-Ford with Dijkstra for non-negative weights',
                'code': self._get_dijkstra_template(language)
            }

        # Generic: no specific transform available
        return {
            'available': False,
            'reason': 'Automatic transformation not available for this pattern. See optimizations above for manual guidance.',
            'complexity_before': complexity,
            'complexity_after': 'varies',
            'code': None
        }

    def _transform_recursive_to_memo(self, code, recursion, language):
        """
        Automatically adds memoization to exponential recursive functions.
        """
        func_name = recursion.get('func_name', '')
        if not func_name:
            return None

        if language == 'python':
            lines = code.split('\n')
            new_lines = []
            added_import = False
            for line in lines:
                # Add import at top
                if not added_import and (line.strip().startswith('def ') or line.strip().startswith('import') or line.strip().startswith('from')):
                    if 'lru_cache' not in code:
                        new_lines.append('from functools import lru_cache')
                        new_lines.append('')
                    added_import = True

                # Add decorator before function
                if re.match(rf'\s*def\s+{func_name}\s*\(', line):
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + '@lru_cache(maxsize=None)')

                new_lines.append(line)

            new_lines.append('')
            new_lines.append(f'# NOTE: Convert list arguments to tuple when calling:')
            new_lines.append(f'# {func_name}(tuple(arr), target)')
            new_lines.append(f'# Complexity improved: {recursion["complexity"]} → O(n × subproblems)')
            return '\n'.join(new_lines)

        elif language == 'javascript':
            lines = code.split('\n')
            new_lines = []
            func_found = False
            for i, line in enumerate(lines):
                if re.match(rf'\s*function\s+{func_name}\s*\(', line) and not func_found:
                    func_found = True
                    # Add memo parameter if not present
                    modified = re.sub(
                        rf'(function\s+{func_name}\s*\()([^)]*)\)',
                        lambda m: m.group(1) + (m.group(2).rstrip() + (', ' if m.group(2).strip() else '') + 'memo = {}') + ')',
                        line
                    )
                    new_lines.append(modified)
                    # Add memo check at start of function body
                    new_lines.append('  const _key = JSON.stringify(Array.from(arguments).slice(0, -1));')
                    new_lines.append('  if (_key in memo) return memo[_key];')
                    continue
                # Before return statements, add memo caching
                if func_found and re.search(r'\breturn\b', line):
                    indent = len(line) - len(line.lstrip())
                    ret_val = re.search(r'return\s+(.+);', line)
                    if ret_val:
                        new_lines.append(' ' * indent + f'const _result = {ret_val.group(1)};')
                        new_lines.append(' ' * indent + 'memo[_key] = _result;')
                        new_lines.append(' ' * indent + 'return _result;')
                        continue
                new_lines.append(line)

            new_lines.append('')
            new_lines.append(f'// Complexity improved: {recursion["complexity"]} → O(n × subproblems)')
            return '\n'.join(new_lines)

        return None

    def _transform_sort_to_builtin(self, code, language):
        """
        Replaces bubble/selection/insertion sort with built-in sort.
        """
        if language == 'python':
            return f'''# Optimized version using built-in Timsort — O(n log n):
def sort_array(arr):
    return sorted(arr)  # Returns new sorted list

# Or in-place:
def sort_array_inplace(arr):
    arr.sort()  # Modifies original list
    return arr

# Both run at O(n log n) — same result, much faster than manual sort algorithms
# Original complexity: O(n²) → New complexity: O(n log n)'''

        elif language == 'javascript':
            return '''// Optimized version using built-in sort — O(n log n):
function sortArray(arr) {
    return [...arr].sort((a, b) => a - b); // New sorted array
}

// Or in-place:
function sortArrayInPlace(arr) {
    arr.sort((a, b) => a - b); // Modifies original
    return arr;
}

// Both run at O(n log n) — faster than manual sort algorithms
// Original complexity: O(n²) → New complexity: O(n log n)'''

        elif language == 'java':
            return '''// Optimized version using Arrays.sort — O(n log n):
import java.util.Arrays;

public static int[] sortArray(int[] arr) {
    int[] copy = Arrays.copyOf(arr, arr.length);
    Arrays.sort(copy); // O(n log n) dual-pivot quicksort
    return copy;
}

// Original complexity: O(n²) → New complexity: O(n log n)'''

        return None

    def _get_dijkstra_template(self, language):
        if language == 'python':
            return '''import heapq

# Dijkstra — O((V+E) log V) replacing Bellman-Ford O(V×E):
def dijkstra(graph, source):
    """
    graph: dict of {node: [(neighbor, weight), ...]}
    source: starting node
    """
    dist = {node: float('inf') for node in graph}
    dist[source] = 0
    pq = [(0, source)]  # (distance, node)

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue  # Skip outdated entries
        for v, weight in graph[u]:
            new_dist = dist[u] + weight
            if new_dist < dist[v]:
                dist[v] = new_dist
                heapq.heappush(pq, (new_dist, v))

    return dist

# Complexity: O(V×E) → O((V+E) log V)
# Note: Only works for non-negative edge weights'''
        elif language == 'java':
            return '''import java.util.*;

// Dijkstra — O((V+E) log V) replacing Bellman-Ford:
public static int[] dijkstra(List<List<int[]>> graph, int source) {
    int n = graph.size();
    int[] dist = new int[n];
    Arrays.fill(dist, Integer.MAX_VALUE);
    dist[source] = 0;

    PriorityQueue<int[]> pq = new PriorityQueue<>(
        Comparator.comparingInt(a -> a[1])
    );
    pq.offer(new int[]{source, 0});

    while (!pq.isEmpty()) {
        int[] curr = pq.poll();
        int node = curr[0], d = curr[1];
        if (d > dist[node]) continue;
        for (int[] edge : graph.get(node)) {
            int next = edge[0], weight = edge[1];
            if (dist[node] + weight < dist[next]) {
                dist[next] = dist[node] + weight;
                pq.offer(new int[]{next, dist[next]});
            }
        }
    }
    return dist;
}
// Complexity: O(V×E) → O((V+E) log V)'''
        return '// Replace with Dijkstra algorithm for better performance.'

    # ─────────────────────────────────────────────
    # SUGGESTIONS
    # ─────────────────────────────────────────────

    def generate_suggestions(self, result):
        suggestions = []
        tc = result['time_complexity']
        sc = result['space_complexity']
        issues = result['issues']
        optimizations = result['optimizations']
        transformed = result.get('transformed_code', {})

        complexity_messages = {
            'O(1)':             '✅ Excellent! Constant time — as efficient as possible.',
            'O(log n)':         '✅ Great! Logarithmic time — scales very well.',
            'O(n)':             '✅ Good! Linear time — efficient for most use cases.',
            'O(n log n)':       '✅ Good! Optimal for comparison-based sorting.',
            'O(n log² n)':      '⚠️ Fair. Slightly above linearithmic — acceptable for most cases.',
            'O(n²)':            '⚠️ Warning! Quadratic — slow for large inputs (n > 10,000).',
            'O(n³)':            '🔴 Critical! Cubic — extremely slow for n > 1,000.',
            'O(2ⁿ)':            '🔴 Critical! Exponential — times out for n > 30. Optimize immediately.',
            'O(3ⁿ)':            '🔴 Critical! Exponential — times out for n > 20. Optimize immediately.',
            'O((V + E) log V)': '✅ Optimal for graph shortest path with priority queue.',
            'O(V + E)':         '✅ Optimal graph traversal complexity.',
            'O(V × E)':         '⚠️ Can be improved — consider Dijkstra if no negative weights.',
            'O(V³)':            '⚠️ Cubic graph complexity — use Dijkstra per vertex for sparse graphs.',
            'O(n log n) average, O(n²) worst': '⚠️ Worst case is O(n²) — use randomized pivot or Merge Sort.',
        }

        complexity_messages.update({
            'O(n² log n)': 'Heavy. Quadratic work is repeated across logarithmic steps.',
            'O(n³ log n)': 'Critical. Sorting is repeated inside nested loops.',
            'O(n * n!)': 'Critical. Factorial growth is only practical for very small n.',
            'O(n * 2^n)': 'Critical. The code generates exponentially many outputs and copies up to n items per output.',
            'O((log n)!)': 'Critical. The recursive work grows quasi-polynomially because each level creates a logarithmic number of subcalls.',
            'O(2^n)': 'Critical. Exponential recursion times out quickly without memoization.',
            'O(3^n)': 'Critical. Exponential recursion times out quickly without memoization.',
        })

        msg = complexity_messages.get(tc)
        if msg:
            suggestions.append(msg)

        if sc == 'O(n²)':
            suggestions.append('⚠️ High memory O(n²) — try in-place algorithms or rolling arrays.')
        elif sc == 'O(1)':
            suggestions.append('✅ Constant space — memory usage is optimal.')

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
            'O(1)': 0, 'O(log n)': 0, 'O(log² n)': 0.5,
            'O(n)': 1, 'O(n log n)': 2, 'O(n log² n)': 2.5,
            'O(n²)': 4, 'O(n² log n)': 5, 'O(n³)': 7,
            'O(2ⁿ)': 8, 'O(3ⁿ)': 9,
            'O((V + E) log V)': 1, 'O(V + E)': 0,
            'O(V × E)': 4, 'O(V³)': 6,
            'O(n log n) average, O(n²) worst': 3,
        }
        deductions.update({
            'O(n² log n)': 5,
            'O(n³ log n)': 8,
            'O(n * n!)': 9,
            'O(n * 2^n)': 8.5,
            'O((log n)!)': 7,
            'O(2^n)': 8,
            'O(3^n)': 9,
        })

        score -= deductions.get(result['time_complexity'], 2)

        if result['space_complexity'] == 'O(n²)': score -= 2
        elif result['space_complexity'] == 'O(n)': score -= 0.5

        for issue in result['issues']:
            if issue['severity'] == 'high': score -= 1.5
            elif issue['severity'] == 'medium': score -= 0.5
            elif issue['severity'] == 'low': score -= 0.2

        return max(1, round(score))
