import { useLocation, useNavigate } from 'react-router-dom';
import RatingGauge from '../components/RatingGauge';
import ComplexityBadge from '../components/ComplexityBadge';
import IssueCard from '../components/IssueCard';
import { downloadReport } from '../services/api';
import { useState } from 'react';

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(0);

  // Safe state extraction
  const stateData = location.state || {};
  const result = stateData.result;
  const type = stateData.type;

  const getSafeFilename = (data, fallback = 'Unknown File') => {
    const filename = data?.filename || data?.result?.filename || fallback;
    return typeof filename === 'string' && filename.trim() ? filename : fallback;
  };

  const formatDisplayCode = (code) => {
    if (typeof code !== 'string') return '';

    return code
      .replace(/\r\n/g, '\n')
      .replace(/\t/g, '  ')
      .trim();
  };

  if (!result) {
    navigate('/analyze');
    return null;
  }

  const handleDownload = async () => {
    setDownloading(true);
    try {
      if (!result || !type) {
        alert('No result data available. Please analyze code first.');
        return;
      }

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
      console.error("Download error:", err);
      alert('PDF download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  // Single file result - FIXED with safe access
  const renderSingleResult = (data, filename) => {
    const r = data?.result || data || {};

    // Safe defaults for missing properties
    const rating = r?.rating || 0;
    const overall = r?.overall_complexity || {};
    const time_complexity = r?.time_complexity || 'Unknown';
    const space_complexity = r?.space_complexity || 'Unknown';
    const language = r?.language || 'Unknown';
    const lines_of_code = r?.lines_of_code || 0;
    const issues = Array.isArray(r?.issues) ? r.issues : [];
    const concrete = r?.concrete_analysis;
    const inputEffect = r?.input_effect_analysis;
    const amortized = r?.amortized_analysis;
    const allocation = r?.memory_allocation_analysis;
    const displaySpace = overall.space || space_complexity;
    const peakSpace = overall.peak_space || displaySpace;
    const totalAllocation = overall.total_allocation || allocation?.total_allocated_space;
    const hasDistinctAllocation = totalAllocation && totalAllocation !== displaySpace;
    const hasDistinctPeak = peakSpace && peakSpace !== displaySpace;
    const confidence = r?.analysis_confidence;
    const confidenceDetail = !Array.isArray(confidence?.notes) || confidence.notes.length === 0
      ? confidence?.reason || ''
      : '';
    const hotspots = Array.isArray(r?.hotspots) ? r.hotspots : [];
    const aiTransformed = r?.ai_transformed_code;
    const optimizedCode = aiTransformed?.available ? aiTransformed : null;
    const optimizedByAi = Boolean(aiTransformed?.available);
    const hasIssueGrokSolution = issues.some((issue) => Boolean(issue?.grok_solution?.code));
    //const suggestions = Array.isArray(r?.suggestions) ? r.suggestions : [];
    const safeFilename = filename || getSafeFilename(data);

    return (
      <div data-filename={safeFilename}>
        {/* Total Complexity */}
        <div className="card" style={{
          padding: '22px 24px',
          marginBottom: '20px',
          border: '1px solid var(--primary)',
          background: '#f8fbff'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '18px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 0, flex: '1 1 320px' }}>
              <div style={{ fontSize: '13px', color: 'var(--primary)', marginBottom: '8px', fontWeight: '700', textTransform: 'uppercase' }}>
                Total Complexity
              </div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark)', lineHeight: '1.4', overflowWrap: 'anywhere' }}>
                {overall.headline || `${time_complexity} time, ${displaySpace} space`}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '8px', lineHeight: '1.5' }}>
                {overall.memory_model || (
                  hasDistinctAllocation
                    ? `Space complexity is ${displaySpace}; total allocated/copied memory over the run is ${totalAllocation}.`
                    : `Space complexity is ${displaySpace}.`
                )}
              </div>
              {confidence && (
                <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '6px', lineHeight: '1.5' }}>
                  Confidence: time {confidence.time || 'medium'}, space {confidence.space || 'medium'}
                  {confidenceDetail ? ` - ${confidenceDetail}` : ''}
                  {Array.isArray(confidence.notes) && confidence.notes.length > 0 ? ` — ${confidence.notes.join(' ')}` : ''}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Time
                </div>
                <ComplexityBadge complexity={overall.time || time_complexity} />
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Space
                </div>
                <ComplexityBadge complexity={displaySpace} />
              </div>
              {totalAllocation && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Total Allocation
                  </div>
                  <ComplexityBadge complexity={totalAllocation} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Metrics row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {/* Rating */}
          <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Performance Rating
            </div>
            <RatingGauge rating={rating} />
          </div>

          {/* Time Complexity */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Time Complexity
            </div>
            <ComplexityBadge complexity={time_complexity} />
            <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '10px', lineHeight: '1.5' }}>
              How execution time grows as input size increases
            </div>
          </div>

          {/* Space Complexity */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Space Complexity
            </div>
            <ComplexityBadge complexity={displaySpace} />
            <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '10px', lineHeight: '1.5' }}>
              {r.space_complexity_reason || 'How peak memory usage grows as input size increases'}
            </div>
            {hasDistinctPeak && (
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '8px', lineHeight: '1.5' }}>
                Peak live auxiliary memory: <strong style={{ color: 'var(--dark)' }}>{peakSpace}</strong>
              </div>
            )}
            {hasDistinctAllocation && (
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '8px', lineHeight: '1.5' }}>
                Total allocated/copied over the full run: <strong style={{ color: 'var(--dark)' }}>{totalAllocation}</strong>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Code Stats
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Language</span>
                <span style={{ fontSize: '13px', fontWeight: '600', textTransform: 'uppercase' }}>
                  {language.toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Lines of Code</span>
                <span style={{ fontSize: '13px', fontWeight: '600' }}>{lines_of_code}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Issues Found</span>
                <span style={{ fontSize: '13px', fontWeight: '600', color: issues.length > 0 ? 'var(--danger)' : 'var(--success)' }}>
                  {issues.length}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr)',
          gap: '20px',
          marginBottom: '20px'
        }}>
          {/* Concrete Input Analysis */}
          {concrete && (
            <div className="card" style={{ border: '1px solid var(--primary)', background: '#f8fbff' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
                Concrete Input Result
              </h3>
              {concrete.available ? (
                <>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                    gap: '12px',
                    marginBottom: '12px'
                  }}>
                    {[
                      ['Function', `${concrete.function}()`],
                      ['Inputs', Object.entries(concrete.inputs || {}).map(([k, v]) => `${k}=${v}`).join(', ')],
                      ['Return Value', concrete.return_value],
                      ['Time', concrete.time],
                      ['Space', concrete.space],
                      ['Fixed Big-O', `${concrete.fixed_input_time_complexity} time, ${concrete.fixed_input_space_complexity} space`],
                    ].map(([label, value]) => (
                      <div key={label} style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                        <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                          {label}
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--dark)', fontWeight: '600', fontFamily: 'var(--font-code)', overflowWrap: 'anywhere' }}>
                          {String(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: 0 }}>
                    {concrete.reason}. Symbolic growth remains {concrete.symbolic_time_complexity} when inputs are variable.
                  </p>
                </>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--dark)', lineHeight: '1.6', margin: 0 }}>
                  {concrete.reason || 'Exact concrete analysis is unavailable for these inputs.'}
                </p>
              )}
            </div>
          )}

          {/* Broad Input Impact Estimate */}
          {inputEffect && (
            <div className="card" style={{ border: '1px solid var(--border)', background: '#fbfcff' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
                Input Impact Estimate
              </h3>
              {inputEffect.available ? (
                <>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                    gap: '12px',
                    marginBottom: '12px'
                  }}>
                    {[
                      ['Detected Sizes', Object.entries(inputEffect.input_sizes?.dimensions || {}).map(([k, v]) => `${k}=${v}`).join(', ') || 'N/A'],
                      ['Graph Size', inputEffect.input_sizes?.graph && Object.keys(inputEffect.input_sizes.graph).length ? `V=${inputEffect.input_sizes.graph.V}, E=${inputEffect.input_sizes.graph.E}` : 'N/A'],
                      ['Dominant Size', inputEffect.dominant_size],
                      ['Estimated Time', inputEffect.estimated_time_units],
                      ['Time Formula', inputEffect.time_formula],
                      ['Estimated Space', inputEffect.estimated_space_units],
                    ].map(([label, value]) => (
                      <div key={label} style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                        <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                          {label}
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--dark)', fontWeight: '600', fontFamily: 'var(--font-code)', overflowWrap: 'anywhere' }}>
                          {String(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: 0 }}>
                    {inputEffect.reason}
                  </p>
                </>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--dark)', lineHeight: '1.6', margin: 0 }}>
                  {inputEffect.reason || 'Input impact estimate is unavailable for these values.'}
                </p>
              )}
            </div>
          )}

          {/* Amortized Analysis */}
          {amortized && (
            <div className="card" style={{ border: '1px solid #b7dfbf', background: '#f6fff8' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
                Amortized Analysis
              </h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '12px',
                marginBottom: '12px'
              }}>
                {[
                  ['Pattern', amortized.pattern],
                  ['Worst Operation', amortized.per_operation_worst],
                  ['Amortized Operation', amortized.amortized_per_operation],
                  ['Total Cost', amortized.total_for_n_ops],
                  ['Worst Total', amortized.worst_total_for_n_ops],
                ].filter(([, value]) => value !== undefined && value !== null && value !== '').map(([label, value]) => (
                  <div key={label} style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                      {label}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--dark)', fontWeight: '600', fontFamily: 'var(--font-code)', overflowWrap: 'anywhere' }}>
                      {String(value || 'N/A')}
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--dark)', lineHeight: '1.6', margin: 0 }}>
                {amortized.reason}
              </p>
            </div>
          )}

          {/* Memory Allocation Analysis */}
          {allocation && (
            <div className="card" style={{ border: '1px solid #d7c7ff', background: '#fbf9ff' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
                Memory Allocation Pressure
              </h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '12px',
                marginBottom: '12px'
              }}>
                {[
                  ['Pattern', allocation.pattern],
                  ['Peak Live Space', allocation.peak_live_auxiliary_space],
                  ['Total Allocated', allocation.total_allocated_space],
                  ['Per Level', allocation.per_level_allocation],
                  ['Levels', allocation.recursion_levels],
                ].map(([label, value]) => (
                  <div key={label} style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--gray)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                      {label}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--dark)', fontWeight: '600', fontFamily: 'var(--font-code)', overflowWrap: 'anywhere' }}>
                      {String(value || 'N/A')}
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--dark)', lineHeight: '1.6', margin: 0 }}>
                {allocation.reason}
              </p>
            </div>
          )}

          {/* AI Explanation */}
          {r.ai_explanation && (
            <div
              className="card"
              style={{ background: 'linear-gradient(135deg, #e8f0fe, #f8f9fa)' }}
            >
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                🤖 AI Explanation
              </h3>
              {r.ai_explanation.why_this_complexity && (
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    Why this complexity?
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--dark)', lineHeight: '1.7' }}>
                    {r.ai_explanation.why_this_complexity}
                  </p>
                </div>
              )}
              {r.ai_explanation.real_world_analogy && (
                <div style={{ marginBottom: '14px', background: 'white', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    💡 Real World Analogy
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--dark)', lineHeight: '1.7', margin: 0 }}>
                    {r.ai_explanation.real_world_analogy}
                  </p>
                </div>
              )}
              {r.ai_explanation.performance_impact && (
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    📈 Performance Impact
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--dark)', lineHeight: '1.7' }}>
                    {r.ai_explanation.performance_impact}
                  </p>
                </div>
              )}
              {r.ai_explanation.top_optimization && (
                <div style={{ background: '#e6f4ea', padding: '12px', borderRadius: '8px', border: '1px solid #b7dfbf' }}>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--success)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    🎯 Top Optimization
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--dark)', lineHeight: '1.7', margin: 0 }}>
                    {r.ai_explanation.top_optimization}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Hotspots */}
          {hotspots.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                Hot Code Sections
              </h3>
              {hotspots.map((hotspot, i) => (
                <div key={i} style={{
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: i < hotspots.length - 1 ? '12px' : 0
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '700', fontFamily: 'var(--font-code)' }}>
                      {hotspot.function}() at line {hotspot.line}
                    </span>
                    <ComplexityBadge complexity={hotspot.complexity} />
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', margin: '0 0 10px' }}>
                    {hotspot.reason}
                  </p>
                  {hotspot.snippet && (
                    <pre style={{
                      margin: 0,
                      padding: '12px',
                      background: '#111827',
                      color: '#e5e7eb',
                      borderRadius: '8px',
                      overflowX: 'auto',
                      fontSize: '12px',
                      lineHeight: '1.5',
                      fontFamily: 'var(--font-code)'
                    }}>{formatDisplayCode(hotspot.snippet)}</pre>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Call Chain Report */}
          {r.call_chain_report && r.call_chain_report.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                🔗 Function Call Chain Analysis
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '14px' }}>
                These functions have higher effective complexity due to the functions they call:
              </p>
              {r.call_chain_report.map((chain, i) => (
                <div key={i} style={{
                  background: '#fef7e0',
                  border: '1px solid #fde68a',
                  borderRadius: '10px',
                  padding: '14px',
                  marginBottom: '10px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '13px', fontWeight: '700', fontFamily: 'var(--font-code)' }}>
                      {chain.function}()
                    </span>
                    <span style={{ background: '#e6f4ea', color: 'var(--success)', padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: '600' }}>
                      own: {chain.own_complexity}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--gray)' }}>→ calls →</span>
                    <span style={{ background: '#fce8e6', color: 'var(--danger)', padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: '600' }}>
                      effective: {chain.effective_complexity}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--dark)', margin: 0, lineHeight: '1.6' }}>
                    {chain.message}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Per Function Explanations */}
          {r.function_explanations && r.function_explanations.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                Per-Function Complexity Breakdown
              </h3>
              {r.function_explanations.map((fn, i) => (
                <div key={i} style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(120px, 180px) minmax(0, 1fr)',
                  gap: '12px 16px',
                  padding: '12px 0',
                  borderBottom: i < r.function_explanations.length - 1 ? '1px solid var(--border)' : 'none'
                }}>
                  <code style={{
                    background: 'var(--primary-light)',
                    color: 'var(--primary)',
                    padding: '3px 10px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '600',
                    whiteSpace: 'nowrap',
                    maxWidth: '100%',
                    overflowWrap: 'anywhere'
                  }}>
                    {fn.function}()
                  </code>
                  <div style={{ flex: '1 1 220px', minWidth: 0 }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                      <span style={{
                        fontSize: '12px',
                        fontWeight: '700',
                        fontFamily: 'var(--font-code)',
                        color: 'var(--dark)',
                        background: '#f8fafc',
                        border: '1px solid var(--border)',
                        borderRadius: '999px',
                        padding: '3px 8px'
                      }}>
                        own: {fn.own_complexity || fn.complexity}
                      </span>
                      {(fn.effective_complexity || fn.complexity) !== (fn.own_complexity || fn.complexity) && (
                        <span style={{
                          fontSize: '12px',
                          fontWeight: '700',
                          fontFamily: 'var(--font-code)',
                          color: 'var(--danger)',
                          background: '#fce8e6',
                          border: '1px solid #f6b8b3',
                          borderRadius: '999px',
                          padding: '3px 8px'
                        }}>
                          effective: {fn.effective_complexity || fn.complexity}
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6', overflowWrap: 'anywhere', margin: 0 }}>
                      {fn.explanation}
                    </p>
                    {fn.calls && fn.calls.length > 0 && (
                      <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {fn.calls.map((call, callIndex) => (
                          <span key={callIndex} style={{
                            fontSize: '11px',
                            fontFamily: 'var(--font-code)',
                            color: 'var(--primary)',
                            background: 'var(--primary-light)',
                            borderRadius: '999px',
                            padding: '3px 8px'
                          }}>
                            calls {call.function}() {call.multiplier && call.multiplier !== 'O(1)' ? `x ${call.multiplier}` : ''}{' -> '}{call.complexity}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Issues */}
        {issues.length > 0 && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              ⚠️ Issues Found ({issues.length})
            </h3>
            {issues.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))}
          </div>
        )}

        {/* Suggestions */}
        {/* Transformed Code */}
        {optimizedCode && optimizedCode.available && !hasIssueGrokSolution && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px' }}>
              {optimizedByAi ? 'Grok Optimized Version of Your Code' : '🔄 Optimized Version of Your Code'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px' }}>
              {optimizedCode.description} —
              <span style={{ color: 'var(--danger)', fontWeight: '600' }}>
                {' '}
                {optimizedCode.complexity_before}
              </span>
              {' → '}
              <span style={{ color: 'var(--success)', fontWeight: '600' }}>
                {optimizedCode.complexity_after}
              </span>
            </p>
            {optimizedByAi && optimizedCode.notes && (
              <p style={{ fontSize: '12px', color: 'var(--gray)', marginBottom: '12px', lineHeight: '1.5' }}>
                {optimizedCode.notes}
              </p>
            )}
            <pre style={{
              background: '#1e1e2e',
              color: '#cdd6f4',
              padding: '16px',
              borderRadius: '10px',
              fontSize: '13px',
              overflowX: 'auto',
              lineHeight: '1.6',
              fontFamily: 'var(--font-code)',
              whiteSpace: 'pre',
              tabSize: 2,
              margin: 0
            }}>
              {formatDisplayCode(optimizedCode.code)}
            </pre>
          </div>
        )}

        {/* Optimizations */}
        {r.optimizations && r.optimizations.length > 0 && !hasIssueGrokSolution && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              💡 Optimization Suggestions
            </h3>
            {r.optimizations.map((opt, i) => (
              <div key={i} style={{
                borderBottom: i < r.optimizations.length - 1 ? '1px solid var(--border)' : 'none',
                paddingBottom: '20px',
                marginBottom: '20px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: '600' }}>{opt.title}</h4>
                  {opt.ai_generated && (
                    <span style={{
                      background: 'var(--primary-light)',
                      color: 'var(--primary)',
                      padding: '3px 9px',
                      borderRadius: '999px',
                      fontSize: '11px',
                      fontWeight: '700'
                    }}>
                      {opt.ai_discovered ? 'Grok discovered' : 'Grok generated'}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                  <span style={{
                    background: '#fce8e6',
                    color: 'var(--danger)',
                    padding: '3px 10px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: '600'
                  }}>
                    Before: {opt.complexity_before}
                  </span>
                  <span style={{ color: 'var(--gray)', fontSize: '12px', alignSelf: 'center' }}>→</span>
                  <span style={{
                    background: '#e6f4ea',
                    color: 'var(--success)',
                    padding: '3px 10px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: '600'
                  }}>
                    After: {opt.complexity_after}
                  </span>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '10px' }}>
                  <strong>Problem:</strong> {opt.problem}
                </p>
                <p style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '10px' }}>
                  <strong>Solution:</strong> {opt.solution}
                </p>
                {opt.ai_note && (
                  <p style={{ fontSize: '12px', color: 'var(--gray)', marginBottom: '10px', lineHeight: '1.5' }}>
                    <strong>{opt.ai_generated ? 'Grok note' : 'AI review'}:</strong> {opt.ai_note}
                  </p>
                )}
                <pre style={{
                  background: '#1e1e2e',
                  color: '#cdd6f4',
                  padding: '14px',
                  borderRadius: '10px',
                  fontSize: '12px',
                  overflowX: 'auto',
                  lineHeight: '1.6',
                  fontFamily: 'var(--font-code)',
                  whiteSpace: 'pre',
                  tabSize: 2,
                  margin: 0
                }}>
                  {formatDisplayCode(opt.example)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Multi file result - FIXED with safe access
  const renderMultiResult = () => {
    const files = Array.isArray(result?.files) ? result.files : [];
    const projectSummary = result?.project_summary || {};
    const confidenceCounts = projectSummary.confidence_counts || {};
    const needsReviewCount = (confidenceCounts.low || 0) + (confidenceCounts.medium || 0);

    return (
      <div>
        {/* Summary cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {[
            { label: 'Total Files', value: result?.total_files || 0, icon: '📁' },
            { label: 'Total Lines', value: result?.total_lines || 0, icon: '📝' },
            { label: 'Total Issues', value: result?.total_issues || 0, icon: '⚠️' },
            { label: 'Avg Rating', value: `${(result?.average_rating || 0).toFixed(1)}/10`, icon: '⭐' },
            { label: 'Worst Time', value: projectSummary.worst_time_complexity || 'N/A', icon: 'O' },
            { label: 'Needs Review', value: needsReviewCount, icon: '!' },
          ].map(({ label, value, icon }) => (
            <div key={label} className="card" style={{ textAlign: 'center', padding: '20px' }}>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>{icon}</div>
              <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--primary)' }}>{value}</div>
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '4px' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* File selector */}
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
            📂 Files Analyzed ({files.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
            {files.map((file, i) => (
              <button
                key={i}
                onClick={() => setSelectedFile(i)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  border: '1.5px solid',
                  borderColor: selectedFile === i ? 'var(--primary)' : 'var(--border)',
                  background: selectedFile === i ? 'var(--primary-light)' : 'white',
                  color: selectedFile === i ? 'var(--primary)' : 'var(--gray)',
                  fontSize: '12px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-code)'
                }}
              >
                {getSafeFilename(file, `File ${i + 1}`).split('/').pop()}
              </button>
            ))}
          </div>

          {/* Selected file result */}
          {files[selectedFile] && renderSingleResult(files[selectedFile], files[selectedFile]?.filename)}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '48px 0', minHeight: '80vh' }}>
      <div className="container">
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '32px',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <h1 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '4px' }}>
              Analysis Results
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--gray)' }}>
              {type === 'code' && `File: ${result?.filename || 'Unknown'}`}
              {type === 'zip' && `ZIP file — ${result?.total_files || 0} files analyzed`}
              {type === 'github' && `GitHub: ${result?.github_url || 'Unknown'}`}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => navigate('/analyze')}
              className="btn btn-outline"
            >
              ← Analyze Another
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn btn-primary"
            >
              {downloading ? '⏳ Generating...' : '📄 Download PDF'}
            </button>
          </div>
        </div>

        {/* Results */}
        {type === 'code' && renderSingleResult(result, result?.filename)}
        {(type === 'zip' || type === 'github') && renderMultiResult()}
      </div>
    </div>
  );
}
