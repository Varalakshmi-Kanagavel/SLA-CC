import { useEffect, useState } from 'react';
import { Activity, ArrowUpRight, BarChart3, Bell, BookOpen, Boxes, ChevronDown, CircleHelp, Cloud, Cpu, Database, Download, FileText, Gauge, GitCompareArrows, LayoutDashboard, Menu, Play, Radio, RotateCcw, Search, Settings2, ShieldCheck, Trash2, Users, Zap } from 'lucide-react';
import { CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

// ── Types ────────────────────────────────────────────────────────────────────
type Point = { t: number; users: number; cpu: number; memory: number; request_rate: number; response_time: number; replicas: number; threshold: number; slo_violation: boolean; algorithm: string; game_replicas?: number };
type Run = { algorithm: string; metrics: Point[]; summary: Record<string, number> };
type Result = { id: string; name: string; config: Record<string, any>; runs: Record<string, Run> };
type ExpMeta = { id: string; name: string; created_at: string };
type Settings = { warningMultiplier: number; criticalMultiplier: number; decreaseStep: number; increaseStep: number };

// ── Constants ─────────────────────────────────────────────────────────────────
const WORKLOAD_LABELS: Record<string, string> = { constant: 'Constant', ramp: 'Ramp up', spike: 'Sudden spike', sawtooth: 'Sawtooth', custom: 'Custom ramp & cooldown', minecraft: 'Minecraft evening burst 🎮' };
const SWEEP_SLOS = [100, 200, 500];
const SWEEP_WORKLOADS = ['constant', 'ramp', 'spike', 'sawtooth'];
const fmt = (n: number) => new Intl.NumberFormat('en-US').format(Math.round(n));
const DEFAULT_SETTINGS: Settings = { warningMultiplier: 1.2, criticalMultiplier: 1.5, decreaseStep: 5, increaseStep: 1 };

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState('Overview');
  // Experiment form
  const [algorithm, setAlgorithm] = useState('both');
  const [workload, setWorkload] = useState('spike');
  const [duration, setDuration] = useState(120);
  const [initial, setInitial] = useState(10);
  const [peak, setPeak] = useState(300);
  const [slo, setSlo] = useState(200);
  const [threshold, setThreshold] = useState(70);
  const [minReplicas, setMinReplicas] = useState(1);
  const [maxReplicas, setMaxReplicas] = useState(10);
  // Run state
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Experiments list
  const [experiments, setExperiments] = useState<ExpMeta[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedExp, setSelectedExp] = useState<Result | null>(null);
  // Compare state
  const [compareIdA, setCompareIdA] = useState('');
  const [compareIdB, setCompareIdB] = useState('');
  const [compareA, setCompareA] = useState<Result | null>(null);
  const [compareB, setCompareB] = useState<Result | null>(null);
  // Sweep state
  const [sweepTab, setSweepTab] = useState<'single' | 'sweep'>('single');
  const [sweepWorkloads, setSweepWorkloads] = useState<string[]>(['spike', 'ramp']);
  const [sweepSlos, setSweepSlos] = useState<number[]>([200]);
  const [sweepLoading, setSweepLoading] = useState(false);
  const [sweepResult, setSweepResult] = useState<any | null>(null);
  // Settings
  const [settings, setSettings] = useState<Settings>(() => { try { const s = localStorage.getItem('cloudscale-settings'); return s ? JSON.parse(s) : DEFAULT_SETTINGS; } catch { return DEFAULT_SETTINGS; } });

  const runs = result?.runs ?? {};
  const conventional = runs.conventional?.metrics ?? [];
  const adaptive = runs.adaptive?.metrics ?? [];
  const isMinecraft = workload === 'minecraft';
  const chartData = conventional.map((p, i) => ({ t: p.t, users: p.users, rate: p.request_rate, cpuHpa: p.cpu, cpuAdaptive: adaptive[i]?.cpu, latencyHpa: p.response_time, latencyAdaptive: adaptive[i]?.response_time, replicasHpa: p.replicas, replicasAdaptive: adaptive[i]?.replicas, threshold: adaptive[i]?.threshold }));
  const stats = Object.values(runs).map(r => r.summary);
  const latest = adaptive[adaptive.length - 1] ?? conventional[conventional.length - 1];
  const summaryAvg = (key: string) => stats.length ? stats.reduce((n, s) => n + (s[key] ?? 0), 0) / stats.length : 0;
  const exportUrl = (type: string) => result ? `/api/experiments/${result.id}/export/${type}` : '#';

  useEffect(() => { loadExperiments(); }, []);

  const loadExperiments = async () => { try { setExperiments(await fetch('/api/experiments').then(r => r.json())); } catch {} };

  async function runExperiment() {
    setLoading(true); setError('');
    try {
      const path = algorithm === 'both' ? '/api/experiments/compare' : '/api/experiments';
      const body = { name: `${WORKLOAD_LABELS[workload].replace(' 🎮', '')} — ${algorithm}`, algorithm, workload, duration, initial_users: initial, peak_users: peak, slo_ms: slo, cpu_threshold: threshold, min_replicas: minReplicas, max_replicas: maxReplicas, warning_multiplier: settings.warningMultiplier, critical_multiplier: settings.criticalMultiplier, decrease_step: settings.decreaseStep, increase_step: settings.increaseStep };
      const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error((await res.json()).detail ?? 'Simulation failed');
      setResult(await res.json()); await loadExperiments();
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to reach the simulation API. Start the backend or use Docker Compose.'); } finally { setLoading(false); }
  }

  async function runSweep() {
    if (!sweepWorkloads.length || !sweepSlos.length) return;
    setSweepLoading(true); setSweepResult(null);
    try {
      const scenarios = sweepWorkloads.flatMap(w => sweepSlos.map(s => ({ name: `${WORKLOAD_LABELS[w]} · ${s}ms`, workload: w, slo_ms: s, algorithm: 'both', duration, initial_users: initial, peak_users: peak, cpu_threshold: threshold })));
      const res = await fetch('/api/experiments/batch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'Scenario sweep', scenarios }) });
      if (!res.ok) throw new Error('Sweep failed');
      setSweepResult(await res.json()); await loadExperiments();
    } catch (e) { setError(e instanceof Error ? e.message : 'Sweep failed'); } finally { setSweepLoading(false); }
  }

  useEffect(() => { if (!compareIdA) { setCompareA(null); return; } fetch(`/api/experiments/${compareIdA}`).then(r => r.json()).then(setCompareA); }, [compareIdA]);
  useEffect(() => { if (!compareIdB) { setCompareB(null); return; } fetch(`/api/experiments/${compareIdB}`).then(r => r.json()).then(setCompareB); }, [compareIdB]);

  async function deleteExperiment(id: string) { await fetch(`/api/experiments/${id}`, { method: 'DELETE' }); setExperiments(prev => prev.filter(e => e.id !== id)); if (selectedExp?.id === id) setSelectedExp(null); }

  const saveSettings = (next: Settings) => { setSettings(next); localStorage.setItem('cloudscale-settings', JSON.stringify(next)); };

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" onClick={() => setPage('Overview')}><span className="brand-mark"><Activity size={19} /></span><span><b>CloudScale</b><small>RESEARCH LAB</small></span></a>
        <div className="workspace"><span className="cloud-icon"><Cloud size={17} /></span><span><b>Research workspace</b><small>Simulation environment</small></span><ChevronDown size={14} /></div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {([['Overview', LayoutDashboard], ['Experiments', BarChart3], ['Simulator', Activity], ['Compare runs', GitCompareArrows], ['Methodology', BookOpen], ['Settings', Settings2], ['Report', FileText]] as const).map(([name, Icon]) => (
            <button className={`nav-link ${page === name ? 'active' : ''}`} onClick={() => setPage(name)} key={name}>
              <Icon size={17} />{name}{name === 'Experiments' && experiments.length > 0 && <span className="nav-count">{experiments.length}</span>}
            </button>
          ))}
        </nav>
        <div className="side-bottom">
          <div className="infra"><span className="pulse" /><span><b>Demo mode active</b><small>Cluster not connected</small></span></div>
          <div className="user"><div className="avatar">VK</div><span><b>Research Lab</b><small>Team 10 workspace</small></span><ChevronDown size={14} /></div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button className="mobile-menu" id="mobile-menu-btn"><Menu size={20} /></button>
          <div className="crumb">Workspace <span>/</span> <b>{page}</b></div>
          <div className="header-actions"><span className="mode-pill"><span className="pulse" />SIMULATION</span><button className="icon-btn" title="Notifications"><Bell size={17} /></button><button className="help-btn"><CircleHelp size={16} /> Help</button></div>
        </header>
        <div className="content">
          {page === 'Overview' && <>
            <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> CLOUD INFRASTRUCTURE RESEARCH</div><h1>Autoscaling, under the microscope.</h1><p>Study how SLO-aware threshold adaptation changes Kubernetes scaling behavior.</p></div><button className="primary" id="overview-run-btn" onClick={() => { setPage('Simulator'); }}><Play size={16} fill="currentColor" /> Run experiment <ArrowUpRight size={16} /></button></div>
            <div className="alert"><span className="alert-icon"><ShieldCheck size={17} /></span><span><b>Synthetic workload simulation for research experimentation.</b><small>Paper-inspired methodology. Results are simulated and do not represent a production Kubernetes cluster.</small></span><span className="alert-tag">DEMO ENVIRONMENT</span></div>
            <div className="section-head"><div><h2>Live system overview</h2><p>Current run metrics and experiment health</p></div><button className="subtle" onClick={() => { setResult(null); setError(''); }}><RotateCcw size={14} /> Reset view</button></div>
            <div className="kpis">
              <Kpi icon={<Radio />} label="SYSTEM STATUS" value={loading ? 'Running' : result ? 'Complete' : 'Idle'} meta={result ? result.name : 'Waiting for experiment'} status />
              <Kpi icon={<Users />} label="ACTIVE USERS" value={latest ? fmt(latest.users) : '—'} meta={(WORKLOAD_LABELS[workload] ?? workload).replace(' 🎮', '') + ' workload'} />
              <Kpi icon={<Cpu />} label="CPU UTILIZATION" value={latest ? `${latest.cpu.toFixed(1)}%` : '—'} meta="Across simulated pods" />
              <Kpi icon={<Zap />} label="RESPONSE TIME" value={latest ? `${Math.round(latest.response_time)} ms` : '—'} meta={`SLO target: ${slo} ms`} danger={!!latest && latest.response_time > slo} />
              <Kpi icon={<Boxes />} label="AVG. REPLICAS" value={stats.length ? summaryAvg('avg_replicas').toFixed(1) : '—'} meta={latest && Object.values(runs).length ? `Peak ${Math.max(...Object.values(runs).map((r: any) => r.summary.peak_replicas))} replicas` : 'Min 1 · Max 10'} />
              <Kpi icon={<Gauge />} label="ADAPTIVE THRESHOLD" value={adaptive.length ? `${latest?.threshold}%` : `${threshold}%`} meta="Allowed range: 40–85%" />
            </div>
            <div className="section-head charts-title"><div><h2>Algorithm performance</h2><p>{result ? 'Same synthetic workload · Conventional HPA vs SLO-adaptive' : 'Run a simulation to see the two scaling strategies side by side'}</p></div><div className="legend"><span><i className="dot blue" /> Conventional HPA</span><span><i className="dot violet" /> Adaptive HPA</span></div></div>
            <div className="charts-grid">
              <Chart title="CPU utilization" unit="%" data={chartData} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} />
              <Chart title="Application response time" unit="ms" data={chartData} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={slo} />
              <Chart title="Replica count" unit="pods" data={chartData} keyA="replicasHpa" keyB="replicasAdaptive" colorA="#52a7ff" colorB="#a78bfa" />
              <Chart title="Adaptive CPU threshold" unit="%" data={chartData} keyA="threshold" colorA="#a78bfa" ymax={100} />
            </div>
            <div className="bottom-grid">
              <div className="panel recent">
                <div className="panel-head"><div><span className="eyebrow">RESEARCH HISTORY</span><h2>Recent experiments</h2></div><button className="text-btn" onClick={() => setPage('Experiments')}>View all <ArrowUpRight size={14} /></button></div>
                {experiments.length ? <div className="history-list">{experiments.slice(0, 4).map(e => <button className="history-row" key={e.id} onClick={() => fetch(`/api/experiments/${e.id}`).then(r => r.json()).then(setResult)}><span className="history-icon"><BarChart3 size={15} /></span><span><b>{e.name}</b><small>{new Date(e.created_at + 'Z').toLocaleString()}</small></span><ArrowUpRight size={15} /></button>)}</div> : <div className="empty-mini"><Database size={18} />Experiments you run will be saved here.</div>}
              </div>
              <div className="panel methodology"><span className="eyebrow">RESEARCH METHODOLOGY</span><h2>What are we testing?</h2><p>Fixed CPU targets can react slowly when application latency rises. The adaptive controller lowers its threshold when response time breaches warning or critical SLO bands, and cautiously raises it when performance has headroom.</p><button className="text-btn" onClick={() => setPage('Methodology')}>Explore methodology <ArrowUpRight size={14} /></button></div>
            </div>
            <footer><span>CloudScale Lab <i>·</i> Academic research prototype</span><span><span className="pulse" /> All systems operational <i>·</i> Demo environment</span></footer>
          </>}

          {page === 'Simulator' && <>
            <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> EXPERIMENT RUNNER</div><h1>Simulator</h1><p>Configure and run autoscaling experiments with synthetic workloads.</p></div></div>
            {isMinecraft && <div className="alert"><span className="alert-icon">🎮</span><span><b>Minecraft stateful workload mode</b><small>1 fixed game pod (stateful, not HPA-scaled) · N proxy pods scaled by HPA · Player connection curve: evening burst pattern</small></span><span className="alert-tag">STATEFUL</span></div>}
            <div className="sim-tabs"><button id="tab-single" className={`sim-tab${sweepTab === 'single' ? ' active' : ''}`} onClick={() => setSweepTab('single')}><Play size={13} /> Single run</button><button id="tab-sweep" className={`sim-tab${sweepTab === 'sweep' ? ' active' : ''}`} onClick={() => setSweepTab('sweep')}><BarChart3 size={13} /> Scenario sweep</button></div>
            {sweepTab === 'single' && <section className="experiment-layout" id="experiment-controls">
              <div className="panel controls">
                <div className="panel-head"><div><span className="eyebrow">EXPERIMENT DESIGN</span><h2>Configure a run</h2></div><span className="step">01 / SETUP</span></div>
                <label>Compare algorithms<select id="select-algorithm" value={algorithm} onChange={e => setAlgorithm(e.target.value)}><option value="both">Conventional HPA vs Adaptive HPA</option><option value="conventional">Conventional HPA only</option><option value="adaptive">Adaptive HPA only</option></select><small>Both algorithms receive an identical deterministic workload.</small></label>
                <label>Workload pattern<select id="select-workload" value={workload} onChange={e => setWorkload(e.target.value)}>{Object.entries(WORKLOAD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
                <div className="field-row"><NumberField label="Duration (seconds)" id="input-duration" value={duration} set={setDuration} min={20} max={900} /><NumberField label="SLO target (ms)" id="input-slo" value={slo} set={setSlo} min={50} max={5000} /></div>
                <div className="field-row"><NumberField label="Initial users" id="input-initial" value={initial} set={setInitial} min={1} max={10000} /><NumberField label="Peak users" id="input-peak" value={peak} set={setPeak} min={1} max={10000} /></div>
                <div className="field-row"><NumberField label="Min replicas" id="input-min-rep" value={minReplicas} set={setMinReplicas} min={1} max={100} /><NumberField label="Max replicas" id="input-max-rep" value={maxReplicas} set={setMaxReplicas} min={1} max={100} /></div>
                <label>Initial CPU threshold <span className="value-inline">{threshold}%</span><input type="range" id="range-threshold" min="40" max="85" value={threshold} onChange={e => setThreshold(+e.target.value)} /><small>Adaptive mode changes this threshold as latency moves around the SLO.</small></label>
                <div className="form-actions"><button id="btn-run" className="primary run" onClick={runExperiment} disabled={loading}>{loading ? <span className="spinner" /> : <Play size={15} fill="currentColor" />}{loading ? 'Running simulation…' : algorithm === 'both' ? 'Compare algorithms' : 'Start simulation'}</button><button className="icon-btn reset" title="Reset form" onClick={() => { setInitial(10); setPeak(300); setDuration(120); setSlo(200); setThreshold(70); setResult(null); setError(''); }}><RotateCcw size={16} /></button></div>
                {error && <div className="error" id="run-error">{error}</div>}
              </div>
              <div className="panel results">
                <div className="panel-head"><div><span className="eyebrow">EXPERIMENT RESULTS</span><h2>{result?.name ?? 'Your results will appear here'}</h2></div>{result && <div className="exports"><a href={exportUrl('csv')} id="export-csv"><Download size={13} /> CSV</a><a href={exportUrl('json')} id="export-json"><Download size={13} /> JSON</a><button id="btn-report" onClick={() => setPage('Report')}><FileText size={13} /> Report</button></div>}</div>
                {result ? <>
                  <div className="result-table">
                    <div className="table-row th"><span>PERFORMANCE METRIC</span><span>CONVENTIONAL</span><span>ADAPTIVE</span></div>
                    {[['Average response', 'avg_latency', ' ms'], ['95th percentile latency', 'p95_latency', ' ms'], ['SLO violations', 'slo_violation_pct', '%'], ['Average CPU', 'avg_cpu', '%'], ['Average replicas', 'avg_replicas', ''], ['Scaling events', 'scaling_events', '']].map(([label, key, unit]) => <div className="table-row" key={key as string}><span>{label}</span><b>{runs.conventional ? `${runs.conventional.summary[key as string]}${unit}` : '—'}</b><b className="violet-text">{runs.adaptive ? `${runs.adaptive.summary[key as string]}${unit}` : '—'}</b></div>)}
                  </div>
                  <div className="result-note"><ShieldCheck size={16} /> Compare results across identical synthetic inputs. Simulation output, not a measured cluster result.</div>
                  <div className="charts-grid" style={{ marginTop: 16 }}>
                    <Chart title={isMinecraft ? 'Proxy CPU utilization' : 'CPU utilization'} unit="%" data={chartData} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} />
                    <Chart title={isMinecraft ? 'Tick latency' : 'Application response time'} unit="ms" data={chartData} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={slo} />
                    <Chart title={isMinecraft ? 'Proxy replica count' : 'Replica count'} unit="pods" data={chartData} keyA="replicasHpa" keyB="replicasAdaptive" colorA="#52a7ff" colorB="#a78bfa" />
                    <Chart title="Adaptive CPU threshold" unit="%" data={chartData} keyA="threshold" colorA="#a78bfa" ymax={100} />
                  </div>
                </> : <div className="empty-results"><div className="empty-icon"><BarChart3 size={24} /></div><b>Ready when you are</b><span>Choose a workload and run your first experiment.<br />Simulation results will be saved for later review.</span><button className="subtle" onClick={runExperiment} disabled={loading}><Play size={13} /> Run a sample comparison</button></div>}
              </div>
            </section>}
            {sweepTab === 'sweep' && <div className="sweep-layout">
              <div className="panel controls">
                <div className="panel-head"><div><span className="eyebrow">SCENARIO SWEEP</span><h2>Multi-scenario batch</h2></div><span className="step">02 / SWEEP</span></div>
                <p className="sweep-desc">Select workload patterns and SLO targets. Each combination runs both algorithms and results are compared in a summary grid.</p>
                <div className="sweep-group"><div className="sweep-group-label">WORKLOAD PATTERNS</div>{SWEEP_WORKLOADS.map(w => <label key={w} className="sweep-check"><input type="checkbox" checked={sweepWorkloads.includes(w)} onChange={() => setSweepWorkloads(prev => prev.includes(w) ? prev.filter(x => x !== w) : [...prev, w])} />{WORKLOAD_LABELS[w]}</label>)}</div>
                <div className="sweep-group"><div className="sweep-group-label">SLO TARGETS (ms)</div>{SWEEP_SLOS.map(s => <label key={s} className="sweep-check"><input type="checkbox" checked={sweepSlos.includes(s)} onChange={() => setSweepSlos(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])} />{s} ms</label>)}</div>
                <div className="sweep-group"><div className="sweep-group-label">SHARED PARAMETERS</div><div className="field-row"><NumberField label="Duration (s)" id="sweep-duration" value={duration} set={setDuration} min={20} max={900} /><NumberField label="Peak users" id="sweep-peak" value={peak} set={setPeak} min={1} max={10000} /></div></div>
                <div className="form-actions"><button id="btn-run-sweep" className="primary run" onClick={runSweep} disabled={sweepLoading || !sweepWorkloads.length || !sweepSlos.length}>{sweepLoading ? <span className="spinner" /> : <Play size={15} fill="currentColor" />}{sweepLoading ? 'Running sweep…' : `Run ${sweepWorkloads.length * sweepSlos.length} scenario${sweepWorkloads.length * sweepSlos.length !== 1 ? 's' : ''}`}</button></div>
              </div>
              {sweepResult && <div className="panel sweep-results">
                <div className="panel-head"><div><span className="eyebrow">SWEEP RESULTS</span><h2>SLO violations — Conventional → Adaptive</h2></div></div>
                <div className="sweep-table">
                  <div className="sweep-table-row sweep-header"><div className="sweep-cell">Workload</div>{sweepSlos.map(s => <div className="sweep-cell" key={s}>{s} ms SLO</div>)}</div>
                  {sweepWorkloads.map(w => {
                    return <div className="sweep-table-row" key={w}><div className="sweep-cell sweep-label">{WORKLOAD_LABELS[w]}</div>{sweepSlos.map(s => { const r = (sweepResult.results ?? []).find((x: any) => x.config?.workload === w && x.config?.slo_ms === s); if (!r) return <div className="sweep-cell" key={s}>—</div>; const conv = r.runs?.conventional?.summary?.slo_violation_pct ?? 0; const adap = r.runs?.adaptive?.summary?.slo_violation_pct ?? 0; const better = adap < conv; return <div className={`sweep-cell sweep-data${better ? ' sweep-win' : ''}`} key={s}><span>{conv.toFixed(1)}%</span><span className="sweep-arrow">→</span><span className={better ? 'sweep-adap-win' : ''}>{adap.toFixed(1)}%</span></div>; })}</div>;
                  })}
                </div>
                <p className="result-note" style={{ marginTop: 10 }}><ShieldCheck size={14} /> Conv → Adaptive · SLO violation % · Lower is better · Purple = Adaptive wins</p>
              </div>}
            </div>}
          </>}

          {page === 'Experiments' && <>
            <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> EXPERIMENT HISTORY</div><h1>Experiments</h1><p>Browse, review, and delete your saved simulation runs.</p></div></div>
            <div className="search-bar"><Search size={14} /><input id="exp-search" placeholder="Search experiments…" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} /></div>
            <div className="exp-table panel">
              <div className="exp-row exp-header"><span>NAME</span><span>DATE</span><span></span></div>
              {experiments.filter(e => e.name.toLowerCase().includes(searchTerm.toLowerCase())).length === 0 && <div className="empty-mini" style={{ padding: '20px 16px' }}><Database size={18} />{experiments.length === 0 ? 'No experiments yet. Run one in the Simulator.' : 'No results found.'}</div>}
              {experiments.filter(e => e.name.toLowerCase().includes(searchTerm.toLowerCase())).map(e => <div className={`exp-row${selectedExp?.id === e.id ? ' exp-selected' : ''}`} key={e.id} onClick={() => fetch(`/api/experiments/${e.id}`).then(r => r.json()).then(setSelectedExp)} style={{ cursor: 'pointer' }}>
                <span className="exp-name"><span className="history-icon" style={{ display: 'inline-flex' }}><BarChart3 size={13} /></span>{e.name}</span>
                <span style={{ fontSize: 9, color: '#7d8ba0' }}>{new Date(e.created_at + 'Z').toLocaleString()}</span>
                <button className="exp-del" id={`del-${e.id}`} onClick={ev => { ev.stopPropagation(); deleteExperiment(e.id); }}><Trash2 size={13} /></button>
              </div>)}
            </div>
            {selectedExp && (() => { const r = selectedExp.runs ?? {}; const c = r.conventional?.metrics ?? []; const a = r.adaptive?.metrics ?? []; const d = c.map((p, i) => ({ t: p.t, cpuHpa: p.cpu, cpuAdaptive: a[i]?.cpu, latencyHpa: p.response_time, latencyAdaptive: a[i]?.response_time, replicasHpa: p.replicas, replicasAdaptive: a[i]?.replicas, threshold: a[i]?.threshold })); return <>
              <div className="section-head" style={{ marginTop: 18 }}><div><h2>{selectedExp.name}</h2><p>Detailed results for selected experiment</p></div><button className="subtle" onClick={() => setSelectedExp(null)}><RotateCcw size={13} /> Clear</button></div>
              <div className="result-table"><div className="table-row th"><span>PERFORMANCE METRIC</span><span>CONVENTIONAL</span><span>ADAPTIVE</span></div>{[['Avg response', 'avg_latency', ' ms'], ['P95 latency', 'p95_latency', ' ms'], ['SLO violations', 'slo_violation_pct', '%'], ['Avg CPU', 'avg_cpu', '%'], ['Avg replicas', 'avg_replicas', ''], ['Scaling events', 'scaling_events', '']].map(([l, k, u]) => <div className="table-row" key={k as string}><span>{l}</span><b>{r.conventional ? `${r.conventional.summary[k as string]}${u}` : '—'}</b><b className="violet-text">{r.adaptive ? `${r.adaptive.summary[k as string]}${u}` : '—'}</b></div>)}</div>
              {d.length > 0 && <div className="charts-grid" style={{ marginTop: 16 }}><Chart title="CPU utilization" unit="%" data={d} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} /><Chart title="Response time" unit="ms" data={d} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={selectedExp.config?.slo_ms} /><Chart title="Replica count" unit="pods" data={d} keyA="replicasHpa" keyB="replicasAdaptive" colorA="#52a7ff" colorB="#a78bfa" /><Chart title="Adaptive threshold" unit="%" data={d} keyA="threshold" colorA="#a78bfa" ymax={100} /></div>}
            </>; })()}
          </>}

          {page === 'Compare runs' && <>
            <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> COMPARISON TOOL</div><h1>Compare runs</h1><p>Select two saved experiments to compare their adaptive algorithm results side-by-side.</p></div></div>
            <div className="compare-selectors">
              <div className="panel compare-pick"><div className="eyebrow" style={{ marginBottom: 8 }}>RUN A</div><select id="compare-a" className="compare-select" value={compareIdA} onChange={e => setCompareIdA(e.target.value)}><option value="">Select an experiment…</option>{experiments.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select>{compareA && <div className="compare-meta"><b>{compareA.config?.workload}</b> · {compareA.config?.duration}s · SLO {compareA.config?.slo_ms}ms</div>}</div>
              <div className="compare-vs">VS</div>
              <div className="panel compare-pick"><div className="eyebrow" style={{ marginBottom: 8 }}>RUN B</div><select id="compare-b" className="compare-select" value={compareIdB} onChange={e => setCompareIdB(e.target.value)}><option value="">Select an experiment…</option>{experiments.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select>{compareB && <div className="compare-meta"><b>{compareB.config?.workload}</b> · {compareB.config?.duration}s · SLO {compareB.config?.slo_ms}ms</div>}</div>
            </div>
            {(compareA || compareB) ? (() => {
              const METRICS: [string, string, string, boolean][] = [['Avg response time', 'avg_latency', ' ms', true], ['P95 latency', 'p95_latency', ' ms', true], ['SLO violations', 'slo_violation_pct', '%', true], ['Average CPU', 'avg_cpu', '%', false], ['Average replicas', 'avg_replicas', '', false], ['Scaling events', 'scaling_events', '', false]];
              const mkData = (r: Result | null) => { if (!r) return []; const c = r.runs?.conventional?.metrics ?? [], a = r.runs?.adaptive?.metrics ?? []; return c.map((p, i) => ({ t: p.t, cpuHpa: p.cpu, cpuAdaptive: a[i]?.cpu, latencyHpa: p.response_time, latencyAdaptive: a[i]?.response_time, replicasHpa: p.replicas, replicasAdaptive: a[i]?.replicas, threshold: a[i]?.threshold })); };
              return <>
                <div className="panel" style={{ marginTop: 16, padding: 0, overflow: 'hidden' }}>
                  <div className="table-row th" style={{ gridTemplateColumns: '1.5fr 1fr 1fr 0.6fr' }}><span>METRIC (ADAPTIVE)</span><span>RUN A</span><span>RUN B</span><span>WINNER</span></div>
                  {METRICS.map(([label, key, unit, lower]) => { const av = compareA?.runs?.adaptive?.summary?.[key], bv = compareB?.runs?.adaptive?.summary?.[key]; const w = av !== undefined && bv !== undefined ? (lower ? (av < bv ? 'A' : av > bv ? 'B' : 'tie') : (av > bv ? 'A' : av < bv ? 'B' : 'tie')) : null; return <div className="table-row" key={key} style={{ gridTemplateColumns: '1.5fr 1fr 1fr 0.6fr' }}><span>{label}</span><b>{av !== undefined ? `${av}${unit}` : '—'}</b><b className="violet-text">{bv !== undefined ? `${bv}${unit}` : '—'}</b><span className={`compare-winner${w === 'A' ? ' win-a' : w === 'B' ? ' win-b' : ''}`}>{w === 'A' ? '🏆 A' : w === 'B' ? '🏆 B' : w === 'tie' ? '= Tie' : '—'}</span></div>; })}
                </div>
                <div className="compare-charts">
                  {compareA && <div><div className="section-head" style={{ marginTop: 20 }}><div><h2>Run A: {compareA.name}</h2><p>Workload: {compareA.config?.workload} · Duration: {compareA.config?.duration}s · SLO: {compareA.config?.slo_ms}ms</p></div></div><div className="charts-grid"><Chart title="CPU" unit="%" data={mkData(compareA)} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} /><Chart title="Response time" unit="ms" data={mkData(compareA)} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={compareA.config?.slo_ms} /></div></div>}
                  {compareB && <div><div className="section-head" style={{ marginTop: 20 }}><div><h2>Run B: {compareB.name}</h2><p>Workload: {compareB.config?.workload} · Duration: {compareB.config?.duration}s · SLO: {compareB.config?.slo_ms}ms</p></div></div><div className="charts-grid"><Chart title="CPU" unit="%" data={mkData(compareB)} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} /><Chart title="Response time" unit="ms" data={mkData(compareB)} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={compareB.config?.slo_ms} /></div></div>}
                </div>
              </>;
            })() : <div className="empty-results" style={{ minHeight: 200 }}><div className="empty-icon"><GitCompareArrows size={24} /></div><b>Select two experiments above</b><span>Choose experiments from the dropdowns to compare their adaptive algorithm performance.</span></div>}
          </>}

          {page === 'Methodology' && <>
            <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> RESEARCH METHODOLOGY</div><h1>Methodology</h1><p>How the simulation models conventional and adaptive Kubernetes autoscaling.</p></div></div>
            <div className="method-grid">
              <div className="panel method-card"><span className="eyebrow">PROBLEM & BASELINE</span><h2>Conventional HPA</h2><p>A conventional Horizontal Pod Autoscaler reacts to a <b>fixed CPU utilization target</b>. This baseline is compared with a controller that adjusts the CPU target in response to latency relative to an application SLO.</p><div className="method-code"><span className="code-comment"># HPA replica formula</span>{'\n'}desired = ceil(current × cpu / target){'\n'}desired = clamp(desired, min, max)</div></div>
              <div className="panel method-card"><span className="eyebrow">PAPER-INSPIRED APPROACH</span><h2>Adaptive Controller</h2><p>The demonstration starts from a configured CPU threshold and adjusts it based on latency feedback each time step:</p><div className="method-code"><span className="code-comment"># Adaptive threshold update</span>{'\n'}if latency ≥ slo × critical_mult:{'\n'}{'  '}threshold -= step × 1.5{'\n'}elif latency {'>'} slo × warning_mult:{'\n'}{'  '}threshold -= step{'\n'}elif latency {'<'} slo × 0.8:{'\n'}{'  '}threshold += inc_step{'\n'}threshold = clamp(threshold, min, max)</div></div>
              <div className="panel method-card"><span className="eyebrow">EVALUATION METRICS</span><h2>What we measure</h2><ul className="method-list"><li>Average and p95 response time (ms)</li><li>SLO violation fraction (%)</li><li>CPU utilization (%)</li><li>Average and peak replica count</li><li>Number of scaling events</li></ul><p style={{ marginTop: 12 }}>Both algorithms receive the exact same deterministic user sequence for fair comparison.</p></div>
              <div className="panel method-card method-warn"><span className="eyebrow">LIMITATIONS</span><h2>Simulation boundaries</h2><p>This model omits:</p><ul className="method-list warn"><li>Kubernetes control-loop sampling delay</li><li>Real pod startup latency</li><li>Request queues and backpressure</li><li>Heterogeneous node characteristics</li><li>Measured application behavior</li></ul><p style={{ marginTop: 8, fontSize: 10, color: '#f09a79' }}>Validate simulated results against a real cluster before drawing deployment conclusions.</p></div>
            </div>
            <div className="panel method-steps"><span className="eyebrow">EXPERIMENT PLAN</span><h2>How to run a rigorous evaluation</h2><ol className="method-steps-list"><li>Fix a workload pattern, duration, initial users, peak users, and SLO.</li><li>Run both policies with those identical inputs.</li><li>Save the configuration and every simulated time step with the result.</li><li>Compare response-time distribution, SLO violations, CPU, replicas, and scaling events.</li><li>Export CSV/JSON and record that the run uses synthetic simulation.</li><li>Repeat with multiple workload shapes and parameter settings; do not generalize from a single run.</li></ol></div>
          </>}

          {page === 'Settings' && (() => {
            const [local, setLocal] = useState<Settings>({ ...settings });
            const set = (key: keyof Settings, val: number) => setLocal(p => ({ ...p, [key]: val }));
            return <>
              <div className="welcome"><div><div className="eyebrow"><span className="pulse" /> CONFIGURATION</div><h1>Settings</h1><p>Default adaptive controller parameters applied to new experiments.</p></div></div>
              <div className="settings-grid">
                <div className="panel controls">
                  <div className="panel-head"><div><span className="eyebrow">ADAPTIVE CONTROLLER DEFAULTS</span><h2>Threshold adjustment</h2></div></div>
                  <label>Warning multiplier <span className="value-inline">{local.warningMultiplier.toFixed(2)}×</span><input type="range" min="1.05" max="2" step="0.05" value={local.warningMultiplier} onChange={e => set('warningMultiplier', +e.target.value)} /><small>Latency above SLO × this → lower threshold 1 step</small></label>
                  <label>Critical multiplier <span className="value-inline">{local.criticalMultiplier.toFixed(2)}×</span><input type="range" min="1.1" max="3" step="0.1" value={local.criticalMultiplier} onChange={e => set('criticalMultiplier', +e.target.value)} /><small>Latency above SLO × this → lower threshold 1.5 steps</small></label>
                  <label>Decrease step <span className="value-inline">{local.decreaseStep}%</span><input type="range" min="1" max="30" step="1" value={local.decreaseStep} onChange={e => set('decreaseStep', +e.target.value)} /><small>CPU threshold reduction per aggressive step</small></label>
                  <label>Increase step <span className="value-inline">{local.increaseStep}%</span><input type="range" min="0.5" max="10" step="0.5" value={local.increaseStep} onChange={e => set('increaseStep', +e.target.value)} /><small>CPU threshold recovery per healthy step</small></label>
                  <div className="form-actions"><button id="btn-save-settings" className="primary" onClick={() => saveSettings(local)}>Save defaults</button><button className="subtle" onClick={() => { setLocal(DEFAULT_SETTINGS); saveSettings(DEFAULT_SETTINGS); }}><RotateCcw size={14} /> Reset</button></div>
                </div>
                <div className="panel method-card"><span className="eyebrow">ACTIVE DEFAULTS</span><h2>Currently saved</h2>{[['Warning multiplier', settings.warningMultiplier.toFixed(2) + '×'], ['Critical multiplier', settings.criticalMultiplier.toFixed(2) + '×'], ['Decrease step', settings.decreaseStep + '%'], ['Increase step', settings.increaseStep + '%']].map(([k, v]) => <div key={k} className="setting-row"><span>{k}</span><b>{v}</b></div>)}<p style={{ marginTop: 14, fontSize: 10, color: '#8290a5' }}>Settings are saved to browser localStorage and applied to all new experiments.</p></div>
              </div>
            </>;
          })()}

          {page === 'Report' && (result ? (() => {
            const r = result.runs ?? {}, c = r.conventional?.metrics ?? [], a = r.adaptive?.metrics ?? [];
            const d = c.map((p, i) => ({ t: p.t, cpuHpa: p.cpu, cpuAdaptive: a[i]?.cpu, latencyHpa: p.response_time, latencyAdaptive: a[i]?.response_time, replicasHpa: p.replicas, replicasAdaptive: a[i]?.replicas, threshold: a[i]?.threshold }));
            const cfg = result.config ?? {};
            return <>
              <div className="report-topbar"><div><div className="eyebrow">RESEARCH REPORT</div><h1 className="report-title">CloudScale Lab — Experiment Report</h1></div><button className="primary" id="btn-print" onClick={() => window.print()}><Download size={14} /> Print / Save PDF</button></div>
              <div className="panel report-meta"><span className="eyebrow">EXPERIMENT CONFIGURATION</span><div className="report-config-grid">{[['Experiment', result.name], ['Workload', cfg.workload], ['Duration', cfg.duration + 's'], ['Initial users', cfg.initial_users], ['Peak users', cfg.peak_users], ['SLO target', cfg.slo_ms + ' ms'], ['CPU threshold', cfg.cpu_threshold + '%'], ['Min replicas', cfg.min_replicas], ['Max replicas', cfg.max_replicas]].map(([k, v]) => <div key={k as string} className="report-config-item"><span>{k}</span><b>{v}</b></div>)}</div></div>
              <div className="panel" style={{ marginTop: 14, padding: 0, overflow: 'hidden' }}>
                <div className="table-row th" style={{ gridTemplateColumns: '1.5fr 1fr 1fr 0.7fr' }}><span>PERFORMANCE METRIC</span><span>CONVENTIONAL HPA</span><span>ADAPTIVE HPA</span><span>CHANGE</span></div>
                {[['Average response time', 'avg_latency', ' ms', true], ['95th percentile latency', 'p95_latency', ' ms', true], ['SLO violations', 'slo_violation_pct', '%', true], ['Average CPU utilization', 'avg_cpu', '%', false], ['Average replicas', 'avg_replicas', '', false], ['Peak replicas', 'peak_replicas', '', false], ['Scaling events', 'scaling_events', '', false]].map(([label, key, unit, lower]) => {
                  const cv = r.conventional?.summary?.[key as string], av = r.adaptive?.summary?.[key as string];
                  const delta = cv !== undefined && av !== undefined && cv !== 0 ? ((av - cv) / Math.abs(cv) * 100).toFixed(1) : null;
                  const improved = lower ? (av !== undefined && cv !== undefined && av < cv) : (av !== undefined && cv !== undefined && av > cv);
                  return <div className="table-row" key={key as string} style={{ gridTemplateColumns: '1.5fr 1fr 1fr 0.7fr' }}><span>{label}</span><b>{cv !== undefined ? `${cv}${unit}` : '—'}</b><b className="violet-text">{av !== undefined ? `${av}${unit}` : '—'}</b><span className={delta !== null ? (improved ? 'delta-good' : 'delta-bad') : ''}>{delta !== null ? `${improved ? '▼' : '▲'} ${Math.abs(+delta)}%` : '—'}</span></div>;
                })}
              </div>
              <div className="charts-grid" style={{ marginTop: 16 }}><Chart title="CPU utilization" unit="%" data={d} keyA="cpuHpa" keyB="cpuAdaptive" colorA="#52a7ff" colorB="#a78bfa" ymax={100} /><Chart title="Application response time" unit="ms" data={d} keyA="latencyHpa" keyB="latencyAdaptive" colorA="#52a7ff" colorB="#a78bfa" slo={cfg.slo_ms} /><Chart title="Replica count" unit="pods" data={d} keyA="replicasHpa" keyB="replicasAdaptive" colorA="#52a7ff" colorB="#a78bfa" /><Chart title="Adaptive CPU threshold" unit="%" data={d} keyA="threshold" colorA="#a78bfa" ymax={100} /></div>
              <div className="panel method-card" style={{ marginTop: 14 }}><span className="eyebrow">RESEARCH LIMITATIONS</span><h2>Interpretation guidance</h2><p>This experiment uses synthetic workload simulation. The controller is paper-inspired and transparent; it does not claim to reproduce a specific research paper or production Kubernetes behavior. All metrics are simulation outputs generated by a simple synthetic model. Scaling cooldown is simplified. Validate findings against a real K3s cluster before drawing deployment conclusions.</p></div>
              <div className="result-note" style={{ marginTop: 12 }}><ShieldCheck size={16} /> CloudScale Lab · Academic research prototype · Team 10 (23N217, 23N243, 23N264, 24N435) · Simulation-only output</div>
            </>;
          })() : <div className="empty-results" style={{ minHeight: 300 }}><div className="empty-icon"><FileText size={24} /></div><b>No experiment selected</b><span>Run an experiment in the Simulator first, then return here to generate a report.</span><button className="primary" style={{ marginTop: 8 }} onClick={() => setPage('Simulator')}><Play size={14} fill="currentColor" /> Go to Simulator</button></div>)}
        </div>
      </main>
    </div>
  );
}

// ── Shared components ─────────────────────────────────────────────────────────
function Kpi({ icon, label, value, meta, status, danger }: { icon: React.ReactNode; label: string; value: string; meta: string; status?: boolean; danger?: boolean }) {
  return <div className="kpi"><div className="kpi-top"><span>{label}</span><span className={`kpi-icon${danger ? ' bad' : ''}`}>{icon}</span></div><div className="kpi-value">{status && <i className="pulse" />}{value}</div><div className={`kpi-meta${danger ? ' red' : ''}`}>{meta}</div></div>;
}
function NumberField({ label, id, value, set, min, max }: { label: string; id?: string; value: number; set: (v: number) => void; min: number; max: number }) {
  return <label>{label}<input type="number" id={id} min={min} max={max} value={value} onChange={e => set(+e.target.value)} /></label>;
}
function Chart({ title, unit, data, keyA, keyB, colorA, colorB, ymax, slo }: { title: string; unit: string; data: any[]; keyA: string; keyB?: string; colorA: string; colorB?: string; ymax?: number; slo?: number }) {
  return <div className="panel chart"><div className="chart-head"><div><h3>{title}</h3><small>{unit} · simulation timeline</small></div><button className="chart-more">···</button></div><div className="chart-body">{data.length ? <ResponsiveContainer width="100%" height="100%"><ComposedChart data={data} margin={{ top: 12, right: 10, left: -22, bottom: 0 }}><CartesianGrid stroke="#202837" strokeDasharray="3 4" vertical={false} /><XAxis dataKey="t" tick={{ fill: '#738097', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={x => `${x}s`} /><YAxis tick={{ fill: '#738097', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, ymax ?? 'auto']} /><Tooltip contentStyle={{ background: '#111925', border: '1px solid #273347', borderRadius: 8, color: '#eef3fb', fontSize: 12 }} labelFormatter={x => `Time ${x}s`} />{slo && <ReferenceLine y={slo} stroke="#f59e0b" strokeDasharray="5 4" label={{ value: 'SLO', fill: '#fbbf24', fontSize: 10, position: 'insideTopRight' }} />}<Line type="monotone" dataKey={keyA} name="Conventional HPA" stroke={colorA} strokeWidth={2} dot={false} activeDot={{ r: 3 }} />{keyB && <Line type="monotone" dataKey={keyB} name={keyB === 'threshold' ? 'Adaptive threshold' : 'Adaptive HPA'} stroke={colorB ?? colorA} strokeWidth={2} dot={false} activeDot={{ r: 3 }} connectNulls />}</ComposedChart></ResponsiveContainer> : <div className="chart-empty"><div className="chart-placeholder">{Array.from({ length: 28 }, (_, i) => <i style={{ height: `${18 + Math.abs(Math.sin(i * .53)) * 64}%` }} key={i} />)}</div><span>Run an experiment to explore {title.toLowerCase()} trends</span></div>}</div></div>;
}
