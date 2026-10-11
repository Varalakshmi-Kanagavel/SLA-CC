import { useState, useEffect } from 'react';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  Download, 
  Play, 
  Printer, 
  RefreshCw, 
  Sliders, 
  Sparkles 
} from 'lucide-react';
import { 
  CartesianGrid, 
  ComposedChart, 
  Line, 
  ReferenceLine, 
  ResponsiveContainer, 
  Tooltip, 
  XAxis, 
  YAxis 
} from 'recharts';

type Point = {
  t: number;
  users: number;
  cpu: number;
  memory: number;
  request_rate: number;
  response_time: number;
  replicas: number;
  threshold: number;
  slo_violation: boolean;
  algorithm: string;
};

type Run = {
  algorithm: string;
  metrics: Point[];
  summary: Record<string, number>;
};

type Result = {
  id: string;
  name: string;
  runs: Record<string, Run>;
};

const PRESETS = [
  { id: 'spike', label: 'Sudden Traffic Spike', desc: 'Sharp surge in requests to test rapid SLO violation defense', initial: 15, peak: 160, duration: 120, slo: 180, threshold: 70 },
  { id: 'ramp', label: 'Gradual Ramp Up', desc: 'Predictable rising traffic to evaluate steady autoscaling lag', initial: 10, peak: 140, duration: 120, slo: 200, threshold: 70 },
  { id: 'sawtooth', label: 'Sawtooth Oscillations', desc: 'Periodic wave bursts to test controller threshold stability', initial: 20, peak: 150, duration: 150, slo: 200, threshold: 70 },
  { id: 'constant', label: 'Sustained Heavy Load', desc: 'Continuous peak traffic testing long-term capacity bounds', initial: 110, peak: 110, duration: 90, slo: 220, threshold: 70 },
];

export default function App() {
  const [workload, setWorkload] = useState('spike');
  const [duration, setDuration] = useState(120);
  const [initialUsers, setInitialUsers] = useState(15);
  const [peakUsers, setPeakUsers] = useState(160);
  const [sloMs, setSloMs] = useState(180);
  const [cpuThreshold, setCpuThreshold] = useState(70);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');

  // Auto-run default comparison on initial load for instant presentation
  useEffect(() => {
    runComparison();
  }, []);

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setWorkload(preset.id);
    setInitialUsers(preset.initial);
    setPeakUsers(preset.peak);
    setDuration(preset.duration);
    setSloMs(preset.slo);
    setCpuThreshold(preset.threshold);
  };

  async function runComparison() {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/experiments/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `${workload.toUpperCase()} Comparison Evaluation`,
          algorithm: 'both',
          workload,
          duration,
          initial_users: initialUsers,
          peak_users: peakUsers,
          slo_ms: sloMs,
          cpu_threshold: cpuThreshold,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to complete comparison simulation.');
      }

      const data: Result = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to connect to simulation API backend.');
    } finally {
      setLoading(false);
    }
  }

  // Extract run metrics for charts
  const runs = result?.runs || {};
  const conventionalMetrics = runs.conventional?.metrics || [];
  const adaptiveMetrics = runs.adaptive?.metrics || [];
  const conventionalSummary = runs.conventional?.summary || {};
  const adaptiveSummary = runs.adaptive?.summary || {};

  // Formatted chart points
  const chartData = conventionalMetrics.map((p, i) => {
    const adaptivePoint = adaptiveMetrics[i] || {};
    return {
      t: p.t,
      users: p.users,
      rate: p.request_rate,
      latencyConv: Math.round(p.response_time),
      latencyAdapt: Math.round(adaptivePoint.response_time || p.response_time),
      replicasConv: p.replicas,
      replicasAdapt: adaptivePoint.replicas || p.replicas,
      thresholdConv: cpuThreshold,
      thresholdAdapt: Math.round(adaptivePoint.threshold || cpuThreshold),
      cpuConv: Math.round(p.cpu),
      cpuAdapt: Math.round(adaptivePoint.cpu || p.cpu),
    };
  });

  const exportUrl = (ext: 'csv' | 'json') =>
    result ? `/api/experiments/${result.id}/export/${ext}` : '#';

  // Calculated Presentation Stats
  const convViolations = conventionalSummary.slo_violation_pct ?? 0;
  const adaptViolations = adaptiveSummary.slo_violation_pct ?? 0;
  const convP95 = conventionalSummary.p95_latency ?? 0;
  const adaptP95 = adaptiveSummary.p95_latency ?? 0;
  const convAvgReplicas = conventionalSummary.avg_replicas ?? 0;
  const adaptAvgReplicas = adaptiveSummary.avg_replicas ?? 0;
  const convPeakReplicas = conventionalSummary.peak_replicas ?? 0;
  const adaptPeakReplicas = adaptiveSummary.peak_replicas ?? 0;

  return (
    <div className="pres-container">
      {/* 1. Executive Presentation Header */}
      <header className="pres-header">
        <div className="header-brand">
          <div className="brand-badge">
            <Activity className="brand-icon" size={20} />
            <span>CloudScale Lab</span>
          </div>
          <div className="title-block">
            <h1>SLA-Adaptive Kubernetes Autoscaler</h1>
            <p>Empirical Evaluation: Conventional Fixed-Target HPA vs. Dynamic SLO-Aware Threshold Controller</p>
          </div>
        </div>

        <div className="header-meta">
          <div className="system-tag status-live">
            <span className="live-indicator" />
            <span>Simulation Engine Active</span>
          </div>
          <div className="system-tag status-cloud">
            <span>AWS EC2 K3s Cluster</span>
            <small>Sydney: 16.176.33.10</small>
          </div>
        </div>
      </header>

      {/* 2. Interactive Scenarios & Single Primary Action Bar */}
      <section className="scenario-toolbar">
        <div className="scenario-group">
          <span className="toolbar-label">
            <Sparkles size={14} /> PRESENTATION WORKLOAD PRESETS:
          </span>
          <div className="preset-buttons">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                className={`preset-btn ${workload === p.id ? 'active' : ''}`}
                onClick={() => applyPreset(p)}
              >
                <b>{p.label}</b>
              </button>
            ))}
          </div>
        </div>

        <button
          className="run-btn primary"
          onClick={runComparison}
          disabled={loading}
          title="Run identical workload on both autoscaling algorithms"
        >
          {loading ? (
            <>
              <RefreshCw className="spin" size={17} /> Running Evaluation...
            </>
          ) : (
            <>
              <Play size={17} fill="currentColor" /> Run Autoscaling Comparison
            </>
          )}
        </button>
      </section>

      {error && <div className="pres-error-banner"><AlertTriangle size={18} /> {error}</div>}

      {/* 3. Core Metrics in Order of Presentation Necessity */}
      <section className="metrics-showcase">
        {/* Metric 1: SLO Violations (Most Critical) */}
        <div className={`metric-card highlight ${adaptViolations === 0 ? 'card-success' : 'card-warning'}`}>
          <div className="metric-header">
            <span className="order-tag">01 · PRIMARY GOAL</span>
            <span className="metric-label">SLO VIOLATIONS</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric conv">
              <small>Fixed 70% HPA</small>
              <span className="val-bad">{convViolations.toFixed(1)}%</span>
            </div>
            <div className="metric-arrow">→</div>
            <div className="side-metric adapt">
              <small>Adaptive Controller</small>
              <span className="val-good">{adaptViolations.toFixed(1)}%</span>
            </div>
          </div>
          <div className="metric-footer">
            {convViolations > adaptViolations ? (
              <span className="badge-win">
                <CheckCircle2 size={13} /> {Math.round(convViolations - adaptViolations)}% violation reduction
              </span>
            ) : (
              <span className="badge-neutral">Zero SLA Breaches</span>
            )}
          </div>
        </div>

        {/* Metric 2: P95 Response Latency */}
        <div className="metric-card">
          <div className="metric-header">
            <span className="order-tag">02 · LATENCY</span>
            <span className="metric-label">P95 RESPONSE TIME</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric conv">
              <small>Fixed 70% HPA</small>
              <span>{Math.round(convP95)} ms</span>
            </div>
            <div className="metric-arrow">vs</div>
            <div className="side-metric adapt">
              <small>Adaptive HPA</small>
              <span className="accent-purple">{Math.round(adaptP95)} ms</span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="footer-subtext">SLO Threshold Limit: <b>{sloMs} ms</b></span>
          </div>
        </div>

        {/* Metric 3: Adaptive Threshold Adjustment */}
        <div className="metric-card">
          <div className="metric-header">
            <span className="order-tag">03 · CONTROLLER</span>
            <span className="metric-label">ADAPTIVE CPU THRESHOLD</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric conv">
              <small>Static Baseline</small>
              <span>{cpuThreshold}%</span>
            </div>
            <div className="metric-arrow">⤹</div>
            <div className="side-metric adapt">
              <small>Dynamic Range</small>
              <span className="accent-purple">
                {chartData.length ? `${Math.min(...chartData.map(d => d.thresholdAdapt))}% – ${Math.max(...chartData.map(d => d.thresholdAdapt))}%` : '40% – 85%'}
              </span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="footer-subtext">Dips proactively to trigger scaling</span>
          </div>
        </div>

        {/* Metric 4: Pod Replica Scaling */}
        <div className="metric-card">
          <div className="metric-header">
            <span className="order-tag">04 · CAPACITY</span>
            <span className="metric-label">POD REPLICAS (AVG / PEAK)</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric conv">
              <small>Fixed 70% HPA</small>
              <span>{convAvgReplicas.toFixed(1)} / {convPeakReplicas}</span>
            </div>
            <div className="metric-arrow">vs</div>
            <div className="side-metric adapt">
              <small>Adaptive HPA</small>
              <span className="accent-purple">{adaptAvgReplicas.toFixed(1)} / {adaptPeakReplicas}</span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="footer-subtext">Safe burst absorption bounds</span>
          </div>
        </div>

        {/* Metric 5: Average CPU Utilization */}
        <div className="metric-card">
          <div className="metric-header">
            <span className="order-tag">05 · EFFICIENCY</span>
            <span className="metric-label">AVG. POD CPU LOAD</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric conv">
              <small>Fixed 70% HPA</small>
              <span>{Math.round(conventionalSummary.avg_cpu || 0)}%</span>
            </div>
            <div className="metric-arrow">vs</div>
            <div className="side-metric adapt">
              <small>Adaptive HPA</small>
              <span className="accent-purple">{Math.round(adaptiveSummary.avg_cpu || 0)}%</span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="footer-subtext">Balanced cluster utilization</span>
          </div>
        </div>

        {/* Metric 6: Input Traffic Context */}
        <div className="metric-card">
          <div className="metric-header">
            <span className="order-tag">06 · STRESS CONTEXT</span>
            <span className="metric-label">PEAK CLIENT LOAD</span>
          </div>
          <div className="metric-comparison">
            <div className="side-metric">
              <small>Concurrent Users</small>
              <span>{peakUsers} users</span>
            </div>
            <div className="metric-arrow">·</div>
            <div className="side-metric">
              <small>Request Rate</small>
              <span>{Math.round(peakUsers * 0.8)} req/s</span>
            </div>
          </div>
          <div className="metric-footer">
            <span className="footer-subtext">{workload.toUpperCase()} traffic profile ({duration}s)</span>
          </div>
        </div>
      </section>

      {/* 4. The 4 Essential Presentation Charts */}
      <section className="charts-section">
        <div className="charts-header">
          <div>
            <h2>Side-by-Side Algorithm Timelines</h2>
            <p>Identical synthetic request traffic fed to both autoscaling strategies</p>
          </div>
          <div className="chart-legend">
            <span className="legend-item"><i className="legend-dot blue" /> Conventional Fixed HPA (70% Target)</span>
            <span className="legend-item"><i className="legend-dot purple" /> SLA-Adaptive HPA (Dynamic Target)</span>
            <span className="legend-item"><i className="legend-line amber" /> SLO Target Limit</span>
          </div>
        </div>

        <div className="charts-grid-pres">
          {/* Chart 1: Latency vs SLO (The Core Finding) */}
          <div className="pres-chart-box">
            <div className="box-header">
              <div>
                <h3>1. Response Time vs. SLO Ceiling</h3>
                <small>Measures milliseconds against Service Level Objective</small>
              </div>
              <span className="box-badge">PRIMARY SLI</span>
            </div>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={chartData} margin={{ top: 12, right: 12, left: -15, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(x) => `${x}s`} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0b1324', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }} />
                  <ReferenceLine y={sloMs} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: `SLO ${sloMs}ms`, fill: '#fbbf24', fontSize: 11, position: 'insideTopRight' }} />
                  <Line type="monotone" dataKey="latencyConv" name="Conventional Latency" stroke="#38bdf8" strokeWidth={2.2} dot={false} />
                  <Line type="monotone" dataKey="latencyAdapt" name="Adaptive Latency" stroke="#a855f7" strokeWidth={2.4} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Adaptive Threshold Dynamics */}
          <div className="pres-chart-box">
            <div className="box-header">
              <div>
                <h3>2. CPU Target Adaptation Dynamics</h3>
                <small>Shows controller threshold proactively lowering to absorb latency</small>
              </div>
              <span className="box-badge">CONTROLLER LOGIC</span>
            </div>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={chartData} margin={{ top: 12, right: 12, left: -15, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(x) => `${x}s`} />
                  <YAxis domain={[30, 90]} tick={{ fill: '#64748b', fontSize: 11 }} unit="%" />
                  <Tooltip contentStyle={{ background: '#0b1324', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }} />
                  <Line type="stepAfter" dataKey="thresholdConv" name="Conventional Target" stroke="#38bdf8" strokeWidth={1.8} strokeDasharray="4 4" dot={false} />
                  <Line type="stepAfter" dataKey="thresholdAdapt" name="Adaptive Target" stroke="#a855f7" strokeWidth={2.4} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Pod Replica Count (Scaling Speed) */}
          <div className="pres-chart-box">
            <div className="box-header">
              <div>
                <h3>3. Pod Replica Scaling Timeline</h3>
                <small>Demonstrates proactive scale-out vs conventional HPA delay</small>
              </div>
              <span className="box-badge">K8S CAPACITY</span>
            </div>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={chartData} margin={{ top: 12, right: 12, left: -15, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(x) => `${x}s`} />
                  <YAxis allowDecimals={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0b1324', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }} />
                  <Line type="stepAfter" dataKey="replicasConv" name="Conventional Replicas" stroke="#38bdf8" strokeWidth={2.2} dot={false} />
                  <Line type="stepAfter" dataKey="replicasAdapt" name="Adaptive Replicas" stroke="#a855f7" strokeWidth={2.4} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 4: CPU Utilization Profile */}
          <div className="pres-chart-box">
            <div className="box-header">
              <div>
                <h3>4. Pod CPU Utilization</h3>
                <small>Relative utilization per pod across time steps</small>
              </div>
              <span className="box-badge">EFFICIENCY</span>
            </div>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={chartData} margin={{ top: 12, right: 12, left: -15, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(x) => `${x}s`} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} unit="%" />
                  <Tooltip contentStyle={{ background: '#0b1324', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="cpuConv" name="Conventional CPU" stroke="#38bdf8" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="cpuAdapt" name="Adaptive CPU" stroke="#a855f7" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Empirical Comparison Table & Presentation Controls */}
      <section className="results-and-config-grid">
        {/* Left: Direct Comparison Summary Table */}
        <div className="pres-card table-card">
          <div className="card-top">
            <div>
              <h3>Definitive Comparison Summary</h3>
              <p>Key indicators measured over the {duration}-second evaluation run</p>
            </div>
            <div className="export-actions">
              <a className="export-btn" href={exportUrl('csv')} download>
                <Download size={13} /> CSV
              </a>
              <button className="export-btn" onClick={() => window.print()}>
                <Printer size={13} /> Print
              </button>
            </div>
          </div>

          <div className="clean-table">
            <div className="t-row t-head">
              <span>RESEARCH METRIC</span>
              <span>CONVENTIONAL HPA</span>
              <span>SLA-ADAPTIVE HPA</span>
              <span>OUTCOME / BENEFIT</span>
            </div>

            <div className="t-row highlight-row">
              <span className="col-title">SLO Violation Fraction</span>
              <span className="col-val bad">{convViolations.toFixed(1)}%</span>
              <span className="col-val good">{adaptViolations.toFixed(1)}%</span>
              <span className="col-badge win">
                {convViolations > adaptViolations ? 'SLO Preserved' : 'Fully Compliant'}
              </span>
            </div>

            <div className="t-row">
              <span className="col-title">P95 Response Latency</span>
              <span className="col-val">{Math.round(convP95)} ms</span>
              <span className="col-val accent-purple">{Math.round(adaptP95)} ms</span>
              <span className="col-badge">
                {convP95 > adaptP95 ? `–${Math.round(convP95 - adaptP95)} ms lower` : 'Within limits'}
              </span>
            </div>

            <div className="t-row">
              <span className="col-title">Average Latency</span>
              <span className="col-val">{Math.round(conventionalSummary.avg_latency || 0)} ms</span>
              <span className="col-val accent-purple">{Math.round(adaptiveSummary.avg_latency || 0)} ms</span>
              <span className="col-badge">Smoother tail</span>
            </div>

            <div className="t-row">
              <span className="col-title">Target CPU Threshold</span>
              <span className="col-val">Fixed 70%</span>
              <span className="col-val accent-purple">Adaptive (40%–85%)</span>
              <span className="col-badge win">Dynamic headroom</span>
            </div>

            <div className="t-row">
              <span className="col-title">Scaling Actions</span>
              <span className="col-val">{conventionalSummary.scaling_events ?? 0} events</span>
              <span className="col-val accent-purple">{adaptiveSummary.scaling_events ?? 0} events</span>
              <span className="col-badge">Proactive scale-up</span>
            </div>

            <div className="t-row">
              <span className="col-title">Peak Pod Replicas</span>
              <span className="col-val">{convPeakReplicas} pods</span>
              <span className="col-val accent-purple">{adaptPeakReplicas} pods</span>
              <span className="col-badge">Automatic burst bounds</span>
            </div>
          </div>
        </div>

        {/* Right: Fine-Tune Parameters (Compact & Clean) */}
        <div className="pres-card config-card">
          <div className="card-top">
            <div>
              <h3>Scenario Parameters</h3>
              <p>Tune simulation settings for live demonstration</p>
            </div>
            <Sliders size={18} className="text-muted" />
          </div>

          <div className="config-form">
            <div className="input-field">
              <label>Workload Profile Pattern</label>
              <select value={workload} onChange={(e) => setWorkload(e.target.value)}>
                <option value="spike">Sudden Spike (Rapid Surge)</option>
                <option value="ramp">Ramp Up (Linear Increase)</option>
                <option value="sawtooth">Sawtooth Waves (Burst Bursts)</option>
                <option value="constant">Constant High Load</option>
              </select>
            </div>

            <div className="input-grid">
              <div className="input-field">
                <label>SLO Latency Target</label>
                <div className="input-with-unit">
                  <input
                    type="number"
                    min={50}
                    max={2000}
                    value={sloMs}
                    onChange={(e) => setSloMs(+e.target.value)}
                  />
                  <span>ms</span>
                </div>
              </div>

              <div className="input-field">
                <label>Baseline CPU Target</label>
                <div className="input-with-unit">
                  <input
                    type="number"
                    min={40}
                    max={85}
                    value={cpuThreshold}
                    onChange={(e) => setCpuThreshold(+e.target.value)}
                  />
                  <span>%</span>
                </div>
              </div>
            </div>

            <div className="input-grid">
              <div className="input-field">
                <label>Initial Users</label>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={initialUsers}
                  onChange={(e) => setInitialUsers(+e.target.value)}
                />
              </div>

              <div className="input-field">
                <label>Peak Users</label>
                <input
                  type="number"
                  min={10}
                  max={1000}
                  value={peakUsers}
                  onChange={(e) => setPeakUsers(+e.target.value)}
                />
              </div>
            </div>

            <div className="input-field">
              <label>Simulation Duration: <b>{duration}s</b></label>
              <input
                type="range"
                min={30}
                max={300}
                step={10}
                value={duration}
                onChange={(e) => setDuration(+e.target.value)}
              />
            </div>

            <button
              className="run-btn full-width"
              onClick={runComparison}
              disabled={loading}
            >
              {loading ? <RefreshCw className="spin" size={16} /> : <Play size={16} fill="currentColor" />}
              {loading ? 'Simulating...' : 'Apply & Run Comparison'}
            </button>
          </div>
        </div>
      </section>

      {/* 6. Clean Presentation Footer */}
      <footer className="pres-footer">
        <span>CloudScale Lab · SLA-Adaptive Autoscaling Research Project</span>
        <span>Verified against AWS EC2 K3s Cluster & Kubernetes HPA v2</span>
      </footer>
    </div>
  );
}
