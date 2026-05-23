import ast
import copy
import itertools
import os
import re
import json
import time
from contextvars import ContextVar
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
GROK_API_KEY = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY', '')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-3-mini')
GROK_API_BASE = os.getenv('GROK_API_BASE', 'https://api.x.ai/v1/chat/completions')
AI_EXPLAINER_PROVIDER = os.getenv('AI_EXPLAINER_PROVIDER', 'auto').lower()
AI_EXPLAINER_DEBUG = os.getenv('AI_EXPLAINER_DEBUG', '').lower() in ('1', 'true', 'yes')
try:
    AI_REQUEST_TIMEOUT_SECONDS = max(1.0, min(8.0, float(os.getenv('AI_REQUEST_TIMEOUT_SECONDS', '5'))))
except ValueError:
    AI_REQUEST_TIMEOUT_SECONDS = 5.0
try:
    AI_TOTAL_TIMEOUT_SECONDS = max(4.0, min(12.0, float(os.getenv('AI_TOTAL_TIMEOUT_SECONDS', '10'))))
except ValueError:
    AI_TOTAL_TIMEOUT_SECONDS = 10.0

_AI_DEADLINE = ContextVar('AI_DEADLINE', default=None)


def _log_ai_error(message):
    if AI_EXPLAINER_DEBUG:
        print(message)


def start_ai_budget(total_seconds=None):
    budget = AI_TOTAL_TIMEOUT_SECONDS if total_seconds is None else total_seconds
    return _AI_DEADLINE.set(time.monotonic() + max(1.0, float(budget)))


def reset_ai_budget(token):
    _AI_DEADLINE.reset(token)


def _remaining_ai_timeout():
    deadline = _AI_DEADLINE.get()
    if deadline is None:
        return AI_REQUEST_TIMEOUT_SECONDS

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return 0.0
    return min(AI_REQUEST_TIMEOUT_SECONDS, remaining)


def _groq_client(timeout=None):
    from groq import Groq
    return Groq(api_key=GROQ_API_KEY, timeout=timeout or AI_REQUEST_TIMEOUT_SECONDS)


def get_ai_explanation(analysis_result, code, language):
    """
    Uses the configured AI provider to generate intelligent natural language
    explanation of analyzer-owned results.
    Falls back to rule-based explanation if API unavailable.
    """
    try:
        prompt = _build_ai_prompt(analysis_result, code, language)
        ai_response = _call_ai_completion(prompt, max_tokens=1200, return_source=True)
        if isinstance(ai_response, tuple):
            content, provider = ai_response
        else:
            content, provider = ai_response, 'configured_ai'
        if content:
            parsed = _parse_ai_json(content)
            normalized = _normalize_ai_explanation_result(
                parsed,
                analysis_result,
                code,
                language,
                source=provider or 'configured_ai',
            )
            if normalized.get('available'):
                return normalized
    except Exception as e:
        _log_ai_error(f'AI explanation error: {e}')
    return _get_fallback_explanation(analysis_result, code, language)


def get_ai_optimized_code(analysis_result, code, language):
    """
    Ask the configured AI provider to rewrite the detected hot function/code only
    when CodeScope has already found a concrete lower-complexity optimization.
    The analyzer remains the source of truth for before/after complexity.
    """
    optimization = _select_ai_code_optimization(analysis_result)
    if not optimization:
        return {
            'available': False,
            'reason': 'No analyzer-approved lower-complexity rewrite target is available.',
            'source': 'analyzer_guard'
        }

    try:
        prompt = _build_ai_code_prompt(analysis_result, code, language, optimization)
        content = _call_ai_completion(prompt, max_tokens=1600)
        if content:
            parsed = _parse_ai_json(content)
            normalized = _normalize_ai_code_result(parsed, optimization)
            if normalized.get('available'):
                validation = _validate_ai_rewrite_complexity(
                    normalized.get('code', ''),
                    language,
                    normalized.get('complexity_before') or optimization.get('complexity_before'),
                    original_code=code,
                    optimization=optimization,
                )
                if validation.get('valid'):
                    normalized['complexity_after'] = validation.get('complexity') or normalized.get('complexity_after')
                    normalized['validation'] = validation
                    return normalized
    except Exception as e:
        _log_ai_error(f'AI optimized-code error: {e}')

    return {
        'available': False,
        'reason': 'The configured AI provider did not return a same-behavior lower-complexity rewrite, so no optimized code is shown.',
        'source': 'fallback'
    }


def enhance_optimizations_with_ai(analysis_result, code, language):
    """
    Ask AI to improve analyzer suggestions and independently inspect expensive
    functions for same-behavior lower-complexity rewrites.
    """
    optimizations = analysis_result.get('optimizations') or []
    if not isinstance(optimizations, list):
        optimizations = []

    discovery_targets = _expensive_function_targets(analysis_result)
    if not optimizations and not discovery_targets:
        return optimizations

    try:
        prompt = _build_ai_optimization_prompt(
            analysis_result, code, language, optimizations, discovery_targets
        )
        ai_response = _call_ai_completion(prompt, max_tokens=4000, return_source=True)
        if isinstance(ai_response, tuple):
            content, provider = ai_response
        else:
            content, provider = ai_response, 'configured_ai'
        if provider not in ('grok', 'groq'):
            return optimizations
        if content:
            parsed = _parse_ai_json(content)
            return _merge_ai_optimization_suggestions(
                optimizations,
                parsed,
                language=language,
                discovery_targets=discovery_targets,
                original_code=code,
                provider=provider,
            )
    except Exception as e:
        _log_ai_error(f'AI optimization-suggestion error: {e}')
    return optimizations


def _get_groq_explanation(analysis_result, code, language):
    """
    Calls Groq API for intelligent explanation.
    """
    timeout = _remaining_ai_timeout()
    if timeout <= 0:
        return None

    client = _groq_client(timeout)

    prompt = _build_ai_prompt(analysis_result, code, language)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=_ai_messages(prompt),
        temperature=0.3,
        max_tokens=800
    )

    return _parse_ai_json(response.choices[0].message.content)


def _get_grok_explanation(analysis_result, code, language):
    """
    Calls xAI Grok-compatible chat completions API.
    """
    timeout = _remaining_ai_timeout()
    if timeout <= 0:
        return None

    response = requests.post(
        GROK_API_BASE,
        headers={
            'Authorization': f'Bearer {GROK_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': GROK_MODEL,
            'messages': _ai_messages(_build_ai_prompt(analysis_result, code, language)),
            'temperature': 0.25,
            'max_tokens': 800,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload['choices'][0]['message']['content']
    return _parse_ai_json(content)


def _build_ai_prompt(analysis_result, code, language):
    input_schema = analysis_result.get('input_schema') or {}
    provided_inputs = analysis_result.get('provided_inputs')
    concrete = analysis_result.get('concrete_analysis')
    input_effect = analysis_result.get('input_effect_analysis')
    allocation = analysis_result.get('memory_allocation_analysis')
    semantic = analysis_result.get('semantic_analysis')
    overall = analysis_result.get('overall_complexity')
    space_reason = analysis_result.get('space_complexity_reason', '')
    optimizations = analysis_result.get('optimizations') or []
    issues = analysis_result.get('issues') or []
    function_details = analysis_result.get('function_complexity_details') or []

    return f"""You are CodeScope's AI-powered explanation layer. Write the explanation that appears in the CodeScope app for this exact {language} code.

CodeScope's analyzer is the source of truth. Do not recalculate, override, simplify, or "correct" any analyzer-owned Big-O value. Your job is to turn the analyzer facts into a clear, code-specific explanation that feels tailored to the user's pasted code. You are not the detector; you are the professional explanation writer.

This prompt must work generically for any supported Python, C++, Java, JavaScript, or TypeScript snippet. Adapt to the actual identifiers and operations in CODE; do not use memorized example text or hard-coded algorithm blurbs unless that exact pattern appears in the analyzer facts.

CODE:
```{language}
{code[:3000]}
```

ANALYSIS RESULTS:
- Overall Complexity Summary: {json.dumps(overall, ensure_ascii=False) if overall else 'None'}
- Total Complexity Headline: {(overall or {}).get('headline') if isinstance(overall, dict) else 'None'}
- Memory Model: {(overall or {}).get('memory_model') if isinstance(overall, dict) else 'None'}
- Time Complexity: {analysis_result.get('time_complexity')}
- Space Complexity: {analysis_result.get('space_complexity')}
- Space Complexity Reason: {space_reason}
- Memory Allocation Analysis: {json.dumps(allocation, ensure_ascii=False) if allocation else 'None'}
- Semantic Assumptions/Risks: {json.dumps(semantic, ensure_ascii=False) if semantic else 'None'}
- Performance Rating: {analysis_result.get('rating')}/10
- Issues Found: {len(issues)}
- Reason: {analysis_result.get('time_complexity_reason', '')}
- Detected Input Schema: {json.dumps(input_schema, ensure_ascii=False)}
- User Provided Inputs: {json.dumps(provided_inputs, ensure_ascii=False) if provided_inputs else 'None'}
- Concrete Analysis: {json.dumps(concrete, ensure_ascii=False) if concrete else 'None'}
- Input Effect Estimate: {json.dumps(input_effect, ensure_ascii=False) if input_effect else 'None'}
- Function Complexity Details: {json.dumps(function_details, ensure_ascii=False)}
- Top Optimization Data: {json.dumps(optimizations[:2], ensure_ascii=False)}

Your output must be generic enough for any code, but specific to this code instance. Mention the actual function names, operations, library calls, or data structures when they are visible, such as slice(), sorted(), HashMap.put(), TreeMap, unordered_map, DFS, recursion branches, DP tables, regex patterns, or helper calls. Avoid template-sounding wording; explain this user's code.

Please provide:
1. why_this_complexity: start from the Total Complexity Headline when present, then explain the total/overall time complexity from the exact detected pattern.
2. real_world_analogy: one simple analogy connected to the detected pattern.
3. performance_impact: explain growth as input size increases, including reported space, peak live space, and total allocation pressure when Memory Allocation Analysis exists.
4. top_optimization: use only Top Optimization Data; if no safe rewrite exists, say why.

Rules:
- Treat the analyzer's detected reason as primary evidence.
- Only use Big-O values that appear in ANALYSIS RESULTS, Function Complexity Details, Memory Allocation Analysis, or Top Optimization Data.
- Never replace CodeScope's time_complexity, space_complexity, own_complexity, or effective_complexity with your own guess.
- If Overall Complexity Summary exists, use it as the top-level answer.
- If Memory Allocation Analysis exists, distinguish reported space complexity from peak live space and total allocated/copied memory. Do not call total allocation "peak space".
- If Semantic Assumptions/Risks exist, mention important runtime input, library, side-effect, or intended-behavior assumptions without changing the analyzer's Big-O.
- If Total Complexity Headline exists, keep the same facts in why_this_complexity and performance_impact.
- Use Function Complexity Details when explaining multi-function code.
- Treat Top Optimization Data as the only safe source for modified-code advice; do not invent replacement code.
- Use the code's own identifiers in every field when possible, so the explanation does not sound like a static template.
- For every field, mention at least one concrete code cue when available: function name, method call, data structure, loop variable, recursion call, or library operation.
- If the reason is a special sum such as sum_i log(n/i), explain that tighter bound instead of saying nested loops always multiply.
- If the user-provided values are fixed inputs, say fixed inputs are concrete examples; symbolic Big-O still describes variable input growth.
- If Concrete Analysis is None, use Input Effect Estimate only as a rough workload estimate, not exact execution.
- If recursion, explain the recursive call tree and do not describe it as a loop problem.
- If slicing/copying occurs in recursive calls, explicitly mention copy work and allocation pressure.
- If hash tables occur, explain expected/amortized behavior separately from collision-heavy worst cases.
- If sorting, graph traversal, DP, regex, or backtracking is the cause, name that pattern.
- Do not recommend a hash map unless Top Optimization Data explicitly says Hash Map or the code is clearly a lookup, duplicate, complement, or pair-search problem.
- If the best optimization says complexity_after is problem-dependent, say there is no universal safe rewrite and the strategy depends on the operation.
- Do not invent runtime measurements or execute the code.
- Keep each JSON value to 1-3 short beginner-friendly sentences. Avoid vague lines like "nested loops cause O(n²)" unless the analyzer reason actually says that.
- Return valid JSON only.

Format as JSON with keys: why_this_complexity, real_world_analogy, performance_impact, top_optimization"""


def _select_ai_code_optimization(analysis_result):
    optimizations = analysis_result.get('optimizations') or []
    if not isinstance(optimizations, list):
        return None

    blocked_after = {'problem-dependent', 'varies', 'better', 'Pruned exponential (constraint propagation)'}
    for opt in optimizations:
        if not isinstance(opt, dict):
            continue
        before = str(opt.get('complexity_before') or '').strip()
        after = str(opt.get('complexity_after') or '').strip()
        if not before or not after or after in blocked_after:
            continue
        example = opt.get('example')
        if not example:
            continue
        return opt

    transformed = analysis_result.get('transformed_code') or {}
    if transformed.get('available') and transformed.get('code'):
        return {
            'title': transformed.get('description', 'Analyzer-approved optimized rewrite'),
            'problem': transformed.get('description', ''),
            'solution': 'Use the analyzer-approved lower-complexity rewrite as the behavioral target.',
            'complexity_before': transformed.get('complexity_before'),
            'complexity_after': transformed.get('complexity_after'),
            'example': transformed.get('code'),
        }
    return None


def _build_ai_code_prompt(analysis_result, code, language, optimization):
    function_details = analysis_result.get('function_complexity_details') or []
    transformed = analysis_result.get('transformed_code') or {}
    input_schema = analysis_result.get('input_schema') or {}

    return f"""You are CodeScope's code optimizer. Generate a lower-complexity replacement for this exact {language} code only because CodeScope's analyzer has already approved this optimization target.

Analyzer facts are authoritative. Do not change the before/after complexity labels. If you cannot preserve behavior, return available=false instead of guessing.

ORIGINAL CODE:
```{language}
{code[:5000]}
```

ANALYZER COMPLEXITY FACTS:
- Overall: {json.dumps(analysis_result.get('overall_complexity'), ensure_ascii=False)}
- Time Complexity: {analysis_result.get('time_complexity')}
- Space Complexity: {analysis_result.get('space_complexity')}
- Reason: {analysis_result.get('time_complexity_reason', '')}
- Input Schema: {json.dumps(input_schema, ensure_ascii=False)}
- Function Details: {json.dumps(function_details, ensure_ascii=False)}

APPROVED OPTIMIZATION TARGET:
{json.dumps(optimization, ensure_ascii=False)}

ANALYZER TRANSFORMED CODE, IF AVAILABLE:
{json.dumps(transformed, ensure_ascii=False)}

Rewrite requirements:
- Preserve the same observable behavior for the same valid inputs.
- Preserve the same public function/class names and parameters unless the approved optimization explicitly requires helper parameters.
- It is okay to add private/local helper functions.
- Return complete usable code in the same language, not pseudocode.
- Do not include markdown fences in the code field.
- Do not invent a different algorithm unless it matches the approved optimization target.
- Do not add external dependencies unless the original code already uses them or the target example explicitly does.
- If behavior cannot be preserved safely, return available=false with a short reason.

Return valid JSON only with keys:
available, title, description, complexity_before, complexity_after, code, notes"""


def _normalize_ai_code_result(parsed, optimization):
    if not isinstance(parsed, dict):
        return {'available': False, 'reason': 'AI did not return a JSON object.', 'source': 'ai'}

    if parsed.get('available') is False:
        return {
            'available': False,
            'reason': str(parsed.get('reason') or parsed.get('notes') or 'AI declined to generate a safe rewrite.'),
            'source': 'ai'
        }

    code = str(parsed.get('code') or '').strip()
    code = re.sub(r'^```[a-zA-Z0-9_+-]*\s*|\s*```$', '', code).strip()
    if not code:
        return {'available': False, 'reason': 'AI did not return optimized code.', 'source': 'ai'}

    before = optimization.get('complexity_before')
    after = optimization.get('complexity_after')
    return {
        'available': True,
        'source': 'ai',
        'title': str(parsed.get('title') or optimization.get('title') or 'AI Optimized Code'),
        'description': str(parsed.get('description') or optimization.get('solution') or optimization.get('title') or ''),
        'complexity_before': before,
        'complexity_after': after,
        'code': code,
        'notes': str(parsed.get('notes') or 'Generated from analyzer-approved optimization facts.'),
    }


def _expensive_function_targets(analysis_result):
    details = analysis_result.get('function_complexity_details') or []
    if not isinstance(details, list):
        return []

    targets = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        complexity = str(
            detail.get('effective_complexity') or detail.get('complexity') or detail.get('own_complexity') or ''
        )
        own = str(detail.get('own_complexity') or complexity)
        snippet = str(detail.get('snippet') or '').strip()
        targets.append({
            'function': detail.get('function'),
            'line': detail.get('line'),
            'own_complexity': own,
            'effective_complexity': complexity,
            'reason': detail.get('reason', ''),
            'calls': detail.get('calls') or [],
            'snippet': snippet[:1200],
        })
    return targets[:24]


def _is_low_value_ai_rewrite_target(complexity):
    label = str(complexity or '').strip()
    if not label or label == 'O(unknown)':
        return True

    normalized = (
        label.lower()
        .replace(' ', '')
        .replace('α', 'alpha')
        .replace('Î±', 'alpha')
        .replace('²', '^2')
        .replace('Â²', '^2')
        .replace('³', '^3')
        .replace('Â³', '^3')
        .replace('√', 'sqrt')
        .replace('âˆš', 'sqrt')
    )
    cheap = {
        'o(1)',
        'o(alpha(n))',
        'o(loglogn)',
        'o(logn)',
        'o(log^2n)',
        'o(log^3n)',
        'o(sqrtn)',
        'o(n)',
        'o(nloglogn)',
    }
    return normalized in cheap


def _build_ai_optimization_prompt(analysis_result, code, language, optimizations, discovery_targets=None):
    function_details = analysis_result.get('function_complexity_details') or []
    input_schema = analysis_result.get('input_schema') or {}
    discovery_targets = discovery_targets or []

    candidates = []
    for index, opt in enumerate(optimizations[:4]):
        if not isinstance(opt, dict):
            continue
        candidates.append({
            'index': index,
            'title': opt.get('title'),
            'problem': opt.get('problem'),
            'solution': opt.get('solution'),
            'complexity_before': opt.get('complexity_before'),
            'complexity_after': opt.get('complexity_after'),
            'analyzer_example': opt.get('example'),
        })

    return f"""You are CodeScope's optimization-code generator. CodeScope's analyzer has already detected function complexities. Your job is to inspect the exact code, then:
1. Improve any analyzer optimization candidates with code-specific rewrites.
2. Independently inspect every detected function target and discover a same-input/same-output lower-complexity rewrite if one exists, even if the analyzer did not already name the optimization.

ORIGINAL CODE:
```{language}
{code[:12000]}
```

ANALYZER FACTS:
- Language: {language}
- Overall Complexity: {json.dumps(analysis_result.get('overall_complexity'), ensure_ascii=False)}
- Time Complexity: {analysis_result.get('time_complexity')}
- Space Complexity: {analysis_result.get('space_complexity')}
- Reason: {analysis_result.get('time_complexity_reason', '')}
- Input Schema: {json.dumps(input_schema, ensure_ascii=False)}
- Function Details: {json.dumps(function_details, ensure_ascii=False)}

OPTIMIZATION CANDIDATES:
{json.dumps(candidates, ensure_ascii=False)}

ALL DETECTED FUNCTIONS FOR AI OPTIMIZATION REVIEW:
{json.dumps(discovery_targets, ensure_ascii=False)}

Rules:
- Return a code-specific optimized version only when you can preserve the original function/class behavior for the same valid inputs.
- For every item under ALL DETECTED FUNCTIONS FOR AI OPTIMIZATION REVIEW, inspect that function's snippet, detected complexity, reason, and calls.
- Prefer rewriting the exact reviewed function, but include any helper needed for complete usable code.
- Preserve public function/class names and parameters unless the candidate explicitly requires helper parameters.
- The code field must contain complete code in the same language, not pseudocode and not a comment-only strategy list.
- Do not invent unrelated features, I/O prompts, console code, tests, or external dependencies.
- If the candidate is "problem-dependent" and the exact behavior cannot be inferred from the code, return available=false for that candidate.
- For independent discovery, only return a discovered optimization if you can clearly explain the original behavior and the replacement has lower Big-O than that function's effective_complexity.
- If a function is already asymptotically optimal for its required output, omit it from discovered_optimizations or return available=false for that function.
- It is allowed to improve complexity_after when the code-specific rewrite makes the target more precise, but never change the current code's detected complexity_before.
- Do not wrap code in markdown fences.
- Return valid JSON only.

Return this JSON shape:
{{
  "optimizations": [
    {{
      "index": 0,
      "available": true,
      "title": "short code-specific title",
      "problem": "what this code is doing inefficiently",
      "solution": "what the replacement changes",
      "complexity_before": "same as candidate",
      "complexity_after": "lower complexity of the replacement",
      "code": "complete optimized code",
      "notes": "short confidence/safety note"
    }}
  ],
  "discovered_optimizations": [
    {{
      "function": "function name",
      "available": true,
      "title": "short code-specific title",
      "problem": "what the function currently does inefficiently",
      "solution": "what lower-complexity version changes",
      "complexity_before": "detected current complexity",
      "complexity_after": "lower replacement complexity",
      "code": "complete optimized code",
      "notes": "why this preserves behavior"
    }}
  ]
}}"""


def _merge_ai_optimization_suggestions(
    optimizations,
    ai_payload,
    language=None,
    discovery_targets=None,
    original_code=None,
    provider='ai',
):
    provider = provider or 'ai'
    provider_label = _provider_label(provider)
    items = ai_payload.get('optimizations') if isinstance(ai_payload, dict) else ai_payload
    if not isinstance(items, list):
        items = []

    by_index = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            by_index[int(item.get('index'))] = item
        except (TypeError, ValueError):
            continue

    merged = []
    for index, opt in enumerate(optimizations):
        updated = dict(opt)
        ai_item = by_index.get(index)
        if not ai_item:
            merged.append(updated)
            continue

        code = str(ai_item.get('code') or '').strip()
        code = re.sub(r'^```[a-zA-Z0-9_+-]*\s*|\s*```$', '', code).strip()
        if ai_item.get('available') is True and code:
            before = str(opt.get('complexity_before') or ai_item.get('complexity_before') or '')
            validation = _validate_ai_rewrite_complexity(
                code,
                language,
                before,
                original_code=original_code,
                optimization=opt,
            )
            if not validation.get('valid'):
                updated['ai_reviewed'] = True
                updated['ai_note'] = validation.get(
                    'reason',
                    'AI returned code, but CodeScope could not verify a lower-complexity rewrite.'
                )
                merged.append(updated)
                continue

            updated['analyzer_example'] = opt.get('example')
            updated['example'] = code
            updated['ai_generated'] = True
            updated['source'] = provider
            updated['source_label'] = provider_label
            updated['title'] = str(ai_item.get('title') or opt.get('title') or 'AI Optimized Alternative')
            updated['problem'] = str(ai_item.get('problem') or opt.get('problem') or '')
            updated['solution'] = str(ai_item.get('solution') or opt.get('solution') or '')
            updated['complexity_before'] = before
            updated['complexity_after'] = validation.get('complexity') or str(
                ai_item.get('complexity_after') or opt.get('complexity_after') or ''
            )
            updated['ai_note'] = str(
                ai_item.get('notes') or
                f"Generated by AI and re-analyzed by CodeScope as {updated['complexity_after']}."
            )
            updated['validation'] = validation
        else:
            updated['ai_reviewed'] = True
            updated['ai_note'] = str(
                ai_item.get('reason') or ai_item.get('notes') or
                'AI could not safely produce a same-behavior lower-complexity rewrite for this candidate.'
            )
        merged.append(updated)

    discovered = ai_payload.get('discovered_optimizations') if isinstance(ai_payload, dict) else []
    targets = {
        str(target.get('function')): target
        for target in (discovery_targets or [])
        if isinstance(target, dict) and target.get('function')
    }
    if isinstance(discovered, list):
        for item in discovered:
            if not isinstance(item, dict) or item.get('available') is not True:
                continue
            code = str(item.get('code') or '').strip()
            code = re.sub(r'^```[a-zA-Z0-9_+-]*\s*|\s*```$', '', code).strip()
            if not code:
                continue
            function = str(item.get('function') or '')
            target = targets.get(function)
            before = str(
                (target or {}).get('effective_complexity') or
                (target or {}).get('own_complexity') or
                item.get('complexity_before') or ''
            )
            validation = _validate_ai_rewrite_complexity(
                code,
                language,
                before,
                original_code=original_code,
                optimization=target or item,
                required_function=function or None,
            )
            if not validation.get('valid'):
                continue
            merged.append({
                'title': str(item.get('title') or f'{provider_label} Discovered Optimized Alternative'),
                'problem': str(item.get('problem') or ''),
                'solution': str(item.get('solution') or ''),
                'complexity_before': before,
                'complexity_after': validation.get('complexity') or str(item.get('complexity_after') or ''),
                'example': code,
                'ai_generated': True,
                'ai_discovered': True,
                'source': provider,
                'source_label': provider_label,
                'function': function or item.get('function'),
                'ai_note': str(item.get('notes') or f'{provider_label} independently discovered this lower-complexity rewrite from the function facts.'),
                'validation': validation,
            })
    return merged


def _provider_label(provider):
    provider = str(provider or '').lower()
    if provider == 'groq':
        return 'Groq'
    if provider == 'grok':
        return 'Grok'
    return 'AI'


def _validate_ai_rewrite_complexity(
    code,
    language,
    complexity_before,
    original_code=None,
    optimization=None,
    required_function=None,
):
    if not code.strip():
        return {'valid': False, 'reason': 'AI did not return code to validate.'}

    shape_validation = _validate_ai_rewrite_shape(
        original_code,
        code,
        language,
        optimization=optimization,
        required_function=required_function,
    )
    if not shape_validation.get('valid'):
        return shape_validation

    if not language or not complexity_before:
        return {
            'valid': True,
            'reason': shape_validation.get('reason', 'No analyzer baseline was available for validation.'),
            'semantic_guard': shape_validation,
        }

    try:
        from app.analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer()
        filename = {
            'python': 'optimized.py',
            'javascript': 'optimized.js',
            'typescript': 'optimized.ts',
            'java': 'Optimized.java',
            'cpp': 'optimized.cpp',
            'c': 'optimized.c',
        }.get(language, 'optimized.txt')
        result = analyzer.analyze(code, filename)
        complexity_after = result.get('time_complexity')
        before_rank = analyzer._complexity_rank(analyzer._parse_complexity_string(complexity_before))
        after_rank = analyzer._complexity_rank(analyzer._parse_complexity_string(complexity_after))
        if complexity_after == 'O(unknown)':
            return {
                'valid': False,
                'complexity': complexity_after,
                'reason': 'AI code contains unresolved calls, so CodeScope cannot verify the improvement.',
            }
        if after_rank < before_rank:
            return {
                'valid': True,
                'complexity': complexity_after,
                'reason': (
                    f'CodeScope re-analyzed the AI rewrite as {complexity_after}; '
                    f"{shape_validation.get('reason', 'public API guard passed')}"
                ),
                'semantic_guard': shape_validation,
            }
        return {
            'valid': False,
            'complexity': complexity_after,
            'reason': (
                f'AI code was re-analyzed as {complexity_after}, which is not lower than '
                f'the original {complexity_before}.'
            ),
        }
    except Exception as exc:
        return {'valid': False, 'reason': f'Could not validate AI rewrite: {exc}'}


def _validate_ai_rewrite_shape(original_code, optimized_code, language, optimization=None, required_function=None):
    text = (optimized_code or '').strip()
    if not text:
        return {'valid': False, 'reason': 'AI did not return code to validate.'}

    if _looks_like_non_code_response(text):
        return {
            'valid': False,
            'reason': 'AI response looked like explanation text or pseudocode, not complete optimized code.',
        }

    syntax = _syntax_shape_check(text, language)
    if not syntax.get('valid'):
        return syntax

    original_signatures = _public_function_signatures(original_code or '', language)
    optimized_signatures = _public_function_signatures(text, language)

    required_names = []
    if required_function:
        required_names.append(str(required_function))
    opt_function = (optimization or {}).get('function') if isinstance(optimization, dict) else None
    if opt_function:
        required_names.append(str(opt_function))
    if not required_names and len(original_signatures) == 1:
        required_names = list(original_signatures.keys())
    required_names = [
        name for index, name in enumerate(required_names)
        if name and name not in required_names[:index]
    ]

    if original_signatures and not optimized_signatures:
        return {
            'valid': False,
            'reason': 'AI rewrite removed the public function/class signature, so behavior cannot be trusted.',
        }

    if original_signatures and optimized_signatures and not required_names:
        shared = set(original_signatures) & set(optimized_signatures)
        if not shared:
            return {
                'valid': False,
                'reason': 'AI rewrite does not preserve any original public function/class name.',
            }

    for name in required_names:
        if optimized_signatures and name not in optimized_signatures:
            return {
                'valid': False,
                'reason': f'AI rewrite does not preserve required public function/class name: {name}.',
            }
        if name in original_signatures and name in optimized_signatures:
            original_params = original_signatures[name].get('params') or []
            optimized_params = optimized_signatures[name].get('params') or []
            if len(original_params) != len(optimized_params):
                return {
                    'valid': False,
                    'reason': f'AI rewrite changed the parameter count for {name}.',
                }
            if original_params and optimized_params and original_params != optimized_params:
                return {
                    'valid': False,
                    'reason': f'AI rewrite changed the public parameter names for {name}.',
                }

    semantic_probe = _python_semantic_equivalence_probe(
        original_code or '',
        text,
        required_names,
        original_signatures,
        optimized_signatures,
        language,
    )
    if semantic_probe.get('status') == 'failed':
        return {
            'valid': False,
            'reason': semantic_probe.get(
                'reason',
                'AI rewrite failed safe semantic equivalence probes.',
            ),
            'semantic_equivalence': semantic_probe,
        }

    return {
        'valid': True,
        'reason': 'syntax and public API guard passed; semantic equivalence still depends on the approved optimization facts.',
        'original_signatures': original_signatures,
        'optimized_signatures': optimized_signatures,
        'semantic_equivalence': semantic_probe,
    }


def _looks_like_non_code_response(text):
    lowered = text.lower()
    if lowered.startswith(('here is', "here's", 'sure,', 'the optimized', 'explanation:')):
        return True
    if '```' in text:
        return True
    return bool(re.search(r'\b(pseudocode|todo:|replace this with|same as above)\b', lowered))


def _syntax_shape_check(code, language):
    if language == 'python':
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return {'valid': False, 'reason': f'AI Python rewrite has invalid syntax: {exc.msg}.'}
    elif language in ('javascript', 'typescript', 'java', 'cpp', 'c'):
        if not _balanced_code_delimiters(code):
            return {'valid': False, 'reason': 'AI rewrite has unbalanced brackets/braces.'}
    return {'valid': True}


def _balanced_code_delimiters(code):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    quote = None
    escaped = False
    for ch in code:
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'", '`'):
            quote = ch
            continue
        if ch in pairs.values():
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack and quote is None


def _public_function_signatures(code, language):
    if not code:
        return {}
    if language == 'python':
        return _python_public_signatures(code)
    return _regex_public_signatures(code, language)


def _python_public_signatures(code):
    signatures = {}
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return signatures

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
            signatures[node.name] = {'params': _python_param_names(node.args)}
        elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            signatures[node.name] = {'params': []}
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith('_'):
                    params = _python_param_names(child.args)
                    if params and params[0] in ('self', 'cls'):
                        params = params[1:]
                    signatures[f'{node.name}.{child.name}'] = {'params': params}
    return signatures


def _python_param_names(args):
    params = [arg.arg for arg in getattr(args, 'posonlyargs', [])]
    params.extend(arg.arg for arg in args.args)
    params.extend(arg.arg for arg in args.kwonlyargs)
    if args.vararg:
        params.append(args.vararg.arg)
    if args.kwarg:
        params.append(args.kwarg.arg)
    return params


def _regex_public_signatures(code, language):
    signatures = {}
    patterns = [
        r'\bfunction\s*\*?\s+([A-Za-z_]\w*)\s*\(([^)]*)\)',
        r'\b(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([A-Za-z_]\w*))\s*(?::\s*[^=]+)?=>',
        (
            r'\b(?:public|private|protected)?\s*(?:static\s+)?'
            r'(?:[\w:<>\[\], ?&*]+\s+)+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:const\s*)?\{'
        ),
        r'\bclass\s+([A-Za-z_]\w*)\b',
    ]
    keywords = {'if', 'for', 'while', 'switch', 'catch', 'return'}
    for pattern in patterns:
        for match in re.finditer(pattern, code):
            name = match.group(1)
            if name in keywords or name.startswith('_'):
                continue
            raw_params = ''
            if match.lastindex and match.lastindex >= 2:
                raw_params = match.group(2) or (match.group(3) if match.lastindex >= 3 else '') or ''
            signatures[name] = {'params': _split_signature_params(raw_params, language)}
    return signatures


def _split_signature_params(raw_params, language):
    params = []
    current = ''
    depth = 0
    openers = {'<', '(', '[', '{'}
    closers = {'>', ')', ']', '}'}
    for ch in raw_params or '':
        if ch in openers:
            depth += 1
        elif ch in closers and depth > 0:
            depth -= 1
        if ch == ',' and depth == 0:
            name = _normalize_param_name(current, language)
            if name:
                params.append(name)
            current = ''
        else:
            current += ch
    name = _normalize_param_name(current, language)
    if name:
        params.append(name)
    return params


def _normalize_param_name(raw, language):
    text = re.sub(r'=.*$', '', raw or '').strip()
    if not text:
        return ''
    text = text.replace('...', '').replace('&', ' ').replace('*', ' ').strip()
    if language in ('javascript', 'typescript', 'python') and ':' in text:
        text = text.split(':', 1)[0].strip()
    text = re.sub(r'\[[^\]]*\]$', '', text).strip()
    tokens = re.split(r'\s+', text)
    return re.sub(r'\W+', '', tokens[-1]) if tokens else ''


def _python_semantic_equivalence_probe(
    original_code,
    optimized_code,
    required_names,
    original_signatures,
    optimized_signatures,
    language,
):
    if language != 'python':
        return {
            'status': 'skipped',
            'reason': 'Semantic probes currently run only for safe pure Python functions.',
        }
    if not original_code or not original_signatures or not optimized_signatures:
        return {'status': 'skipped', 'reason': 'Original and optimized Python signatures are required.'}

    candidates = [name for name in required_names if name in original_signatures and name in optimized_signatures]
    if not candidates:
        candidates = sorted(set(original_signatures) & set(optimized_signatures))
    candidates = [name for name in candidates if '.' not in name]
    if not candidates:
        return {'status': 'skipped', 'reason': 'No shared top-level Python function was available for probing.'}

    target = candidates[0]
    params = original_signatures[target].get('params') or []
    if len(params) > 4:
        return {'status': 'skipped', 'reason': 'Function has too many parameters for bounded semantic probes.'}

    original_safety = _safe_python_probe_subset(original_code)
    optimized_safety = _safe_python_probe_subset(optimized_code)
    if not original_safety.get('safe') or not optimized_safety.get('safe'):
        return {
            'status': 'skipped',
            'reason': original_safety.get('reason') or optimized_safety.get('reason') or 'Code is outside safe probe subset.',
        }

    samples = _python_probe_samples(params)
    if not samples:
        return {'status': 'skipped', 'reason': 'No bounded sample inputs could be generated.'}

    try:
        original_fn = _load_safe_python_function(original_code, target)
        optimized_fn = _load_safe_python_function(optimized_code, target)
    except Exception as exc:
        return {'status': 'skipped', 'reason': f'Could not load safe Python functions: {exc}'}

    checked = 0
    for args in samples:
        checked += 1
        left_args = copy.deepcopy(args)
        right_args = copy.deepcopy(args)
        try:
            left = original_fn(*left_args)
            left_error = None
        except Exception as exc:
            left = None
            left_error = type(exc).__name__
        try:
            right = optimized_fn(*right_args)
            right_error = None
        except Exception as exc:
            right = None
            right_error = type(exc).__name__

        if left_error or right_error:
            if left_error != right_error:
                return {
                    'status': 'failed',
                    'reason': f'Python semantic probe mismatch on sample {checked}: {left_error} vs {right_error}.',
                    'function': target,
                    'samples_checked': checked,
                }
            continue
        if left != right:
            return {
                'status': 'failed',
                'reason': f'Python semantic probe mismatch on sample {checked}: {left!r} != {right!r}.',
                'function': target,
                'samples_checked': checked,
            }

    return {
        'status': 'checked',
        'reason': f'Checked {checked} bounded safe Python sample input(s) with matching outputs.',
        'function': target,
        'samples_checked': checked,
    }


def _safe_python_probe_subset(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {'safe': False, 'reason': f'Python syntax is invalid: {exc.msg}.'}

    allowed_nodes = (
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign,
        ast.AugAssign, ast.AnnAssign, ast.For, ast.If, ast.Expr, ast.Compare,
        ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load, ast.Store,
        ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Subscript, ast.Slice,
        ast.IfExp, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
        ast.comprehension, ast.Break, ast.Continue, ast.Pass,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
        ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    )
    disallowed_nodes = (
        ast.Import, ast.ImportFrom, ast.ClassDef, ast.Lambda, ast.While, ast.With,
        ast.Try, ast.Raise, ast.Global, ast.Nonlocal, ast.Delete, ast.AsyncFunctionDef,
        ast.Await, ast.Yield, ast.YieldFrom, ast.Attribute,
    )
    safe_builtins = set(_safe_python_builtins())
    defined_functions = {
        node.name for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')
    }

    for top_level in tree.body:
        if not isinstance(top_level, ast.FunctionDef):
            return {'safe': False, 'reason': 'Safe semantic probes allow top-level functions only.'}

    for node in ast.walk(tree):
        if isinstance(node, disallowed_nodes):
            return {'safe': False, 'reason': f'{type(node).__name__} is outside the safe probe subset.'}
        if not isinstance(node, allowed_nodes):
            return {'safe': False, 'reason': f'{type(node).__name__} is outside the safe probe subset.'}
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                return {'safe': False, 'reason': 'Only direct safe function calls can be probed.'}
            if node.func.id not in safe_builtins and node.func.id not in defined_functions:
                return {'safe': False, 'reason': f'Call to {node.func.id} is outside the safe probe subset.'}

    return {'safe': True}


def _safe_python_builtins():
    return {
        'abs': abs,
        'all': all,
        'any': any,
        'bool': bool,
        'dict': dict,
        'enumerate': enumerate,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'max': max,
        'min': min,
        'range': range,
        'reversed': reversed,
        'round': round,
        'set': set,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
    }


def _load_safe_python_function(code, target):
    namespace = {'__builtins__': _safe_python_builtins()}
    exec(compile(code, '<codescope-semantic-probe>', 'exec'), namespace, namespace)
    fn = namespace.get(target)
    if not callable(fn):
        raise ValueError(f'{target} was not callable after loading.')
    return fn


def _python_probe_samples(params):
    value_sets = [_sample_values_for_param(name) for name in params]
    samples = []
    for values in itertools.product(*value_sets):
        samples.append(list(values))
        if len(samples) >= 18:
            break
    return samples


def _sample_values_for_param(name):
    lowered = str(name or '').lower()
    if re.search(r'(nums|numbers|arr|array|items|values|list|seq)', lowered):
        return [[], [1], [1, 2, 1], [0, -1, 2]]
    if re.search(r'(s|str|text|word|pattern)$', lowered):
        return ['', 'a', 'aba', 'abc']
    if re.search(r'(flag|enabled|ok|valid|is_|has_)', lowered):
        return [False, True]
    if re.search(r'(target|key|value|x|y|z|n|m|k|count|size|limit|index|idx)', lowered):
        return [0, 1, 2, 5]
    return [0, 1, 2]


def _ai_messages(prompt):
    return [
        {
            'role': 'system',
            'content': (
                'You are CodeScope AI Explainer. Follow analyzer facts exactly, write code-specific beginner-friendly '
                'explanations, and return only valid JSON in the requested schema.'
            )
        },
        {'role': 'user', 'content': prompt}
    ]


def _provider_order():
    if AI_EXPLAINER_PROVIDER in ('grok', 'xai'):
        return ('grok', 'groq')
    if AI_EXPLAINER_PROVIDER == 'groq':
        return ('groq', 'grok')
    if GROK_API_KEY:
        return ('grok', 'groq')
    return ('groq', 'grok')


def _call_ai_completion(prompt, max_tokens=900, return_source=False):
    last_error = None
    for provider in _provider_order():
        timeout = _remaining_ai_timeout()
        if timeout <= 0:
            _log_ai_error('AI budget exhausted; using analyzer fallback.')
            break

        if provider == 'grok' and GROK_API_KEY:
            try:
                response = requests.post(
                    GROK_API_BASE,
                    headers={
                        'Authorization': f'Bearer {GROK_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': GROK_MODEL,
                        'messages': _ai_messages(prompt),
                        'temperature': 0.2,
                        'max_tokens': max_tokens,
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload['choices'][0]['message']['content']
                return (content, 'grok') if return_source else content
            except Exception as exc:
                last_error = exc
                _log_ai_error(f'Grok API error: {exc}')
        if provider == 'groq' and GROQ_API_KEY:
            try:
                timeout = _remaining_ai_timeout()
                if timeout <= 0:
                    _log_ai_error('AI budget exhausted before Groq call; using analyzer fallback.')
                    break
                client = _groq_client(timeout)
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=_ai_messages(prompt),
                    temperature=0.2,
                    max_tokens=max_tokens
                )
                content = response.choices[0].message.content
                return (content, 'groq') if return_source else content
            except ImportError as exc:
                last_error = exc
                _log_ai_error(f'Groq package unavailable: {exc}')
            except Exception as exc:
                last_error = exc
                _log_ai_error(f'Groq API error: {exc}')
    if last_error:
        _log_ai_error(f'AI provider unavailable; using fallback explanation: {last_error}')
    return (None, None) if return_source else None


def _parse_ai_json(content):
    content = _extract_json_payload(content)
    try:
        return json.loads(content)
    except Exception:
        return {'why_this_complexity': content, 'real_world_analogy': '',
                'performance_impact': '', 'top_optimization': ''}


def _normalize_ai_explanation_result(parsed, analysis_result, code, language, source='configured_ai'):
    if not isinstance(parsed, dict):
        return {'available': False, 'reason': 'AI explanation was not a JSON object.'}

    fallback = _build_generic_fact_explanation(analysis_result, code, language)
    keys = ('why_this_complexity', 'real_world_analogy', 'performance_impact', 'top_optimization')
    normalized = {}
    for key in keys:
        value = parsed.get(key)
        normalized[key] = str(value).strip() if value not in (None, '') else fallback[key]

    if _ai_explanation_conflicts_with_facts(normalized, analysis_result):
        fallback['source'] = 'analyzer_fallback'
        fallback['available'] = True
        fallback['ai_rejected'] = True
        fallback['reason'] = 'AI explanation mentioned Big-O values that conflict with analyzer-owned facts.'
        return fallback

    normalized.update(_analysis_fact_metadata(analysis_result))
    normalized['source'] = source or 'configured_ai'
    normalized['available'] = True
    normalized['fact_locked'] = True
    return normalized


def _analysis_fact_metadata(analysis_result):
    return {
        'detected_time_complexity': analysis_result.get('time_complexity'),
        'detected_space_complexity': analysis_result.get('space_complexity'),
        'detected_reason': analysis_result.get('time_complexity_reason', ''),
        'memory_model': analysis_result.get('memory_allocation_analysis') or {},
    }


def _ai_explanation_conflicts_with_facts(explanation, analysis_result):
    allowed = _allowed_complexity_mentions(analysis_result)
    text = ' '.join(str(explanation.get(key, '')) for key in (
        'why_this_complexity', 'performance_impact', 'top_optimization'
    ))
    return _text_has_disallowed_complexity(text, allowed)


def _allowed_complexity_mentions(analysis_result):
    allowed = set()

    def add(value):
        if value:
            allowed.add(_normalize_complexity_token(value))

    add(analysis_result.get('time_complexity'))
    add(analysis_result.get('space_complexity'))
    overall = analysis_result.get('overall_complexity') or {}
    for value in overall.values():
        add(value)
    allocation = analysis_result.get('memory_allocation_analysis') or {}
    for key in ('peak_live_auxiliary_space', 'total_allocated_space'):
        add(allocation.get(key))
    for detail in analysis_result.get('function_complexity_details') or []:
        if not isinstance(detail, dict):
            continue
        add(detail.get('complexity'))
        add(detail.get('own_complexity'))
        add(detail.get('effective_complexity'))
        for call in detail.get('calls') or []:
            if isinstance(call, dict):
                add(call.get('complexity'))
                add(call.get('multiplier'))
    for opt in analysis_result.get('optimizations') or []:
        if isinstance(opt, dict):
            add(opt.get('complexity_before'))
            add(opt.get('complexity_after'))
    return allowed


def _text_has_disallowed_complexity(text, allowed):
    for token in re.findall(r'O\s*\([^)]*\)', str(text or '')):
        normalized = _normalize_complexity_token(token)
        if normalized and normalized not in allowed:
            return True
    return False


def _normalize_complexity_token(value):
    text = _normalize_complexity(value)
    return (
        text.replace('×', 'x')
        .replace('*', 'x')
        .replace('α', 'alpha')
        .replace('³', '^3')
        .replace('²', '^2')
        .replace('ⁿ', '^n')
        .replace('  ', ' ')
        .strip()
    )


def _extract_json_payload(content):
    text = re.sub(r'```(?:json)?|```', '', content or '').strip()
    if not text:
        return text
    first_object = text.find('{')
    first_array = text.find('[')
    starts = [i for i in (first_object, first_array) if i != -1]
    if not starts:
        return text
    start = min(starts)
    end_char = '}' if text[start] == '{' else ']'
    end = text.rfind(end_char)
    return text[start:end + 1] if end >= start else text


def _get_fallback_explanation(analysis_result, code, language):
    """
    Generic analyzer-fact explanation when the configured AI/API is not available.
    """
    fallback = _build_generic_fact_explanation(analysis_result, code, language)
    fallback['source'] = 'analyzer_fallback'
    fallback['available'] = True
    fallback['fact_locked'] = True
    fallback['reason'] = 'Configured AI was unavailable, so CodeScope used analyzer-owned facts.'
    return fallback


def _build_generic_fact_explanation(analysis_result, code, language):
    tc = analysis_result.get('time_complexity', 'Unknown')
    sc = analysis_result.get('space_complexity', 'Unknown')
    reason = (analysis_result.get('time_complexity_reason') or '').strip()
    overall = analysis_result.get('overall_complexity') or {}
    headline = overall.get('headline') if isinstance(overall, dict) else ''
    memory_model = overall.get('memory_model') if isinstance(overall, dict) else ''
    function_details = analysis_result.get('function_complexity_details') or []
    allocation = analysis_result.get('memory_allocation_analysis') or {}
    optimizations = analysis_result.get('optimizations') or []

    function_names = [
        str(item.get('function'))
        for item in function_details
        if isinstance(item, dict) and item.get('function')
    ]
    function_text = ', '.join(f'{name}()' for name in function_names[:4])
    if len(function_names) > 4:
        function_text += ', ...'

    dominant = next(
        (
            item for item in function_details
            if isinstance(item, dict) and item.get('effective_complexity') == tc
        ),
        function_details[0] if function_details else None
    )
    dominant_text = ''
    if isinstance(dominant, dict):
        own = dominant.get('own_complexity') or dominant.get('complexity')
        effective = dominant.get('effective_complexity') or dominant.get('complexity')
        dominant_text = (
            f" The main function-level driver is {dominant.get('function')}(), "
            f"with own cost {own} and effective cost {effective}."
        )

    memory_text = ''
    if allocation:
        peak = allocation.get('peak_live_auxiliary_space', sc)
        total = allocation.get('total_allocated_space', peak)
        memory_text = f" Peak auxiliary space is {peak}; total allocation pressure is {total}."

    optimization_text = _first_optimization(
        analysis_result,
        'No analyzer-approved safe rewrite is available for this exact code.'
    )
    if optimizations:
        optimization_text = _first_optimization(analysis_result, optimization_text)

    display_reason = reason
    if 'matrix' in (code or '').lower() and 'Binary exponentiation' in reason:
        display_reason = f"binary matrix exponentiation ({reason})"

    why = (
        f"CodeScope's total summary is {headline or f'{tc} time and {sc} space'}. "
        f"It classified this {language or 'code'} from analyzer-owned evidence: "
        f"{display_reason or 'matched loops, calls, recursion, and known algorithm patterns'}."
        f"{dominant_text}"
    )
    if function_text:
        why += f" Functions considered: {function_text}."

    performance_impact = f"As inputs grow, runtime follows {tc} while reported space follows {sc}."
    if memory_model:
        performance_impact += f" {memory_model}"
    elif memory_text:
        performance_impact += memory_text

    return {
        'why_this_complexity': why,
        'real_world_analogy': (
            "Think of the analyzer facts as the measured skeleton of the program, and this explanation as the plain-English label attached to that skeleton."
        ),
        'performance_impact': performance_impact,
        'top_optimization': optimization_text,
        **_analysis_fact_metadata(analysis_result),
    }


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

    if norm_tc in ('O(α(n))', 'O(alpha(n))'):
        return {
            'why_this_complexity': (
                "This is Union-Find with path compression and union by rank/size. "
                "Those two techniques make each find or union amortized O(α(n)), where α is the inverse Ackermann function."
            ),
            'real_world_analogy': (
                "It is like updating shortcuts every time you follow a chain, so the next lookup reaches the leader almost immediately."
            ),
            'performance_impact': (
                "α(n) grows so slowly that it is at most a tiny constant for any realistic input, but O(α(n)) is the precise theoretical bound."
            ),
            'top_optimization': "This is already the standard optimal DSU implementation. Keep both path compression and rank/size linking."
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

    fractional_poly = re.fullmatch(r'O\(n\^([0-9]+(?:\.[0-9]+)?)\)', norm_tc)
    if fractional_poly:
        exponent = float(fractional_poly.group(1))
        return {
            'why_this_complexity': (
                f"This is {tc} because the recursive branches shrink by different factors. "
                "For uneven divide-and-conquer, CodeScope solves the Akra-Bazzi equation instead of assuming every branch is n/2."
            ),
            'real_world_analogy': (
                "It is like splitting work into two smaller piles where one pile is half-sized and the other is third-sized. "
                "The total tree grows, but not as fast as a full linear number of nodes."
            ),
            'performance_impact': (
                (
                    f"The exponent {exponent:.3f} is below 1, so this grows sublinearly in the symbolic model. "
                    "It is much better than O(n), while still slower than logarithmic recursion."
                ) if exponent < 1 else (
                    f"The exponent {exponent:.3f} is between common polynomial classes. "
                    "It grows faster than linear time but remains better than quadratic time."
                )
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "No generic rewrite is needed; this is already a tight divide-and-conquer bound for the detected recurrence."
            )
        }

    if norm_tc == 'O(k^3 log n)':
        return {
            'why_this_complexity': (
                "This is binary matrix exponentiation. power() reduces the exponent in O(log n) recursive levels, "
                "and each level calls multiply(), whose three nested loops multiply two k by k matrices in O(k^3) time."
            ),
            'real_world_analogy': (
                "It is like folding the exponent in half again and again, but paying for one full matrix multiplication at each fold."
            ),
            'performance_impact': (
                "The exponent n is handled efficiently because it only adds a log n factor. The matrix dimension k is the real bottleneck: "
                "doubling k makes each multiplication about eight times more expensive."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Use an optimized matrix multiplication backend such as NumPy/BLAS, or consider blocking/Strassen-style multiplication for very large matrices."
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
        if 'immutable string' in reason_lower or 'string concatenation' in reason_lower:
            return {
                'why_this_complexity': (
                    "This is quadratic because the code repeatedly concatenates to an immutable string inside a loop. "
                    "Each update copies the existing accumulated text, so the copy work adds up like 1 + 2 + ... + n."
                ),
                'real_world_analogy': (
                    "It is like rewriting the whole sentence every time you add one new word, instead of keeping a list of words and joining once."
                ),
                'performance_impact': (
                    "Small n may look fine, but doubling n can create about four times as much copying. "
                    "The final string uses linear space, but the repeated copying costs quadratic time."
                ),
                'top_optimization': _first_optimization(
                    analysis_result,
                    "Collect pieces in a list/array/StringBuilder and join once at the end."
                )
            }
        if 'front insertion' in reason_lower or 'insert shifts' in reason_lower or 'unshift' in reason_lower:
            return {
                'why_this_complexity': (
                    "This is quadratic because each front insertion into an array-backed container shifts the existing elements. "
                    "The loop performs inserts of cost 0, 1, 2, and so on, which adds up to O(n²)."
                ),
                'real_world_analogy': (
                    "It is like adding each new item to the front of a packed shelf: every existing item must move one slot to the right."
                ),
                'performance_impact': (
                    "This is much slower than appending. Doubling n can create roughly four times as much shifting work."
                ),
                'top_optimization': _first_optimization(
                    analysis_result,
                    "Append at the back and reverse once, or use a deque/list structure with O(1) front insertion."
                )
            }
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

    if norm_tc == 'O(n^2 log n)':
        if 'ordered map' in reason_lower or 'tree lookup' in reason_lower:
            return {
                'why_this_complexity': (
                    "This is O(n² log n) because the code performs n² loop iterations, and each ordered map access is a tree operation costing O(log n)."
                ),
                'real_world_analogy': (
                    "It is like doing every grid cell update, but each update also has to walk a small sorted directory to find the right key."
                ),
                'performance_impact': (
                    "It is slower than plain O(n²) by a logarithmic factor. "
                    "The map stores up to n² keys, so memory grows quadratically."
                ),
                'top_optimization': _first_optimization(
                    analysis_result,
                    "Use an unordered/hash map if key order is not needed, or a vector/array when keys are dense integers."
                )
            }
        return {
            'why_this_complexity': (
                "This is O(n² log n) because quadratic loop work is combined with a logarithmic operation inside the loop."
            ),
            'real_world_analogy': (
                "It is like checking every pair in a grid, then doing a small binary-search-style lookup for each pair."
            ),
            'performance_impact': (
                "This grows faster than O(n²), so large inputs can slow down noticeably once the logarithmic lookup cost piles up."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Look for a way to replace the logarithmic inner operation with O(1) average lookup or direct indexing."
            )
        }

    if norm_tc == 'O(n log^2 n)':
        return {
            'why_this_complexity': (
                "This is O(n log² n) because the code splits the array recursively, but then re-sorts the combined left and right halves at every level. "
                "Each recursion level pays sorting-style O(n log n) work, and there are O(log n) levels."
            ),
            'real_world_analogy': (
                "It is like dividing papers into piles, sorting every pile, then mixing pairs of piles and sorting those larger piles again instead of simply merging them."
            ),
            'performance_impact': (
                "This is slower than true merge sort by one extra log n factor. "
                "It may look close on small inputs, but the extra sorting at every level becomes visible as n grows."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "Use a linear merge step after the two recursive calls, or call built-in sorted once instead of re-sorting at each recursion level."
            )
        }

    if norm_tc == 'O(n log n)':
        allocation = analysis_result.get('memory_allocation_analysis') or {}
        if allocation.get('pattern') == 'recursive_slice_copy':
            why = (
                "This is O(n log n) because the function recursively splits the array in half, and each slice() call copies elements. "
                "Across each recursion level those copied slices total O(n), and there are O(log n) levels."
            )
            optimization = "Pass left/right index boundaries instead of calling slice() so the recursion does not copy new arrays at every level."
            impact = (
                "Peak live space is O(n), but total allocated slice memory over the full run is O(n log n). "
                "The allocation pressure can matter in JavaScript/TypeScript even when the peak memory bound is lower."
            )
        elif 'sort' in reason_lower or 'sort' in code_lower:
            why = (
                "This is O(n log n) because the main cost is sorting. "
                "Comparison sorting repeatedly divides and orders the data, which adds the log n factor."
            )
            optimization = "For comparison sorting this is usually optimal. Only optimize if the input has a special property, such as small integer ranges."
            impact = (
                "n=1,000 is roughly 10,000 work units, while n=1,000,000 is roughly 20,000,000. "
                "It grows faster than O(n), but it is still very manageable."
            )
        elif 'harmonic' in reason_lower:
            why = (
                "This is O(n log n) because the inner work shrinks in a harmonic pattern. "
                "The first passes do more work, later passes do less, and the total adds up to n log n."
            )
            optimization = "This pattern is usually acceptable. Check whether repeated work can be cached or skipped."
            impact = (
                "n=1,000 is roughly 10,000 work units, while n=1,000,000 is roughly 20,000,000. "
                "It grows faster than O(n), but it is still very manageable."
            )
        elif 'geometric' in reason_lower:
            why = (
                "This is O(n log n) because one part grows by input size while another part grows by repeated doubling or halving. "
                "That creates linear work multiplied by a logarithmic number of steps."
            )
            optimization = "This is generally efficient. Focus on avoiding unnecessary work inside the repeated section."
            impact = (
                "n=1,000 is roughly 10,000 work units, while n=1,000,000 is roughly 20,000,000. "
                "It grows faster than O(n), but it is still very manageable."
            )
        else:
            why = (
                "This is O(n log n) because the code combines input-sized work with a logarithmic step. "
                "That commonly happens in efficient sorting or divide-and-conquer algorithms."
            )
            optimization = "This is usually a good complexity for sorting and divide-and-conquer code."
            impact = (
                "n=1,000 is roughly 10,000 work units, while n=1,000,000 is roughly 20,000,000. "
                "It grows faster than O(n), but it is still very manageable."
            )
        return {
            'why_this_complexity': why,
            'real_world_analogy': (
                "It is like organizing a large set by repeatedly splitting it into smaller groups, then combining the results."
            ),
            'performance_impact': impact,
            'top_optimization': _first_optimization(analysis_result, optimization)
        }

    if norm_tc in ('O(log^2 n)', 'O(log^3 n)'):
        return {
            'why_this_complexity': (
                f"This is {tc} because several logarithmic loops multiply together. "
                "Each loop repeatedly doubles or halves a value, so each level contributes a log n factor."
            ),
            'real_world_analogy': (
                "It is like repeatedly folding a paper stack, then doing another folding-style process inside each fold level."
            ),
            'performance_impact': (
                "This is still very scalable: even huge n values have small logarithms. "
                "It grows faster than one binary-search-style loop, but far slower than linear time."
            ),
            'top_optimization': _first_optimization(
                analysis_result,
                "No major asymptotic optimization is needed unless the repeated logarithmic passes can be merged."
            )
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
        'O(k³ log n)': {
            'why_this_complexity': 'Matrix exponentiation detected: the exponent is reduced by squaring in O(log n) levels, and each level performs one k by k matrix multiplication costing O(k³).',
            'real_world_analogy': 'Like folding the exponent in half again and again, but paying for a full matrix multiplication at each fold.',
            'performance_impact': 'Excellent when the exponent is large: doubling the exponent only adds one more matrix multiplication level.',
            'top_optimization': 'Use a tuned matrix multiplication backend such as NumPy/BLAS; for very large matrices, consider blocking or Strassen-style multiplication.'
        },
    }

    default = {
        'why_this_complexity': f'Analysis detected: {reason}. The complexity is {tc} based on the loop structure and algorithm pattern found in the code.',
        'real_world_analogy': 'The algorithm\'s growth rate determines how it handles larger inputs.',
        'performance_impact': f'With complexity {tc}, performance degrades as input size increases.',
        'top_optimization': 'Review the issues and optimizations sections for specific improvement suggestions.'
    }

    return explanations.get(tc, default)


def get_function_level_explanations(func_complexities, call_chain_report, language, function_details=None, code=None):
    """
    Generates per-function explanations for the call chain analysis.
    Analyzer data owns the facts; AI only writes the user-facing explanation text.
    """
    explanations = []

    if function_details:
        try:
            ai_explanations = _get_ai_function_explanations(
                function_details,
                call_chain_report,
                language,
                code or ''
            )
            if ai_explanations:
                return ai_explanations
        except Exception as e:
            _log_ai_error(f'AI function explanation error: {e}')

        detail_items = (
            function_details.values()
            if isinstance(function_details, dict)
            else function_details
        )
        for detail in detail_items:
            own = detail.get('own_complexity', detail.get('complexity', 'O(1)'))
            effective = detail.get('effective_complexity', detail.get('complexity', own))
            calls = detail.get('calls') or []
            explanations.append({
                'function': detail.get('function'),
                'complexity': effective,
                'own_complexity': own,
                'effective_complexity': effective,
                'calls': calls,
                'line': detail.get('line'),
                'snippet': detail.get('snippet') or '',
                'explanation': _explain_detailed_function(detail)
            })
        return explanations

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


def _get_ai_function_explanations(function_details, call_chain_report, language, code):
    prompt = _build_function_explanation_prompt(function_details, call_chain_report, language, code)
    content = _call_ai_completion(prompt, max_tokens=1500)
    if not content:
        return None
    parsed = _parse_function_explanation_json(content)
    if not parsed:
        return None
    return _merge_ai_function_explanations(function_details, parsed)


def _build_function_explanation_prompt(function_details, call_chain_report, language, code):
    detail_items = (
        list(function_details.values())
        if isinstance(function_details, dict)
        else list(function_details or [])
    )
    return f"""You are writing CodeScope's AI-powered Per-Function Complexity Breakdown for this {language} code.

CodeScope's analyzer already detected all complexity values. Do not recalculate, rename, simplify, upgrade, or downgrade any Big-O. Your only job is to make each function explanation specific, professional, and helpful for the user's exact code. You are the explanation layer, not the detector.

CODE:
```{language}
{(code or '')[:3500]}
```

ANALYZER FUNCTION FACTS:
{json.dumps(detail_items, ensure_ascii=False)}

CALL CHAIN REPORT:
{json.dumps(call_chain_report or [], ensure_ascii=False)}

For each function:
- Keep function, own_complexity, effective_complexity, complexity, and calls exactly as analyzer provided.
- Only mention Big-O values present in the provided analyzer facts for that function or its calls.
- Explain why the own complexity happens from the function body.
- If effective_complexity differs from own_complexity, explain which helper call causes the increase.
- If recursion exists, explain the recurrence/branching/depth instead of calling it a loop problem.
- If the function is an algorithm pattern such as matrix multiplication, DFS, DP, subset generation, sorting, regex, graph traversal, or backtracking, name the pattern.
- Do not give optimization code here; this section is for understanding the function.
- Use 1-3 concise sentences per explanation.

Return valid JSON only as an array. Each item must have:
function, complexity, own_complexity, effective_complexity, calls, explanation"""


def _parse_function_explanation_json(content):
    payload = _extract_json_payload(content)
    try:
        parsed = json.loads(payload)
    except Exception:
        return None
    if isinstance(parsed, dict):
        parsed = parsed.get('functions') or parsed.get('function_explanations') or parsed.get('items')
    return parsed if isinstance(parsed, list) else None


def _merge_ai_function_explanations(function_details, ai_items):
    detail_items = (
        list(function_details.values())
        if isinstance(function_details, dict)
        else list(function_details or [])
    )
    ai_by_name = {
        item.get('function'): item
        for item in ai_items
        if isinstance(item, dict) and item.get('function')
    }
    merged = []
    for detail in detail_items:
        name = detail.get('function')
        ai_item = ai_by_name.get(name, {})
        explanation = str(ai_item.get('explanation') or '').strip()
        own = detail.get('own_complexity', detail.get('complexity', 'O(1)'))
        effective = detail.get('effective_complexity', detail.get('complexity', own))
        if not explanation or _function_explanation_conflicts_with_facts(explanation, detail):
            explanation = _explain_detailed_function(detail)
        merged.append({
            'function': name,
            'complexity': effective,
            'own_complexity': own,
            'effective_complexity': effective,
            'calls': detail.get('calls') or [],
            'line': detail.get('line'),
            'snippet': detail.get('snippet') or '',
            'explanation': explanation
        })
    return merged


def _function_explanation_conflicts_with_facts(explanation, detail):
    fake_result = {
        'time_complexity': detail.get('effective_complexity') or detail.get('complexity'),
        'space_complexity': None,
        'function_complexity_details': [detail],
        'optimizations': [],
    }
    return _text_has_disallowed_complexity(explanation, _allowed_complexity_mentions(fake_result))


def _explain_detailed_function(detail):
    func_name = detail.get('function', 'function')
    own = detail.get('own_complexity', detail.get('complexity', 'O(1)'))
    effective = detail.get('effective_complexity', detail.get('complexity', own))
    reason = detail.get('reason') or ''
    calls = detail.get('calls') or []

    if 'Binary matrix exponentiation' in reason:
        helper = ''
        if calls:
            helper = ' ' + ' '.join(
                f"It calls {call.get('function')}() at {call.get('complexity')}."
                for call in calls
                if call.get('function')
            )
        return (
            f"{func_name}() has own/control cost {own} because the exponent is reduced by halving. "
            f"Its effective cost is {effective} because each recursive level performs one k by k matrix multiply.{helper} "
            f"{reason}"
        ).strip()

    if 'Naive square matrix multiplication' in reason:
        return (
            f"{func_name}() is the cubic helper: it fills k² result cells, and each cell computes a length-k dot product. "
            f"That gives own/effective cost {effective} and allocates the k by k result matrix."
        )

    if own != effective:
        call_text = ''
        if calls:
            parts = [
                f"{call.get('function')}() at {call.get('complexity')}"
                for call in calls
                if call.get('function')
            ]
            if parts:
                call_text = f" It calls {', '.join(parts)}."
        return (
            f"{func_name}() has own/control cost {own}, but its effective cost is {effective} "
            f"after including helper calls.{call_text} {reason}"
        ).strip()

    if reason:
        return reason
    return _explain_single_function(func_name, effective, None)


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
