import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
GROK_API_KEY = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY', '')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-3-mini')
GROK_API_BASE = os.getenv('GROK_API_BASE', 'https://api.x.ai/v1/chat/completions')


def get_ai_explanation(analysis_result, code, language):
    """
    Uses Groq API to generate intelligent natural language
    explanation of the analysis results.
    Falls back to rule-based explanation if API unavailable.
    """
    if GROQ_API_KEY:
        try:
            return _get_groq_explanation(analysis_result, code, language)
        except Exception as e:
            print(f'Groq API error: {e}')
    if GROK_API_KEY:
        try:
            return _get_grok_explanation(analysis_result, code, language)
        except Exception as e:
            print(f'Grok API error: {e}')
    return _get_fallback_explanation(analysis_result, code, language)


def _get_groq_explanation(analysis_result, code, language):
    """
    Calls Groq API for intelligent explanation.
    """
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    prompt = _build_ai_prompt(analysis_result, code, language)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=800
    )

    return _parse_ai_json(response.choices[0].message.content)


def _get_grok_explanation(analysis_result, code, language):
    """
    Calls xAI Grok-compatible chat completions API.
    """
    response = requests.post(
        GROK_API_BASE,
        headers={
            'Authorization': f'Bearer {GROK_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': GROK_MODEL,
            'messages': [{'role': 'user', 'content': _build_ai_prompt(analysis_result, code, language)}],
            'temperature': 0.25,
            'max_tokens': 800,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload['choices'][0]['message']['content']
    return _parse_ai_json(content)


def _build_ai_prompt(analysis_result, code, language):
    input_schema = analysis_result.get('input_schema') or {}
    provided_inputs = analysis_result.get('provided_inputs')
    concrete = analysis_result.get('concrete_analysis')
    optimizations = analysis_result.get('optimizations') or []
    issues = analysis_result.get('issues') or []

    return f"""You are CodeScope's algorithm teacher. Explain this {language} code's complexity result for a beginner, but stay mathematically accurate.

CODE:
```{language}
{code[:3000]}
```

ANALYSIS RESULTS:
- Time Complexity: {analysis_result.get('time_complexity')}
- Space Complexity: {analysis_result.get('space_complexity')}
- Performance Rating: {analysis_result.get('rating')}/10
- Issues Found: {len(issues)}
- Reason: {analysis_result.get('time_complexity_reason', '')}
- Detected Input Schema: {json.dumps(input_schema, ensure_ascii=False)}
- User Provided Inputs: {json.dumps(provided_inputs, ensure_ascii=False) if provided_inputs else 'None'}
- Concrete Analysis: {json.dumps(concrete, ensure_ascii=False) if concrete else 'None'}
- Top Optimization Data: {json.dumps(optimizations[:2], ensure_ascii=False)}

Please provide:
1. Why this exact time complexity was chosen.
2. A simple real-world analogy.
3. What happens as input size grows; use provided concrete inputs only if they are relevant.
4. The single most useful optimization.

Rules:
- Treat the analyzer's detected reason as primary evidence.
- If the reason is a special sum such as sum_i log(n/i), explain that tighter bound instead of saying nested loops always multiply.
- If the user-provided values are fixed inputs, say fixed inputs are concrete examples; symbolic Big-O still describes variable input growth.
- If recursion, explain the recursive call tree and do not describe it as a loop problem.
- If sorting, graph traversal, DP, regex, or backtracking is the cause, name that pattern.
- Do not invent runtime measurements or execute the code.
- Keep each JSON value to 1-3 short beginner-friendly sentences.
- Return valid JSON only.

Format as JSON with keys: why_this_complexity, real_world_analogy, performance_impact, top_optimization"""


def _parse_ai_json(content):
    content = re.sub(r'```json|```', '', content or '').strip()
    try:
        return json.loads(content)
    except Exception:
        return {'why_this_complexity': content, 'real_world_analogy': '',
                'performance_impact': '', 'top_optimization': ''}


def _get_fallback_explanation(analysis_result, code, language):
    """
    Rule-based explanation when Groq API is not available.
    """
    return _build_clear_fallback_explanation(analysis_result, code, language)


def _normalize_complexity(value):
    text = str(value or 'O(n)')
    return (
        text
        .replace('\u00b2', '^2')
        .replace('\u00b3', '^3')
        .replace('\u207f', '^n')
        .replace('\u00d7', 'x')
    )


def _first_optimization(analysis_result, fallback):
    optimizations = analysis_result.get('optimizations') or []
    if not isinstance(optimizations, list) or not optimizations:
        return fallback

    first = optimizations[0]
    if not isinstance(first, dict):
        return fallback

    solution = str(first.get('solution') or first.get('title') or fallback).rstrip('.')
    before = first.get('complexity_before')
    after = first.get('complexity_after')
    if before and after:
        return f"{solution}. This can improve the main cost from {before} to {after}."
    return solution


def _build_clear_fallback_explanation(analysis_result, code, language):
    tc = analysis_result.get('time_complexity', 'O(n)')
    reason = (analysis_result.get('time_complexity_reason') or '').strip()
    norm_tc = _normalize_complexity(tc)
    reason_lower = reason.lower()
    code_lower = code.lower()

    if norm_tc == 'O((log n)!)':
        return {
            'why_this_complexity': (
                "This is quasi-polynomial because the recursive function does not make just one half-size recursive call. "
                "At each level it makes about log n calls on n/2, so the call tree multiplies by log n, then log(n/2), and so on."
            ),
            'real_world_analogy': (
                "It is like splitting a task in half, but asking a shrinking committee to repeat the split at every level."
            ),
            'performance_impact': (
                "This grows faster than any fixed polynomial such as O(n^2), but slower than ordinary exponential O(2^n). "
                "It can still become impractical for large inputs."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Avoid putting repeated recursive calls inside a logarithmic loop, or cache repeated subproblems when valid."
            )
        }

    if 'recursive calls per level' in reason_lower or norm_tc in ('O(2^n)', 'O(3^n)'):
        match = re.search(r'(\d+)\s+recursive calls per level', reason_lower)
        branch_count = match.group(1) if match else ('3' if norm_tc == 'O(3^n)' else '2')
        return {
            'why_this_complexity': (
                f"This is exponential because the function creates {branch_count} new recursive calls at each level. "
                f"Those calls create more calls again, so the work forms a growing call tree instead of one simple pass. "
                f"With about n levels, that becomes {tc}."
            ),
            'real_world_analogy': (
                f"Imagine one task splitting into {branch_count} smaller tasks, and each of those splits again. "
                "The number of tasks grows very quickly after only a few levels."
            ),
            'performance_impact': (
                "For O(2^n), n=10 is about 1,024 calls, n=20 is about 1,048,576 calls, and n=30 is about 1 billion calls. "
                "That is why this type of recursion becomes slow very fast."
            ),
            'top_optimization': (
                "Use memoization or dynamic programming so each repeated input is solved once and then reused. "
                "For Fibonacci-style recursion, this reduces the time from O(2^n) to O(n)."
            )
        }

    if 'memoized recursion' in reason_lower or ('memo' in code_lower and norm_tc == 'O(n)'):
        return {
            'why_this_complexity': (
                f"This is {tc} because memoization saves each result after it is calculated. "
                "When the same recursive input appears again, the code reuses the saved value instead of recomputing the whole branch."
            ),
            'real_world_analogy': (
                "It is like writing each solved math answer in a notebook. "
                "When the same question comes back, you read the answer instead of solving it again."
            ),
            'performance_impact': (
                "The code grows roughly one step per new input value. "
                "n=1,000 needs about 1,000 useful states instead of an exponential number of repeated calls."
            ),
            'top_optimization': "This is already the right optimization for repeated recursion. You can still check memory use if n becomes very large."
        }

    if norm_tc == 'O(n * n!)':
        return {
            'why_this_complexity': (
                "This is factorial because the code generates permutations or tries every ordering. "
                "There are n! possible orders, and building or copying each result can add another n factor."
            ),
            'real_world_analogy': (
                "It is like arranging people in every possible line order. "
                "Adding one more person multiplies the number of arrangements."
            ),
            'performance_impact': (
                "n=5 has 120 orders, n=8 has 40,320, and n=10 has 3,628,800. "
                "This is only practical for small inputs unless you can avoid generating every result."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "If you do not need every permutation, prune invalid branches early or generate results lazily."
            )
        }

    if norm_tc == 'O(n * 2^n)':
        return {
            'why_this_complexity': (
                "This is O(n * 2^n) because the code generates every subset or power-set result. "
                "There are 2^n subsets, and building or copying those lists contributes a total n factor."
            ),
            'real_world_analogy': (
                "It is like listing every possible team from n people, then writing out the names on each team."
            ),
            'performance_impact': (
                "n=10 has 1,024 subsets, n=20 has 1,048,576 subsets, and the copied output size grows with n too. "
                "This becomes large quickly because the output itself is exponential."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "If every subset must be returned, this cost is unavoidable. Stream or yield subsets to reduce peak memory."
            )
        }

    if norm_tc in ('O(n^2 log n)', 'O(n^3 log n)'):
        if 'recursive' in reason_lower or 'call-chain' in reason_lower:
            return {
                'why_this_complexity': (
                    f"This is {tc} because logarithmic driver work repeatedly calls a heavier helper. "
                    "The helper contains nested loop work, so the quadratic cost is multiplied by the outer log n repetitions."
                ),
                'real_world_analogy': (
                    "It is like doing a large pair-checking task several times, but the number of repeats only doubles/halves with the input size."
                ),
                'performance_impact': (
                    "The quadratic part dominates each pass, and the logarithmic driver adds extra repeated passes. "
                    "This is slower than O(n^2), but much better than exponential growth."
                ),
                'top_optimization': _first_optimization(
                    analysis_result,
                    "Reduce the nested loop work in the helper, or avoid calling the helper on every logarithmic driver step when possible."
                )
            }
        return {
            'why_this_complexity': (
                f"This is {tc} because sorting or another log n operation is repeated inside loop work. "
                "The loop decides how many times sorting runs, and the sort adds the log n factor."
            ),
            'real_world_analogy': (
                "It is like re-sorting the same stack of papers again and again while checking many items. "
                "The repeated sorting is the expensive part."
            ),
            'performance_impact': (
                "When n grows, the repeated loop work and sorting cost multiply together. "
                "This can become slow much earlier than a single O(n log n) sort."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Move sorting outside repeated loops when possible, or use a data structure that maintains order incrementally."
            )
        }

    if norm_tc == 'O(n^3)':
        return {
            'why_this_complexity': (
                "This is cubic because three input-sized loops are nested or the code checks triples of values. "
                "For each first choice, it tries many second choices, then many third choices."
            ),
            'real_world_analogy': (
                "It is like testing every possible group of three people from a room. "
                "The combinations grow extremely fast as the room gets bigger."
            ),
            'performance_impact': (
                "n=100 can mean about 1,000,000 checks, and n=1,000 can mean about 1,000,000,000 checks. "
                "Large inputs will feel very slow."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Try fixing fewer values and using a hash set, two pointers, or preprocessing to remove one loop."
            )
        }

    if norm_tc == 'O(n^2)':
        return {
            'why_this_complexity': (
                "This is quadratic because the code does input-sized work inside another input-sized loop. "
                "That means many pairs of items are compared or processed."
            ),
            'real_world_analogy': (
                "It is like comparing every person in a room with every other person. "
                "Twice as many people creates about four times as many comparisons."
            ),
            'performance_impact': (
                "n=100 is about 10,000 operations, while n=10,000 is about 100,000,000. "
                "It is fine for small inputs but risky for large ones."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Look for a hash map, set, sorting plus two pointers, or preprocessing step that can remove the inner loop."
            )
        }

    if norm_tc == 'O(n log n)':
        if 'sort' in reason_lower or 'sort' in code_lower:
            why = (
                "This is O(n log n) because the main cost is sorting. "
                "Comparison sorting repeatedly divides and orders the data, which adds the log n factor."
            )
            optimization = "For comparison sorting this is usually optimal. Only optimize if the input has a special property, such as small integer ranges."
        elif 'harmonic' in reason_lower:
            why = (
                "This is O(n log n) because the inner work shrinks in a harmonic pattern. "
                "The first passes do more work, later passes do less, and the total adds up to n log n."
            )
            optimization = "This pattern is usually acceptable. Check whether repeated work can be cached or skipped."
        elif 'geometric' in reason_lower:
            why = (
                "This is O(n log n) because one part grows by input size while another part grows by repeated doubling or halving. "
                "That creates linear work multiplied by a logarithmic number of steps."
            )
            optimization = "This is generally efficient. Focus on avoiding unnecessary work inside the repeated section."
        else:
            why = (
                "This is O(n log n) because the code combines input-sized work with a logarithmic step. "
                "That commonly happens in efficient sorting or divide-and-conquer algorithms."
            )
            optimization = "This is usually a good complexity for sorting and divide-and-conquer code."
        return {
            'why_this_complexity': why,
            'real_world_analogy': (
                "It is like organizing a large set by repeatedly splitting it into smaller groups, then combining the results."
            ),
            'performance_impact': (
                "n=1,000 is roughly 10,000 work units, while n=1,000,000 is roughly 20,000,000. "
                "It grows faster than O(n), but it is still very manageable."
            ),
            'top_optimization': _first_optimization(analysis_result, optimization)
        }

    if norm_tc == 'O(log n)':
        return {
            'why_this_complexity': (
                "This is logarithmic because the code reduces the remaining input by a large fraction each step, often by halving it. "
                "It does not need to inspect every item."
            ),
            'real_world_analogy': (
                "It is like guessing a number by always asking whether it is higher or lower than the middle."
            ),
            'performance_impact': (
                "n=1,000 takes about 10 steps, and n=1,000,000 takes about 20 steps. "
                "That is excellent growth."
            ),
            'top_optimization': "This is already highly efficient. Keep the input ordered if the algorithm depends on binary search."
        }

    if norm_tc == 'O(n)':
        return {
            'why_this_complexity': (
                "This is linear because the code does a constant amount of work for each input item. "
                "As the input grows, the work grows at the same rate."
            ),
            'real_world_analogy': (
                "It is like reading every page in a book once. "
                "A book with twice as many pages takes about twice as long."
            ),
            'performance_impact': (
                "n=1,000 means about 1,000 steps, and n=1,000,000 means about 1,000,000 steps. "
                "This is good for most real inputs."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "This is already efficient. You can still remove unnecessary work inside the loop."
            )
        }

    if norm_tc == 'O(1)':
        return {
            'why_this_complexity': (
                "This is constant time because the code performs a fixed amount of work. "
                "The number of operations does not grow with the input size."
            ),
            'real_world_analogy': (
                "It is like opening a saved bookmark directly. "
                "It takes the same kind of effort no matter how much other data exists."
            ),
            'performance_impact': (
                "n=100 and n=1,000,000 take about the same number of core steps. "
                "This is the best possible time complexity."
            ),
            'top_optimization': "No major time-complexity optimization is needed."
        }

    if norm_tc in ('O(V + E)', 'O((V + E) log V)', 'O(V x E)', 'O(V^3)'):
        return {
            'why_this_complexity': (
                f"This graph algorithm is {tc} because the input is measured by vertices V and edges E. "
                f"The detected pattern is: {reason or 'graph traversal or shortest-path processing'}."
            ),
            'real_world_analogy': (
                "It is like navigating a map: intersections are vertices and roads are edges. "
                "The work depends on how many places and connections must be checked."
            ),
            'performance_impact': (
                "Sparse graphs with fewer edges stay much faster than dense graphs with many connections. "
                "As E grows, graph algorithms can become expensive even if V does not grow much."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Use the graph algorithm that matches the problem constraints, such as BFS for unweighted paths or Dijkstra for non-negative weighted paths."
            )
        }

    return {
        'why_this_complexity': (
            f"The analyzer classified this code as {tc}. "
            f"It used this detected pattern as evidence: {reason or 'the structure of the loops, recursion, and library calls'}."
        ),
        'real_world_analogy': (
            "Think of the complexity as the speedometer for how quickly the work grows when the input becomes larger."
        ),
        'performance_impact': (
            f"With {tc}, larger inputs require more work according to that growth pattern. "
            "The exact runtime also depends on constants, hardware, and input shape."
        ),
        'top_optimization': _first_optimization(
            analysis_result,
            "Check the Optimizations and Issues sections for the most specific improvement for this code."
        )
    }


def _get_fallback_explanation_legacy(analysis_result, code, language):
    """
    Previous rule-based explanation kept for reference while the clearer
    fallback above drives the UI.
    """
    tc = analysis_result.get('time_complexity', 'O(n)')
    sc = analysis_result.get('space_complexity', 'O(1)')
    reason = analysis_result.get('time_complexity_reason', '')

    explanations = {
        'O(1)': {
            'why_this_complexity': 'This code runs in constant time — it performs a fixed number of operations regardless of input size. No loops or recursion that depend on input size were detected.',
            'real_world_analogy': 'Like looking up a word in a dictionary using its page number — you go directly there, no matter how big the dictionary is.',
            'performance_impact': 'n=100 → same speed as n=1,000,000. Input size has zero effect on performance.',
            'top_optimization': 'No optimization needed — this is already the best possible complexity.'
        },
        'O(log n)': {
            'why_this_complexity': 'This code halves the problem size on each step. A loop or recursion that doubles/halves its iterator was detected.',
            'real_world_analogy': 'Like finding a name in a phone book by opening the middle, deciding left or right, and repeating — you never read every page.',
            'performance_impact': 'n=1,000 → ~10 operations. n=1,000,000 → ~20 operations. Extremely efficient.',
            'top_optimization': 'Already highly optimized. No changes needed.'
        },
        'O(n)': {
            'why_this_complexity': 'This code visits each element exactly once. A single loop proportional to input size was detected.',
            'real_world_analogy': 'Like reading every page in a book once — the time taken scales directly with the number of pages.',
            'performance_impact': 'n=1,000 → 1,000 operations. n=1,000,000 → 1,000,000 operations. Scales linearly.',
            'top_optimization': 'Good complexity. Look for any unnecessary repeated work inside the loop to optimize constants.'
        },
        'O(n log n)': {
            'why_this_complexity': 'This code combines a linear pass with a logarithmic operation — typically seen in efficient sorting or divide-and-conquer algorithms.',
            'real_world_analogy': 'Like organizing a library by repeatedly splitting books into groups and sorting each group — efficient but not instant.',
            'performance_impact': 'n=1,000 → ~10,000 operations. n=1,000,000 → ~20,000,000 operations. Very manageable.',
            'top_optimization': 'This is optimal for comparison-based sorting. No major optimization needed.'
        },
        'O(n²)': {
            'why_this_complexity': 'Nested loops were detected — for every element, the code iterates through all elements again. This causes quadratic growth.',
            'real_world_analogy': 'Like comparing every person in a room with every other person — if there are 100 people, you make 10,000 comparisons.',
            'performance_impact': 'n=100 → 10,000 ops. n=1,000 → 1,000,000 ops. n=10,000 → will be very slow.',
            'top_optimization': 'Replace the inner loop with a hash map lookup (O(1)) to reduce overall complexity to O(n).'
        },
        'O(n³)': {
            'why_this_complexity': 'Triple nested loops detected — for every pair of elements, the code iterates all elements again.',
            'real_world_analogy': 'Like checking every combination of 3 people in a room — grows impossibly fast.',
            'performance_impact': 'n=100 → 1,000,000 ops. n=1,000 → 1,000,000,000 ops. Practically unusable for large inputs.',
            'top_optimization': 'Fix two outer loops and use a hash set for the third lookup to reduce to O(n²).'
        },
        'O(2ⁿ)': {
            'why_this_complexity': 'Exponential recursion detected — the function calls itself twice per level without caching results, causing the call tree to double at every level.',
            'real_world_analogy': 'Like a chain letter where each person sends it to 2 more people — starts small but grows uncontrollably fast.',
            'performance_impact': 'n=10 → 1,024 ops. n=30 → 1,073,741,824 ops. n=50 → will never finish.',
            'top_optimization': 'Add memoization (@lru_cache in Python, memo object in JS) to cache subproblem results. Reduces to O(n).'
        },
        'O((V + E) log V)': {
            'why_this_complexity': 'Dijkstra\'s algorithm detected — uses a priority queue to process each vertex and edge once with logarithmic heap operations.',
            'real_world_analogy': 'Like finding the fastest route on a map app — it smartly explores nearest locations first using a priority system.',
            'performance_impact': 'Efficient for sparse graphs. V=1,000, E=5,000 → very fast. Scales well with graph size.',
            'top_optimization': 'Already optimal for single-source shortest path with non-negative weights.'
        },
    }

    default = {
        'why_this_complexity': f'Analysis detected: {reason}. The complexity is {tc} based on the loop structure and algorithm pattern found in the code.',
        'real_world_analogy': 'The algorithm\'s growth rate determines how it handles larger inputs.',
        'performance_impact': f'With complexity {tc}, performance degrades as input size increases.',
        'top_optimization': 'Review the issues and optimizations sections for specific improvement suggestions.'
    }

    return explanations.get(tc, default)


def get_function_level_explanations(func_complexities, call_chain_report, language):
    """
    Generates per-function explanations for the call chain analysis.
    """
    explanations = []

    for func_name, complexity in func_complexities.items():
        chain_info = next(
            (r for r in call_chain_report if r['function'] == func_name), None)

        explanation = {
            'function': func_name,
            'complexity': complexity,
            'explanation': _explain_single_function(func_name, complexity, chain_info)
        }
        explanations.append(explanation)

    return explanations


def _explain_single_function(func_name, complexity, chain_info):
    base = f"Function '{func_name}' has {complexity} complexity"
    if chain_info:
        return (
            f"{base} on its own, but calls '{chain_info['chain']}' "
            f"which brings the effective complexity to "
            f"{chain_info['effective_complexity']}. "
            f"The bottleneck is in the called function, not this one."
        )
    normalized = _normalize_complexity(complexity)
    if normalized in ('O(2^n)', 'O(3^n)'):
        return (
            f"Function '{func_name}' is exponential because it makes multiple "
            "recursive calls that branch into more calls before reaching the base case."
        )
    if normalized == 'O(n * 2^n)':
        return (
            f"Function '{func_name}' generates exponentially many output values, "
            "and the total copied output size adds the extra n factor."
        )
    if normalized == 'O(n * n!)':
        return (
            f"Function '{func_name}' is factorial because it explores every "
            "possible ordering or permutation of the input."
        )
    if normalized in ('O(n^2)', 'O(n^3)'):
        return (
            f"Function '{func_name}' has {complexity} complexity because it "
            "uses nested input-sized work."
        )
    return f"{base}."
