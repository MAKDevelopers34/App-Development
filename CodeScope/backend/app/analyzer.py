import ast
import re

class CodeAnalyzer:
    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'java', 'cpp', 'c']

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

    def analyze(self, code, filename=None):
        language = self.detect_language(code, filename)
        
        result = {
            'language': language,
            'time_complexity': self.detect_time_complexity(code, language),
            'space_complexity': self.detect_space_complexity(code, language),
            'issues': self.detect_issues(code, language),
            'suggestions': [],
            'rating': 0,
            'lines_of_code': len(code.strip().split('\n'))
        }
        
        result['suggestions'] = self.generate_suggestions(result['issues'])
        result['rating'] = self.calculate_rating(result)
        
        return result

    def detect_time_complexity(self, code, language):
        lines = code.split('\n')
        max_nesting = 0
        current_nesting = 0
        has_recursion = False
        has_binary_search = False
        has_sorting = False

        # Check for recursion
        func_names = re.findall(r'def\s+(\w+)', code)
        for name in func_names:
            if len(re.findall(rf'\b{name}\s*\(', code)) > 1:
                has_recursion = True

        # Check for sorting
        sort_patterns = ['sort(', 'sorted(', 'Arrays.sort', 'Collections.sort', '.sort()']
        for pattern in sort_patterns:
            if pattern in code:
                has_sorting = True

        # Check for binary search
        if 'binary_search' in code or 'bisect' in code or 'mid' in code.lower():
            has_binary_search = True

        # Count loop nesting
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(kw) for kw in ['for ', 'while ']):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            if stripped == '' or stripped.startswith('def ') or stripped.startswith('class '):
                current_nesting = 0

        # Determine complexity
        if has_recursion and has_sorting:
            return 'O(n log n)'
        elif max_nesting >= 3:
            return 'O(n³)'
        elif max_nesting == 2:
            return 'O(n²)'
        elif has_sorting:
            return 'O(n log n)'
        elif has_binary_search:
            return 'O(log n)'
        elif max_nesting == 1:
            return 'O(n)'
        else:
            return 'O(1)'

    def detect_space_complexity(self, code, language):
        has_2d_array = bool(re.search(r'\[\s*\[', code))
        has_array = bool(re.search(r'\[\s*\]|\blist\b|\bArray\b|\[\]', code))
        has_dict = bool(re.search(r'\{\}|\bdict\b|\bMap\b|\bHashMap\b', code))
        has_recursion = bool(re.search(r'def\s+(\w+).*\n.*\1\s*\(', code, re.DOTALL))

        if has_2d_array:
            return 'O(n²)'
        elif has_recursion:
            return 'O(n)'
        elif has_array or has_dict:
            return 'O(n)'
        else:
            return 'O(1)'

    def detect_issues(self, code, language):
        issues = []
        lines = code.split('\n')
        nesting_level = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Nested loops
            if any(stripped.startswith(kw) for kw in ['for ', 'while ']):
                nesting_level += 1
                if nesting_level >= 2:
                    issues.append({
                        'line': i,
                        'type': 'performance',
                        'severity': 'high',
                        'message': f'Nested loop detected at line {i} — this causes O(n²) or worse complexity'
                    })
            elif stripped == '':
                nesting_level = 0

            # Long functions
            if stripped.startswith('def ') or stripped.startswith('function '):
                func_start = i
                func_lines = 0
                for j in range(i, min(i + 100, len(lines))):
                    func_lines += 1
                if func_lines > 50:
                    issues.append({
                        'line': i,
                        'type': 'maintainability',
                        'severity': 'medium',
                        'message': f'Function at line {i} is very long — consider breaking it into smaller functions'
                    })

            # Hardcoded values
            if re.search(r'==\s*\d{3,}|>=\s*\d{3,}', stripped):
                issues.append({
                    'line': i,
                    'type': 'maintainability',
                    'severity': 'low',
                    'message': f'Hardcoded number at line {i} — use a named constant instead'
                })

            # Global variables
            if stripped.startswith('global '):
                issues.append({
                    'line': i,
                    'type': 'design',
                    'severity': 'medium',
                    'message': f'Global variable used at line {i} — avoid globals for cleaner code'
                })

        return issues

    def generate_suggestions(self, issues):
        suggestions = []
        seen = set()

        for issue in issues:
            if 'Nested loop' in issue['message'] and 'nested_loop' not in seen:
                suggestions.append('Replace nested loops with a hash map (dictionary) to reduce complexity from O(n²) to O(n)')
                seen.add('nested_loop')
            if 'long' in issue['message'].lower() and 'long_func' not in seen:
                suggestions.append('Break large functions into smaller reusable functions for better readability')
                seen.add('long_func')
            if 'Hardcoded' in issue['message'] and 'hardcode' not in seen:
                suggestions.append('Use named constants at the top of your file instead of hardcoded numbers')
                seen.add('hardcode')
            if 'Global' in issue['message'] and 'global' not in seen:
                suggestions.append('Pass variables as function parameters instead of using global variables')
                seen.add('global')

        if not suggestions:
            suggestions.append('Great code! No major performance issues detected.')

        return suggestions

    def calculate_rating(self, result):
        score = 10

        # Deduct for time complexity
        complexity_deductions = {
            'O(1)': 0,
            'O(log n)': 0,
            'O(n)': 1,
            'O(n log n)': 2,
            'O(n²)': 4,
            'O(n³)': 6
        }
        score -= complexity_deductions.get(result['time_complexity'], 2)

        # Deduct for issues
        for issue in result['issues']:
            if issue['severity'] == 'high':
                score -= 2
            elif issue['severity'] == 'medium':
                score -= 1
            elif issue['severity'] == 'low':
                score -= 0.5

        return max(1, round(score))