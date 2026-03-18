import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Mail, Search, RefreshCw, ChevronRight, Inbox, X,
  CreditCard, Monitor, Users, AlertTriangle, HelpCircle,
  TrendingUp, ShieldAlert, Activity, Eye
} from 'lucide-react';

interface EmailMessage {
  id: string;
  threadId: string;
  subject: string;
  from: string;
  date: string;
  snippet: string;
  labelIds: string[];
}

interface SupabaseEmail {
  external_id: string;
  subject: string;
  sender: string;
  current_step: string;
  classification_result: { category: string; priority: string; confidence: number } | null;
  confidence: number;
  sentiment_score: number;
  created_at: string;
}

// Maps Gmail label names → icon + color
const LABEL_META: Record<string, { Icon: React.ElementType; cls: string; dot: string }> = {
  'Billing':    { Icon: CreditCard,    cls: 'bg-blue-50 border-blue-100 text-blue-700',       dot: 'bg-blue-500'    },
  'IT Support': { Icon: Monitor,       cls: 'bg-violet-50 border-violet-100 text-violet-700', dot: 'bg-violet-500'  },
  'HR':         { Icon: Users,         cls: 'bg-emerald-50 border-emerald-100 text-emerald-700', dot: 'bg-emerald-500' },
  'Complaint':  { Icon: AlertTriangle, cls: 'bg-red-50 border-red-100 text-red-700',          dot: 'bg-red-500'     },
  'Query':      { Icon: HelpCircle,    cls: 'bg-amber-50 border-amber-100 text-amber-700',    dot: 'bg-amber-500'   },
  'Escalation': { Icon: TrendingUp,    cls: 'bg-rose-50 border-rose-100 text-rose-700',       dot: 'bg-rose-500'    },
  'Other':      { Icon: ShieldAlert,   cls: 'bg-slate-50 border-slate-200 text-slate-600',    dot: 'bg-slate-400'   },
};

const PRIORITY_CLS: Record<string, string> = {
  high:   'bg-red-50 border-red-100 text-red-600',
  medium: 'bg-amber-50 border-amber-100 text-amber-600',
  low:    'bg-slate-50 border-slate-200 text-slate-500',
};

const EmailInbox: React.FC = () => {
  const location    = useLocation();
  const labelFilter = new URLSearchParams(location.search).get('label');
  const isHumanReview = labelFilter === 'human_review';

  const [allMessages,      setAllMessages]      = useState<EmailMessage[]>([]);
  const [humanReviewEmails,setHumanReviewEmails] = useState<SupabaseEmail[]>([]);
  const [filteredMessages, setFilteredMessages] = useState<EmailMessage[]>([]);
  const [loading,          setLoading]          = useState(true);
  const [searchTerm,       setSearchTerm]       = useState('');
  const [isBackfilling,    setIsBackfilling]    = useState(false);
  const [selectedEmail,    setSelectedEmail]    = useState<EmailMessage | null>(null);

  // ── Fetch Gmail messages via MCP REST API ──────────────────────────────
  const fetchEmails = async (query = '', showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const labelParam = labelFilter && !isHumanReview ? `&label_id=${encodeURIComponent(labelFilter)}` : '';
      const r = await fetch(`http://localhost:9000/api/v1/gmail/search?q=${encodeURIComponent(query)}${labelParam}&max_results=30`, {
        headers: { 'x-api-key': 'dummy-key' }
      });
      const d = await r.json();
      if (d.status === 'OK') setAllMessages(d.messages ?? []);
    } catch (e) {
      console.error('fetchEmails failed', e);
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  // ── Fetch human review queue from Supabase via MCP search ─────────────
  const fetchHumanReview = async () => {
    setLoading(true);
    try {
      const r = await fetch('http://localhost:9000/api/v1/gmail/search?q=label:human_review&max_results=50', {
        headers: { 'x-api-key': 'dummy-key' }
      });
      const d = await r.json();
      if (d.status === 'OK') setAllMessages(d.messages ?? []);
    } catch (e) {
      console.error('fetchHumanReview failed', e);
    } finally {
      setLoading(false);
    }
  };

  const handleBackfill = async () => {
    setIsBackfilling(true);
    try {
      await fetch('http://localhost:9000/api/v1/gmail/backfill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': 'dummy-key' },
        body: JSON.stringify({ max_results: 50 })
      });
      alert('Autonomous labeling started. Refresh in a moment to see updates.');
    } catch (e) {
      console.error(e);
    } finally {
      setIsBackfilling(false);
    }
  };

  useEffect(() => {
    if (isHumanReview) fetchHumanReview();
    else fetchEmails();
  }, [labelFilter]);

  // SSE real-time updates
  useEffect(() => {
    const es = new EventSource('http://localhost:9000/api/v1/gmail/events');
    es.onmessage = () => { if (!isHumanReview) fetchEmails(searchTerm, false); };
    es.onerror   = e => console.error('SSE error', e);
    return () => es.close();
  }, [searchTerm, isHumanReview]);

  useEffect(() => {
    if (!labelFilter || isHumanReview) { setFilteredMessages(allMessages); return; }
    const needle = labelFilter.toLowerCase();
    setFilteredMessages(allMessages.filter(m => m.labelIds.some(id => id.toLowerCase() === needle)));
  }, [labelFilter, allMessages]);

  // ── Category badge ─────────────────────────────────────────────────────
  const getCategoryBadge = (labels: string[]) => {
    const nested   = labels.find(l => l.includes('/'));
    const parts    = nested ? nested.split('/') : [];
    const catName  = parts[0] ?? null;
    const prioName = parts[1]?.toLowerCase() ?? null;
    if (!catName || !LABEL_META[catName]) return null;
    const { Icon, cls } = LABEL_META[catName];
    return (
      <div className="flex items-center gap-1.5">
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border shadow-sm text-[10px] font-bold uppercase tracking-wider ${cls} dark:bg-slate-800 dark:border-slate-700`}>
          <Icon size={11} strokeWidth={2.5} />
          <span>{catName}</span>
        </div>
        {prioName && PRIORITY_CLS[prioName] && (
          <div className={`px-2 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${PRIORITY_CLS[prioName]} dark:bg-slate-800 dark:border-slate-700`}>
            {parts[1]}
          </div>
        )}
      </div>
    );
  };

  // ── Email detail panel ─────────────────────────────────────────────────
  const EmailDetailPanel = ({ email, onClose }: { email: EmailMessage; onClose: () => void }) => (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white">
              <Mail size={18} />
            </div>
            <div>
              <h3 className="font-black text-slate-900 dark:text-slate-100 text-base leading-tight">{email.subject || '(No Subject)'}</h3>
              <p className="text-xs text-slate-400 dark:text-slate-500 font-medium mt-0.5">{email.from}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"><X size={18} className="text-slate-500" /></button>
        </div>
        <div className="p-6 overflow-y-auto flex-1">
          <div className="flex flex-wrap gap-2 mb-5">
            {getCategoryBadge(email.labelIds)}
            {email.labelIds.filter(l => ['INBOX','UNREAD','IMPORTANT'].includes(l)).map(l => (
              <span key={l} className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[10px] font-bold uppercase tracking-wider">{l}</span>
            ))}
          </div>
          <div className="bg-slate-50 dark:bg-slate-950 rounded-2xl p-4 text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium min-h-[120px]">
            {email.snippet || 'No preview available.'}
            <span className="text-slate-400 dark:text-slate-600 italic"> [Full content in Gmail]</span>
          </div>
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800">
            <div className="text-[10px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">AI Classification</div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Thread ID', value: email.threadId?.slice(0,12)+'...' },
                { label: 'Message ID', value: email.id?.slice(0,12)+'...' },
                { label: 'Date', value: email.date },
              ].map(item => (
                <div key={item.label} className="bg-slate-50 dark:bg-slate-950 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mb-1">{item.label}</div>
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 font-mono truncate">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800 flex gap-3">
          <a href={`https://mail.google.com/mail/#inbox/${email.threadId}`} target="_blank" rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-bold transition-colors shadow-lg shadow-blue-200/20">
            <Eye size={16} /> Open in Gmail
          </a>
          <button onClick={onClose} className="px-5 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-bold hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
            Close
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-[#F8FAFC] dark:bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-10 px-8 py-5 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/60 shadow-sm">
        <div className="max-w-5xl mx-auto flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 blur-lg opacity-20 rounded-full" />
                <div className={`relative p-3 text-white rounded-2xl shadow-lg ${isHumanReview ? 'bg-gradient-to-br from-amber-500 to-orange-600' : 'bg-gradient-to-br from-blue-600 to-indigo-700'}`}>
                  {isHumanReview ? <Activity size={24} strokeWidth={1.5} /> : <Inbox size={24} strokeWidth={1.5} />}
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
                  {isHumanReview ? 'Human Review Queue' : labelFilter ? labelFilter.replace('/', ' › ') : 'AI Workspace Inbox'}
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                    {isHumanReview ? `${filteredMessages.length} emails awaiting review` : 'Autonomous Triage Active'}
                  </p>
                </div>
              </div>
            </div>
            {!isHumanReview && (
              <button onClick={handleBackfill} disabled={isBackfilling} className="group flex items-center gap-2.5 px-5 py-2.5 bg-slate-900 dark:bg-blue-600 hover:bg-black dark:hover:bg-blue-700 text-white rounded-xl text-sm font-bold shadow-xl active:scale-95 transition-all disabled:opacity-50">
                <RefreshCw size={17} className={`${isBackfilling ? 'animate-spin' : 'group-hover:rotate-180'} transition-transform duration-700`} />
                Run Autonomous Sync
              </button>
            )}
          </div>

          {labelFilter && !isHumanReview && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">Filtering by</span>
              <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg border border-blue-100 dark:border-blue-800 text-xs font-bold">
                {labelFilter.split('/').join(' › ')}
                <button onClick={() => window.history.pushState({},'','/#/inbox')} className="p-0.5 hover:bg-blue-100 dark:hover:bg-blue-800 rounded"><X size={11} /></button>
              </div>
            </div>
          )}

          {!isHumanReview && (
            <div className="relative max-w-2xl">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" size={18} />
              <input type="text" placeholder="Find emails by subject..." value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchEmails(searchTerm)}
                className="w-full pl-11 pr-5 py-3.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200/50 dark:hover:bg-slate-700 focus:bg-white dark:focus:bg-slate-900 border-2 border-transparent focus:border-blue-500/20 rounded-2xl text-slate-700 dark:text-slate-200 font-medium shadow-inner outline-none transition-all text-sm" />
            </div>
          )}
        </div>
      </header>

      {/* List */}
      <main className="flex-1 overflow-y-auto pt-6 pb-12 px-8">
        <div className="max-w-5xl mx-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400 dark:text-slate-600">
              <div className="relative w-20 h-20 mb-5">
                <div className="absolute inset-0 border-4 border-blue-500/10 rounded-full" />
                <div className="absolute inset-0 border-4 border-t-blue-600 rounded-full animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center"><Mail size={28} className="text-blue-600/40" /></div>
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">Scanning Threads</h3>
              <p className="text-sm font-medium opacity-60 italic">Querying Gmail AI Subsystem...</p>
            </div>
          ) : filteredMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32 text-center bg-white dark:bg-slate-900 rounded-[32px] border-2 border-dashed border-slate-200 dark:border-slate-800">
              <div className="w-16 h-16 bg-slate-50 dark:bg-slate-800 text-slate-200 dark:text-slate-700 rounded-3xl flex items-center justify-center mb-5">
                {isHumanReview ? <Activity size={32} /> : <Mail size={32} />}
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{isHumanReview ? 'No Emails in Review Queue' : 'No Labeled Emails Yet'}</h3>
              <p className="text-slate-500 dark:text-slate-400 max-w-xs mx-auto text-sm leading-relaxed">
                {isHumanReview ? 'All emails have been processed with high confidence.' : labelFilter ? `No emails found for ${labelFilter}.` : "Click 'Run Autonomous Sync' to start triage."}
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {filteredMessages.map((msg, idx) => (
                <div key={msg.id} onClick={() => setSelectedEmail(msg)}
                  style={{ animationDelay: `${idx * 40}ms` }}
                  className="group relative p-5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50 border border-slate-200/80 dark:border-slate-800 rounded-[24px] shadow-sm hover:shadow-lg hover:shadow-blue-500/5 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer animate-in fade-in slide-in-from-bottom-3 flex items-center justify-between overflow-hidden">
                  <div className="flex items-center gap-5 flex-1 min-w-0">
                    <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl flex items-center justify-center text-slate-400 dark:text-slate-600 group-hover:from-blue-600 group-hover:to-indigo-600 group-hover:text-white transition-all duration-300">
                      <Mail size={20} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2.5 mb-1">
                        <h3 className="text-sm font-black text-slate-900 dark:text-slate-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{msg.subject || '(Empty Subject)'}</h3>
                        {getCategoryBadge(msg.labelIds)}
                      </div>
                      <div className="flex items-center gap-2.5 text-xs font-medium text-slate-400 dark:text-slate-500">
                        <span className="truncate max-w-[200px]">{msg.from}</span>
                        <span className="w-1 h-1 bg-slate-300 dark:bg-slate-700 rounded-full" />
                        <span className="flex-shrink-0">{msg.date}</span>
                      </div>
                      {msg.snippet && <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500 truncate max-w-lg">{msg.snippet}</p>}
                    </div>
                  </div>
                  <div className="pl-4">
                    <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-200 shadow-sm">
                      <ChevronRight size={18} strokeWidth={2.5} />
                    </div>
                  </div>
                  <div className="absolute top-0 right-0 w-1 h-full bg-blue-600 opacity-0 group-hover:opacity-100 transition-opacity rounded-r-[24px]" />
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {selectedEmail && <EmailDetailPanel email={selectedEmail} onClose={() => setSelectedEmail(null)} />}
    </div>
  );
};

export default EmailInbox;
