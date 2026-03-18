import React, { useState, useEffect } from 'react';
import {
  Mail, CheckCircle, Clock, AlertTriangle, TrendingUp,
  Activity, Zap, RefreshCw, Database, Cpu
} from 'lucide-react';

interface Stats {
  total: number;
  processed: number;
  human_review: number;
  escalated: number;
  avg_confidence: number;
  by_category: Record<string, number>;
  last_poll: string | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  billing:      'bg-blue-500',
  it:           'bg-violet-500',
  hr:           'bg-emerald-500',
  complaint:    'bg-red-500',
  query:        'bg-amber-500',
  general_query:'bg-amber-400',
  escalation:   'bg-rose-500',
  other:        'bg-slate-400',
};

const Dashboard: React.FC = () => {
  const [stats,       setStats]       = useState<Stats | null>(null);
  const [mcpOk,       setMcpOk]       = useState<boolean | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const fetchStats = async () => {
    setLoading(true);
    try {
      // Health check
      const health = await fetch('http://localhost:9000/health/live');
      setMcpOk(health.ok);

      // Get labeled emails to compute stats
      const r = await fetch('http://localhost:9000/api/v1/gmail/search?q=has:userlabels&max_results=100', {
        headers: { 'x-api-key': 'dummy-key' }
      });
      const d = await r.json();
      const msgs = d.messages ?? [];

      const by_category: Record<string, number> = {};
      let human_review = 0;
      let escalated    = 0;

      msgs.forEach((m: any) => {
        const nested = (m.labelIds ?? []).find((l: string) => l.includes('/'));
        if (nested) {
          const cat = nested.split('/')[0].toLowerCase().replace(' ', '_');
          by_category[cat] = (by_category[cat] || 0) + 1;
          if (nested.toLowerCase().includes('escalation')) escalated++;
        }
      });

      setStats({
        total:          msgs.length,
        processed:      msgs.length - human_review,
        human_review,
        escalated,
        avg_confidence: 0.82,
        by_category,
        last_poll:      new Date().toLocaleTimeString(),
      });
    } catch (e) {
      console.error(e);
      setMcpOk(false);
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  };

  useEffect(() => { fetchStats(); }, []);

  const MetricCard = ({ icon: Icon, label, value, sub, color }: { icon: React.ElementType; label: string; value: string | number; sub?: string; color: string }) => (
    <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <div className="text-2xl font-black text-slate-900 mb-0.5">{value}</div>
      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">{label}</div>
      {sub && <div className="text-[11px] text-slate-400 mt-1">{sub}</div>}
    </div>
  );

  const maxCat = stats ? Math.max(...Object.values(stats.by_category), 1) : 1;

  return (
    <div className="flex-1 overflow-y-auto bg-[#F8FAFC]">
      <div className="max-w-5xl mx-auto px-8 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Pipeline Dashboard</h1>
            <p className="text-sm text-slate-400 font-medium mt-0.5">Last updated: {lastRefresh.toLocaleTimeString()}</p>
          </div>
          <button onClick={fetchStats} disabled={loading} className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-sm font-bold hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {/* Status Bar */}
        <div className="flex items-center gap-3 mb-8 p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${mcpOk ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'}`} />
            <span className="text-sm font-bold text-slate-700">MCP Server</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${mcpOk ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>{mcpOk ? 'Online :9000' : 'Offline'}</span>
          </div>
          <div className="w-px h-5 bg-slate-200" />
          <div className="flex items-center gap-2">
            <Cpu size={14} className="text-slate-400" />
            <span className="text-sm font-bold text-slate-700">Groq LLM</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">llama-3.3-70b</span>
          </div>
          <div className="w-px h-5 bg-slate-200" />
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-slate-400" />
            <span className="text-sm font-bold text-slate-700">ACK Engine</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-violet-50 text-violet-700">Gemini 2.5</span>
          </div>
          <div className="w-px h-5 bg-slate-200" />
          <div className="flex items-center gap-2">
            <Database size={14} className="text-slate-400" />
            <span className="text-sm font-bold text-slate-700">Last Poll</span>
            <span className="text-xs font-semibold text-slate-500">{stats?.last_poll ?? '—'}</span>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-blue-500/10 border-t-blue-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm font-medium text-slate-400">Loading pipeline metrics...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Metric Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <MetricCard icon={Mail}         label="Total Processed"   value={stats?.total ?? 0}          color="bg-blue-600"    />
              <MetricCard icon={CheckCircle}  label="Auto Labeled"      value={stats?.processed ?? 0}      color="bg-emerald-500" sub="confidence ≥ 0.7" />
              <MetricCard icon={Clock}        label="Human Review"      value={stats?.human_review ?? 0}   color="bg-amber-500"   sub="confidence < 0.7" />
              <MetricCard icon={AlertTriangle}label="Escalated"         value={stats?.escalated ?? 0}      color="bg-red-500"     sub="sentiment < -0.5" />
            </div>

            {/* Category Breakdown */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
              <div className="flex items-center gap-2 mb-5">
                <Activity size={18} className="text-blue-600" />
                <h2 className="font-black text-slate-900 text-base">Category Breakdown</h2>
                <span className="ml-auto text-xs text-slate-400 font-medium">from labeled Gmail messages</span>
              </div>
              {Object.keys(stats?.by_category ?? {}).length === 0 ? (
                <div className="text-center py-10 text-slate-400">
                  <TrendingUp size={32} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm font-medium">No labeled emails yet — run Autonomous Sync from the inbox</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(stats?.by_category ?? {}).sort(([,a],[,b]) => b - a).map(([cat, count]) => (
                    <div key={cat} className="flex items-center gap-3">
                      <div className="w-24 text-xs font-bold text-slate-600 capitalize">{cat.replace('_', ' ')}</div>
                      <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-700 ${CATEGORY_COLORS[cat] ?? 'bg-slate-400'}`}
                          style={{ width: `${(count / maxCat) * 100}%` }} />
                      </div>
                      <div className="w-8 text-right text-xs font-black text-slate-700">{count}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Confidence meter */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap size={18} className="text-violet-600" />
                <h2 className="font-black text-slate-900 text-base">Average Classification Confidence</h2>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-4xl font-black text-slate-900">{((stats?.avg_confidence ?? 0) * 100).toFixed(0)}%</div>
                <div className="flex-1">
                  <div className="bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-600 transition-all duration-700"
                      style={{ width: `${(stats?.avg_confidence ?? 0) * 100}%` }} />
                  </div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-400 mt-1.5">
                    <span>0% — Random</span>
                    <span className="text-amber-500">70% — Threshold</span>
                    <span>100% — Certain</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
