import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import ComplexityBadge from '../components/ComplexityBadge';
import { downloadReport, getApiErrorMessage, getModifiedCode } from '../services/api';

const getSafeFilename = (data, fallback = 'Unknown File') => {
  const filename = data?.filename || data?.result?.filename || fallback;
  return typeof filename === 'string' && filename.trim() ? filename : fallback;
};

const formatCode = (code) => String(code || '')
  .replace(/\r\n/g, '\n')
  .replace(/\t/g, '  ')
  .trim();

const lineIndent = (line = '') => {
  const expanded = String(line).replace(/\t/g, '    ');
  return expanded.length - expanded.trimStart().length;
};

const looksLikeNextFunction = (line = '') => {
  const text = String(line).trim();
  return (
    /^(?:async\s+def|def|class)\s+\w+/.test(text) ||
    /^(?:function\s+\*?\s+\w+|(?:const|let|var)\s+\w+\s*=)/.test(text) ||
    /^(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:void|int|long|double|float|boolean|bool|char|String|[\w:<>,\s*&]+)\s+\w+\s*\([^;]*\)\s*\{?/.test(text)
  );
};

const exactFunctionSnippet = (snippet = '') => {
  const lines = formatCode(snippet).split('\n');
  if (lines.length <= 1) return formatCode(snippet);

  const firstContentIndex = lines.findIndex(line => line.trim());
  if (firstContentIndex === -1) return '';

  const baseIndent = lineIndent(lines[firstContentIndex]);
  let seenBody = false;
  let parenDepth = 0;
  let braceDepth = 0;

  for (let index = firstContentIndex; index < lines.length; index += 1) {
    const line = lines[index];
    const text = line.trim();
    const indent = lineIndent(line);

    if (index > firstContentIndex && text) {
      const sameOrOuterIndent = indent <= baseIndent;
      const atPythonBoundary = parenDepth <= 0 && sameOrOuterIndent && (
        looksLikeNextFunction(line) ||
        (seenBody && text.startsWith('#'))
      );
      const atBraceBoundary = braceDepth <= 0 && looksLikeNextFunction(line);

      if (atPythonBoundary || atBraceBoundary) {
        return lines.slice(0, index).join('\n').trim();
      }
    }

    if (text && index > firstContentIndex) {
      seenBody = true;
    }

    parenDepth += (line.match(/[([{]/g) || []).length;
    parenDepth -= (line.match(/[)\]}]/g) || []).length;
    braceDepth += (line.match(/{/g) || []).length;
    braceDepth -= (line.match(/}/g) || []).length;
  }

  return lines.join('\n').trim();
};

const normalizeComplexity = (value = '') => String(value)
  .toLowerCase()
  .replace(/\s+/g, '')
  .replace(/\u00b2/g, '^2')
  .replace(/\u00b3/g, '^3')
  .replace(/\u00d7/g, '*')
  .replace(/\u03c6/g, 'phi')
  .replace(/\u00c2\u00b2/g, '^2')
  .replace(/\u00c2\u00b3/g, '^3')
  .replace(/\u00c3\u2014/g, '*')
  .replace(/\u00c2/g, '');

const complexityRank = (value = '') => {
  const label = normalizeComplexity(value);
  if (!label || label.includes('unknown')) return 0;
  if (label.includes('ackermann')) return 12;
  if (label.includes('n!')) return 11;
  if (label.includes('3^n')) return 10;
  if (label.includes('2^n') || label.includes('phi')) return 9;
  if (label.includes('n^3') || label.includes('v^3')) return 8;
  if (label.includes('n^2log')) return 7;
  if (label.includes('n^2') || label.includes('v*e') || label.includes('n*w')) return 6;
  if (label.includes('nlog') || label.includes('(v+e)log') || label.includes('elog')) return 4;
  if (label.includes('v+e') || label.includes('n+k') || label.includes('n+m') || label.includes('o(n)')) return 3;
  if (label.includes('sqrt')) return 2;
  if (label.includes('log')) return 1;
  return label.includes('n') ? 3 : 0;
};

const aliasesFor = (name = '') => {
  const raw = String(name || '').trim().toLowerCase();
  if (!raw) return [];
  return Array.from(new Set([raw, raw.split('.').pop()].filter(Boolean)));
};

const namesMatch = (left = '', right = '') => {
  const rightAliases = new Set(aliasesFor(right));
  return aliasesFor(left).some(alias => rightAliases.has(alias));
};

const escapeRegExp = (value = '') => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const codeMentionsFunction = (code = '', functionName = '') => {
  const text = String(code || '');
  return aliasesFor(functionName).some(alias => {
    const escaped = escapeRegExp(alias);
    return (
      new RegExp(`\\b${escaped}\\s*\\(`, 'i').test(text) ||
      new RegExp(`\\bdef\\s+${escaped}\\s*\\(`, 'i').test(text) ||
      new RegExp(`\\bfunction\\s+${escaped}\\s*\\(`, 'i').test(text)
    );
  });
};

const normalizeAiSolution = (solution) => {
  if (!solution) return null;
  const code = solution.code || solution.example;
  if (!code) return null;
  return {
    ...solution,
    code,
    source_label: solution.source_label || solution.source || 'AI',
  };
};

const uniqueSolutions = (solutions) => {
  const seen = new Set();
  return solutions.filter(solution => {
    const key = [
      String(solution.function || '').toLowerCase(),
      formatCode(solution.code),
      solution.complexity_before || '',
      solution.complexity_after || '',
    ].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const functionRowsFor = (result) => {
  const details = Array.isArray(result?.function_complexity_details)
    ? result.function_complexity_details
    : [];
  const explanations = Array.isArray(result?.function_explanations)
    ? result.function_explanations
    : [];

  if (details.length === 0) {
    return explanations.map(item => ({
      ...item,
      own_complexity: item.own_complexity || item.complexity || 'O(unknown)',
      effective_complexity: item.effective_complexity || item.complexity || item.own_complexity || 'O(unknown)',
      complexity: item.effective_complexity || item.complexity || item.own_complexity || 'O(unknown)',
      snippet: item.snippet || '',
      calls: item.calls || [],
    }));
  }

  return details.map(detail => {
    const explanation = explanations.find(item => namesMatch(item?.function, detail.function)) || {};
    const own = detail.own_complexity || detail.complexity || explanation.own_complexity || explanation.complexity || 'O(unknown)';
    const effective = detail.effective_complexity || detail.complexity || explanation.effective_complexity || explanation.complexity || own;
    return {
      ...explanation,
      ...detail,
      own_complexity: own,
      effective_complexity: effective,
      complexity: effective,
      explanation: detail.reason || explanation.explanation || '',
      snippet: detail.snippet || explanation.snippet || '',
      calls: detail.calls || explanation.calls || [],
    };
  });
};

const hotspotsFor = (result, functionRows) => {
  const raw = Array.isArray(result?.hotspots) ? result.hotspots : [];
  const ranked = functionRows.length > 0
    ? functionRows.map(fn => {
      const hotspot = raw.find(item => namesMatch(item.function, fn.function)) || {};
      const complexity = fn.effective_complexity || fn.complexity || fn.own_complexity || hotspot.complexity;
      return {
        function: fn.function,
        line: fn.line || hotspot.line || 1,
        complexity,
        reason: fn.explanation || hotspot.reason || '',
        snippet: fn.snippet || hotspot.snippet || '',
        ai_solution: hotspot.ai_solution || fn.ai_solution,
        ai_solutions: fn.ai_solutions || [],
        rank: complexityRank(complexity),
      };
    })
    : raw.map(hotspot => ({
      ...hotspot,
      rank: complexityRank(hotspot.complexity),
    }));

  const rankedHotspots = ranked.filter(item => item.function && item.rank > 0);

  if (rankedHotspots.length === 0) return [];
  const maxRank = Math.max(...rankedHotspots.map(item => item.rank));
  return rankedHotspots
    .filter(item => item.rank === maxRank)
    .map(item => ({
      function: item.function,
      line: item.line,
      complexity: item.complexity,
      reason: item.reason,
      snippet: item.snippet,
      ai_solution: item.ai_solution,
      ai_solutions: item.ai_solutions || [],
    }));
};

const aiSolutionsFor = (result, hotspots, functionRows) => {
  const aiTransformed = result?.ai_transformed_code;
  const optimizations = Array.isArray(result?.optimizations) ? result.optimizations : [];
  const aiOptimizedFunctions = Array.isArray(result?.ai_optimized_functions)
    ? result.ai_optimized_functions
    : [];

  const candidates = [
    aiTransformed?.available ? aiTransformed : null,
    ...aiOptimizedFunctions,
    ...optimizations.filter(opt => opt?.ai_generated && (opt?.example || opt?.code)),
    ...hotspots.map(item => item.ai_solution),
    ...functionRows.map(item => item.ai_solution),
  ].map(normalizeAiSolution).filter(Boolean);

  return uniqueSolutions(candidates).map(solution => {
    if (solution.function) return solution;
    const matched = functionRows.find(fn =>
      codeMentionsFunction(solution.code, fn.function) ||
      aliasesFor(fn.function).some(alias =>
        `${solution.title || ''} ${solution.description || ''} ${solution.solution || ''}`.toLowerCase().includes(alias)
      )
    );
    return matched ? { ...solution, function: matched.function } : solution;
  });
};

const functionTextFor = (solution = '') => (
  `${solution.title || ''} ${solution.description || ''} ${solution.solution || ''} ${solution.problem || ''} ${solution.notes || ''}`
).toLowerCase();

const solutionMatchesFunction = (solution, fn) => {
  if (!solution || !fn?.function) return false;
  if (solution.function && namesMatch(solution.function, fn.function)) return true;
  if (codeMentionsFunction(solution.code, fn.function)) return true;

  const text = functionTextFor(solution);
  return aliasesFor(fn.function).some(alias => text.includes(alias));
};

const attachSolutionsToFunctions = (functions, solutions) => {
  const rows = functions.map(fn => ({ ...fn, ai_solutions: [] }));

  solutions.forEach(solution => {
    let target = rows.find(fn => solutionMatchesFunction(solution, fn));

    if (!target && rows.length === 1) {
      target = rows[0];
    }

    if (!target && solution.complexity_before) {
      target = rows.find(fn => (
        fn.effective_complexity === solution.complexity_before ||
        fn.own_complexity === solution.complexity_before ||
        fn.complexity === solution.complexity_before
      ));
    }

    if (!target) return;
    target.ai_solutions.push(solution);
  });

  return rows.map(fn => ({
    ...fn,
    ai_solutions: uniqueSolutions(fn.ai_solutions),
  }));
};

const isGroqFailureReason = (reason = '') => (
  /\b(?:groq|grok).*(?:error|connection|unavailable|key|timeout|failed)|no groq|no grok/i.test(String(reason || ''))
);

function ResultOverview({ functions, hotspots, hasAiSolutions }) {
  const stats = [
    ['Functions', functions.length],
    ['Hotspots', hotspots.length],
    ['Modified', hasAiSolutions ? 'Ready' : 'On request'],
  ];

  return (
    <section className="result-index">
      {stats.map(([label, value]) => (
        <div key={label} className="index-stat">
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function ComplexitySummary({ result, filename }) {
  const overall = result?.overall_complexity || {};
  const allocation = result?.memory_allocation_analysis || {};
  const time = overall.scalable_time || overall.time || result?.time_complexity || 'O(unknown)';
  const space = overall.scalable_space || overall.space || result?.space_complexity || 'O(unknown)';
  const totalAllocatedSpace = overall.total_allocation || allocation.total_allocated_space;
  const showTotalAllocated = totalAllocatedSpace && totalAllocatedSpace !== space;

  return (
    <section className="card summary-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '18px', flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0, flex: '1 1 280px' }}>
          <div style={{ fontSize: '12px', color: 'var(--primary)', fontWeight: '800', textTransform: 'uppercase', marginBottom: '6px' }}>
            CodeScope Complexity
          </div>
          <h2 style={{ fontSize: '20px', lineHeight: '1.35', margin: 0, color: 'var(--dark)', overflowWrap: 'anywhere' }}>
            {filename}
          </h2>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '10px', fontSize: '13px', color: 'var(--gray)' }}>
            <span>{String(result?.language || 'unknown').toUpperCase()}</span>
            <span>{result?.lines_of_code || 0} lines</span>
            {typeof result?.rating === 'number' && <span>Rating {result.rating}/10</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <MetricBadge label="Big O Time" value={time} />
          <MetricBadge label="Big O Space" value={space} />
          {showTotalAllocated && (
            <MetricBadge label="Total Allocated Space" value={totalAllocatedSpace} />
          )}
        </div>
      </div>
    </section>
  );
}

function MetricBadge({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '800', textTransform: 'uppercase', marginBottom: '5px' }}>
        {label}
      </div>
      <ComplexityBadge complexity={value} />
    </div>
  );
}

function HotCodeSection({ hotspots }) {
  return (
    <section className="card report-section">
      <div className="report-section-head">
        <div>
          <span className="eyebrow">Highest complexity</span>
          <h3>Hot Code Sections</h3>
        </div>
      </div>
      {hotspots.length === 0 ? (
        <p className="empty-state">
          No high-complexity hotspot was detected for this file.
        </p>
      ) : hotspots.map((hotspot, index) => {
        const aiSolutions = uniqueSolutions([
          ...(hotspot.ai_solutions || []),
          normalizeAiSolution(hotspot.ai_solution),
        ].filter(Boolean));

        return (
          <div key={`${hotspot.function || 'hotspot'}-${index}`} className="hotspot-card" style={{ marginBottom: index < hotspots.length - 1 ? '12px' : 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
              <div style={{ fontFamily: 'var(--font-code)', fontSize: '13px', fontWeight: '800', overflowWrap: 'anywhere' }}>
                {hotspot.function || 'file scope'}{hotspot.function ? '()' : ''} at line {hotspot.line || 1}
              </div>
              <ComplexityBadge complexity={hotspot.complexity || 'O(unknown)'} />
            </div>
            {hotspot.reason && (
              <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: '0 0 10px' }}>
                {hotspot.reason}
              </p>
            )}
            {hotspot.snippet && <CodeBlock code={exactFunctionSnippet(hotspot.snippet)} dark />}
            {aiSolutions.map((solution, solutionIndex) => (
              <FunctionAiRewrite
                key={`${solution.function || hotspot.function || 'hotspot-rewrite'}-${solutionIndex}`}
                solution={solution}
              />
            ))}
          </div>
        );
      })}
    </section>
  );
}

function FunctionBreakdown({ functions, groqStatus = '' }) {
  const hasAiSolution = functions.some(fn => Array.isArray(fn.ai_solutions) && fn.ai_solutions.length > 0);

  return (
    <section className="card report-section">
      <div className="report-section-head">
        <div>
          <span className="eyebrow">Function table</span>
          <h3>Function-by-Function Complexity</h3>
        </div>
      </div>
      {groqStatus && !hasAiSolution && (
        <div style={{
          padding: '10px 12px',
          borderRadius: '8px',
          border: '1px solid #fbbc04',
          background: '#fff8e1',
          color: '#8a5a00',
          fontSize: '13px',
          marginBottom: '12px',
        }}>
          {groqStatus}
        </div>
      )}
      {functions.length === 0 ? (
        <p className="empty-state">
          No named functions were detected. The file-level complexity is shown above.
        </p>
      ) : functions.map((fn, index) => (
        <div key={`${fn.function || 'function'}-${index}`} className="function-row" style={{
          borderBottom: index < functions.length - 1 ? '1px solid var(--border)' : 'none',
        }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-code)', fontSize: '13px', fontWeight: '800', color: 'var(--primary)', overflowWrap: 'anywhere' }}>
              {fn.function || 'file scope'}{fn.function ? '()' : ''}
            </div>
            {fn.line && (
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '4px' }}>
                line {fn.line}
              </div>
            )}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: fn.explanation ? '8px' : 0 }}>
              <MetricBadge label="Direct Time" value={fn.own_complexity || fn.complexity || 'O(unknown)'} />
              <MetricBadge label="With Calls" value={fn.effective_complexity || fn.complexity || fn.own_complexity || 'O(unknown)'} />
            </div>
            {fn.explanation && (
              <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: 0, overflowWrap: 'anywhere' }}>
                {fn.explanation}
              </p>
            )}
            {fn.snippet && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '800', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Function Code
                </div>
                <CodeBlock code={exactFunctionSnippet(fn.snippet)} />
              </div>
            )}
            {fn.ai_solutions?.map((solution, solutionIndex) => (
              <FunctionAiRewrite
                key={`${solution.function || fn.function || 'rewrite'}-${solutionIndex}`}
                solution={solution}
              />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function FunctionAiRewrite({ solution }) {
  return (
    <div className="rewrite-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: '11px', color: 'var(--success)', fontWeight: '800', textTransform: 'uppercase', marginBottom: '4px' }}>
            {solution.source_label || 'AI'} Modified Function
          </div>
          <div style={{ fontFamily: 'var(--font-code)', fontSize: '13px', fontWeight: '800', overflowWrap: 'anywhere' }}>
            {solution.title || 'Lower-complexity rewrite'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {solution.complexity_before && <MetricBadge label="Before" value={solution.complexity_before} />}
          {solution.complexity_after && <MetricBadge label="After" value={solution.complexity_after} />}
        </div>
      </div>
      {(solution.description || solution.solution || solution.notes) && (
        <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: '0 0 10px' }}>
          {solution.description || solution.solution || solution.notes}
        </p>
      )}
      <CodeBlock code={solution.code} success />
    </div>
  );
}

function ModifiedCodeAction({ loading, error, hasSolutions, onClick }) {
  return (
    <section className="card modified-action">
      {error && (
        <div style={{ flex: '1 1 260px', color: '#b42318', fontSize: '13px', lineHeight: '1.5' }}>
          {error}
        </div>
      )}
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="btn btn-primary"
        style={{ opacity: loading ? 0.75 : 1 }}
      >
        {loading ? 'Getting Modified Code...' : hasSolutions ? 'Refresh Modified Code' : 'Get Modified Code'}
      </button>
    </section>
  );
}

function CodeBlock({ code, success = false }) {
  return (
    <pre className={`code-block ${success ? 'success-code' : ''}`}>{formatCode(code)}</pre>
  );
}

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const stateData = location.state || {};
  const [currentResult, setCurrentResult] = useState(stateData.result);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');
  const [modifiedLoading, setModifiedLoading] = useState(false);
  const [modifiedError, setModifiedError] = useState('');
  const [selectedFile, setSelectedFile] = useState(0);

  const result = currentResult;
  const type = stateData.type;
  const isCodeResult = type === 'code' || (!type && !Array.isArray(result?.files));

  if (!result) {
    return <Navigate to="/analyze" replace />;
  }

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError('');
    try {
      const reportData = type === 'code'
        ? { ...result, filename: getSafeFilename(result) }
        : {
            ...result,
            files: Array.isArray(result?.files)
              ? result.files.map((file, index) => ({
                  ...file,
                  filename: getSafeFilename(file, `File ${index + 1}`),
                }))
              : [],
          };
      await downloadReport(reportData, type);
    } catch (err) {
      setDownloadError(err?.message || 'PDF download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const handleGetModifiedCode = async () => {
    const sourceCode = result?.source_code || stateData.source_code || '';
    const filename = result?.filename || 'code.py';

    if (!sourceCode.trim()) {
      setModifiedError('Original pasted code is not available for this result. Please analyze the code again.');
      return;
    }

    setModifiedLoading(true);
    setModifiedError('');
    try {
      const payload = await getModifiedCode(
        sourceCode,
        filename,
        result?.concrete_inputs || stateData.concrete_inputs || ''
      );
      setCurrentResult({
        ...payload,
        source_code: sourceCode,
        concrete_inputs: result?.concrete_inputs || stateData.concrete_inputs || '',
      });
    } catch (err) {
      setModifiedError(getApiErrorMessage(err, 'Could not get modified code from Groq. Please try again.'));
    } finally {
      setModifiedLoading(false);
    }
  };

  const renderSingleResult = (data, filename) => {
    const fileResult = data?.result || data || {};
    const safeFilename = filename || getSafeFilename(data);
    const functions = functionRowsFor(fileResult);
    const initialHotspots = hotspotsFor(fileResult, functions);
    const aiSolutions = aiSolutionsFor(fileResult, initialHotspots, functions);
    const functionsWithAiSolutions = attachSolutionsToFunctions(functions, aiSolutions);
    const hotspots = hotspotsFor(fileResult, functionsWithAiSolutions);
    const groqReason = fileResult?.ai_transformed_code?.reason || '';
    const groqStatus = isGroqFailureReason(groqReason) ? groqReason : '';
    const hasAiSolutions = functionsWithAiSolutions.some(fn => (
      Array.isArray(fn.ai_solutions) && fn.ai_solutions.length > 0
    ));

    return (
      <div data-filename={safeFilename}>
        <ResultOverview functions={functionsWithAiSolutions} hotspots={hotspots} hasAiSolutions={hasAiSolutions} />
        <ComplexitySummary result={fileResult} filename={safeFilename} />
        <HotCodeSection hotspots={hotspots} />
        <FunctionBreakdown functions={functionsWithAiSolutions} groqStatus={groqStatus} />
        {isCodeResult && (
          <ModifiedCodeAction
            loading={modifiedLoading}
            error={modifiedError}
            hasSolutions={hasAiSolutions}
            onClick={handleGetModifiedCode}
          />
        )}
      </div>
    );
  };

  const renderMultiResult = () => {
    const files = Array.isArray(result?.files) ? result.files : [];
    const projectSummary = result?.project_summary || {};
    const selected = files[selectedFile] || files[0];

    return (
      <div>
        <section className="card summary-card">
          <h2 style={{ fontSize: '18px', fontWeight: '800', margin: '0 0 14px' }}>
            Project Complexity
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '12px',
          }}>
            {[
              ['Files', result?.total_files || files.length || 0],
              ['Lines', result?.total_lines || 0],
              ['Worst Time', projectSummary.worst_time_complexity || 'O(unknown)'],
              ['Average Rating', `${result?.average_rating || 0}/10`],
            ].map(([label, value]) => (
              <div key={label} className="project-stat">
                <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '800', textTransform: 'uppercase', marginBottom: '5px' }}>
                  {label}
                </div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: 'var(--dark)', overflowWrap: 'anywhere' }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="card report-section">
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '14px' }}>
            Files Analyzed ({files.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
            {files.map((file, index) => (
              <button
                key={`${getSafeFilename(file, `File ${index + 1}`)}-${index}`}
                onClick={() => setSelectedFile(index)}
                className={`file-chip ${selectedFile === index ? 'active' : ''}`}
              >
                {getSafeFilename(file, `File ${index + 1}`).split('/').pop()}
              </button>
            ))}
          </div>
          {selected
            ? renderSingleResult(selected, selected.filename)
            : <p style={{ fontSize: '13px', color: 'var(--gray)', margin: 0 }}>No files were returned for this analysis.</p>}
        </section>
      </div>
    );
  };

  return (
    <div className="page-shell results-page">
      <div className="container">
        <div className="results-header">
          <div>
            <div className="eyebrow">Complexity report</div>
            <h1>
              Analysis Results
            </h1>
            <p>
              {isCodeResult && `File: ${result?.filename || 'Unknown'}`}
              {type === 'zip' && `ZIP file - ${result?.total_files || 0} files analyzed`}
              {type === 'github' && `GitHub: ${result?.github_url || 'Unknown'}`}
            </p>
          </div>

          <div className="result-toolbar">
            <button
              onClick={() => navigate('/analyze')}
              className="btn btn-outline"
            >
              Analyze Another
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn btn-primary"
              style={{ opacity: downloading ? 0.75 : 1 }}
            >
              {downloading ? 'Generating...' : 'Download PDF'}
            </button>
          </div>
        </div>

        {downloadError && (
          <div className="error-box" style={{ marginBottom: '18px' }}>
            {downloadError}
          </div>
        )}

        {isCodeResult && renderSingleResult(result, result?.filename)}
        {(type === 'zip' || type === 'github') && renderMultiResult()}
      </div>
    </div>
  );
}
