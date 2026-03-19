
import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Mail, Search, RefreshCw, ChevronRight, Inbox, Clock, CheckCircle, AlertCircle, Tag, X } from 'lucide-react';

interface EmailMessage {
    id: string;
    threadId: string;
    subject: string;
    from: string;
    date: string;
    snippet: string;
    labelIds: string[];
}

const EmailInbox: React.FC = () => {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const labelFilter = queryParams.get('label');

    const [allMessages, setAllMessages] = useState<EmailMessage[]>([]);
    const [filteredMessages, setFilteredMessages] = useState<EmailMessage[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [isBackfilling, setIsBackfilling] = useState(false);

    const fetchEmails = async (query = '', showLoader = true) => {
        if (showLoader) setLoading(true);
        try {
            const response = await fetch(`http://localhost:9000/api/v1/gmail/search?q=${encodeURIComponent(query)}&max_results=20`, {
                headers: {
                    'x-api-key': 'dummy-key'
                }
            });
            const data = await response.json();
            if (data.status === 'OK') {
                setAllMessages(data.messages);
            }
        } catch (error) {
            console.error("Failed to fetch emails", error);
        } finally {
            if (showLoader) setLoading(false);
        }
    };

    const handleBackfill = async () => {
        setIsBackfilling(true);
        try {
            await fetch('http://localhost:9000/api/v1/gmail/backfill', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': 'dummy-key'
                },
                body: JSON.stringify({ max_results: 50 })
            });
            alert("Autonomous labeling started. Refresh in a moment to see updates.");
        } catch (error) {
            console.error("Failed to trigger backfill", error);
        } finally {
            setIsBackfilling(false);
        }
    };

    useEffect(() => {
        fetchEmails();
    }, []);

    // Real-Time Server-Sent Events (SSE) updates
    useEffect(() => {
        const eventSource = new EventSource('http://localhost:9000/api/v1/gmail/events');

        eventSource.onmessage = (event) => {
            console.log("Received email update event:", event.data);
            fetchEmails(searchTerm, false); // Fetch the latest inbox invisibly
        };

        eventSource.onerror = (error) => {
            console.error("SSE Error:", error);
            // EventSource auto-reconnects natively.
        };

        return () => eventSource.close();
    }, [searchTerm]);

    useEffect(() => {
        if (!labelFilter) {
            setFilteredMessages(allMessages);
            return;
        }
        // Support nested label names like "Action Needed/High"
        const needle = labelFilter.toLowerCase();
        setFilteredMessages(
            allMessages.filter(msg =>
                msg.labelIds.some(id => id.toLowerCase() === needle)
            )
        );
    }, [labelFilter, allMessages]);

    // Priority badge styles
    const PRIORITY_BADGE: Record<string, { label: string; cls: string }> = {
        high:   { label: 'High',   cls: 'bg-red-50 border-red-100 text-red-600'         },
        medium: { label: 'Medium', cls: 'bg-amber-50 border-amber-100 text-amber-600'   },
        low:    { label: 'Low',    cls: 'bg-slate-50 border-slate-200 text-slate-500'   },
    };

    const getCategoryBadge = (labels: string[]) => {
        // Look for a nested label like "Action Needed/High"
        const nested   = labels.find(l => l.includes('/'));
        const parts    = nested ? nested.split('/') : [];
        const catPart  = parts[0] ?? null;
        const prioPart = parts[1]?.toLowerCase() ?? null;

        const isAction   = labels.some(l => l.toLowerCase().includes('action'));
        const isAwaiting = labels.some(l => l.toLowerCase().includes('awaiting'));
        const isFollowUp = labels.some(l => l.toLowerCase().includes('follow'));

        const catBadge =
            isAction   ? { text: catPart ?? 'Action Needed',  cls: 'bg-rose-50 border-rose-100 text-rose-600',   Icon: AlertCircle } :
            isAwaiting ? { text: catPart ?? 'Awaiting Reply',  cls: 'bg-amber-50 border-amber-100 text-amber-600', Icon: Clock       } :
            isFollowUp ? { text: catPart ?? 'Follow Up',       cls: 'bg-sky-50 border-sky-100 text-sky-600',       Icon: Tag         } : null;

        if (!catBadge) return null;
        const prioBadge = prioPart ? PRIORITY_BADGE[prioPart] : null;

        return (
            <div className="flex items-center gap-1.5">
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border shadow-sm text-[10px] font-bold uppercase tracking-wider ${catBadge.cls}`}>
                    <catBadge.Icon size={12} strokeWidth={2.5} />
                    <span>{catBadge.text}</span>
                </div>
                {prioBadge && (
                    <div className={`px-2 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${prioBadge.cls}`}>
                        {prioBadge.label}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-[#F8FAFC]">
            {/* Header with Glassmorphism */}
            <header className="sticky top-0 z-10 px-8 py-6 bg-white/80 backdrop-blur-md border-b border-slate-200/60 shadow-sm">
                <div className="max-w-5xl mx-auto flex flex-col gap-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <div className="absolute inset-0 bg-blue-500 blur-lg opacity-20 rounded-full"></div>
                                <div className="relative p-3 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-2xl shadow-lg">
                                    <Inbox size={26} strokeWidth={1.5} />
                                </div>
                            </div>
                            <div>
                                <h1 className="text-2xl font-black text-slate-900 tracking-tight">AI Workspace Inbox</h1>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Autonomous Triage Active</p>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={handleBackfill}
                            disabled={isBackfilling}
                            className="group flex items-center gap-2.5 px-5 py-2.5 bg-slate-900 hover:bg-black text-white rounded-xl text-sm font-bold shadow-xl shadow-slate-200 hover:shadow-slate-300 active:scale-95 transition-all disabled:opacity-50"
                        >
                            <RefreshCw size={18} className={`${isBackfilling ? 'animate-spin' : 'group-hover:rotate-180'} transition-transform duration-700`} />
                            <span>Run Autonomous Sync</span>
                        </button>
                    </div>

                    {/* active filter badge */}
                    {labelFilter && (
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Filtering by</span>
                            <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-lg border border-blue-100 text-xs font-bold">
                                {labelFilter.split('/').join(' \u203a ')}
                                <button
                                    onClick={() => window.history.pushState({}, '', '/#/inbox')}
                                    className="p-0.5 hover:bg-blue-100 rounded"
                                >
                                    <X size={12} />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Search Field */}
                    <div className="relative group max-w-2xl">
                        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                            <Search className="text-slate-400 group-focus-within:text-blue-500 transition-colors" size={20} />
                        </div>
                        <input
                            type="text"
                            placeholder="Find emails by subject..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && fetchEmails(searchTerm)}
                            className="w-full pl-12 pr-6 py-4 bg-slate-100 hover:bg-slate-200/50 focus:bg-white border-2 border-transparent focus:border-blue-500/20 rounded-2xl text-slate-700 font-medium shadow-inner transition-all outline-none"
                        />
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto overflow-x-hidden pt-8 pb-12 px-8">
                <div className="max-w-5xl mx-auto">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-32 text-slate-400">
                            <div className="relative w-24 h-24 mb-6">
                                <div className="absolute inset-0 border-4 border-blue-500/10 rounded-full"></div>
                                <div className="absolute inset-0 border-4 border-t-blue-600 rounded-full animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Mail size={32} className="text-blue-600/40" />
                                </div>
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 mb-1">Scanning Threads</h3>
                            <p className="text-sm font-medium opacity-60 italic">Querying Gmail AI Subsystem...</p>
                        </div>
                    ) : filteredMessages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-32 text-center bg-white rounded-[32px] border-2 border-dashed border-slate-200">
                            <div className="w-20 h-20 bg-slate-50 text-slate-200 rounded-3xl flex items-center justify-center mb-6">
                                <Mail size={40} />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-2">No Labeled Emails Yet</h3>
                            <p className="text-slate-500 max-w-xs mx-auto text-sm leading-relaxed">
                                {labelFilter ? `No emails found for the ${labelFilter.replace('_', ' ')} category.` : "Click 'Run Autonomous Sync' above to let the LLM categorize your recent communications."}
                            </p>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                            {filteredMessages.map((msg, idx) => (
                                <div
                                    key={msg.id}
                                    style={{ animationDelay: `${idx * 50}ms` }}
                                    className="group relative p-5 bg-white hover:bg-slate-50 border border-slate-200/80 rounded-[28px] shadow-sm hover:shadow-xl hover:shadow-blue-500/5 hover:-translate-y-1 transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-bottom-4 flex items-center justify-between overflow-hidden"
                                >
                                    <div className="flex items-center gap-6 flex-1 min-w-0">
                                        {/* Avatar / Icon Container */}
                                        <div className="flex-shrink-0 w-14 h-14 bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl flex items-center justify-center text-slate-400 group-hover:from-blue-600 group-hover:to-indigo-600 group-hover:text-white transition-all duration-500 transform group-hover:rotate-6">
                                            <Mail size={24} strokeWidth={1.5} />
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <div className="flex flex-wrap items-center gap-3 mb-1.5">
                                                <h3 className="text-base font-black text-slate-900 truncate group-hover:text-blue-600 transition-colors leading-tight">
                                                    {msg.subject || "(Empty Subject)"}
                                                </h3>
                                                {/* Category badges removed for cleaner UI as per feat commit */}
                                                {/* {getCategoryBadge(msg.labelIds)} */}
                                            </div>
                                            <div className="flex items-center gap-3 text-sm font-medium text-slate-400 group-hover:text-slate-500">
                                                <span className="truncate max-w-[220px]">{msg.from}</span>
                                                <span className="w-1 h-1 bg-slate-300 rounded-full flex-shrink-0"></span>
                                                <span className="flex-shrink-0">{msg.date}</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Action Hover */}
                                    <div className="flex items-center gap-3 pl-6">
                                        <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-300 shadow-md">
                                            <ChevronRight size={20} strokeWidth={2.5} />
                                        </div>
                                    </div>

                                    {/* Subtle Gradient Accent */}
                                    <div className="absolute top-0 right-0 w-1 h-full bg-blue-600 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

export default EmailInbox;
