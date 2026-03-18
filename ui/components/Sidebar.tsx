
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  MessageSquare,
  Plus,
  Settings,
  Trash2,
  Palette,
  Mail,
  AlertCircle,
  Clock,
  Tag,
  ChevronDown,
  ChevronRight as ChevronExpand,
} from 'lucide-react';
import { ChatSession } from '../types';
import { APP_NAME } from '../constants';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onOpenSettings: () => void;
}

// ---------------------------------------------------------------------------
// Nested label tree config — matches label_manager.LABEL_TREE exactly
// ---------------------------------------------------------------------------
const LABEL_TREE = [
  {
    key: 'action_needed',
    label: 'Action Needed',
    Icon: AlertCircle,
    color: {
      parent: 'text-rose-600',
      activeBg: 'bg-rose-50',
      dot: 'bg-rose-500',
    },
    children: [
      { key: 'Action Needed/High',   label: 'High',   dot: 'bg-red-500'   },
      { key: 'Action Needed/Medium', label: 'Medium', dot: 'bg-amber-400' },
      { key: 'Action Needed/Low',    label: 'Low',    dot: 'bg-slate-300' },
    ],
  },
  {
    key: 'awaiting_reply',
    label: 'Awaiting Reply',
    Icon: Clock,
    color: {
      parent: 'text-amber-600',
      activeBg: 'bg-amber-50',
      dot: 'bg-amber-500',
    },
    children: [
      { key: 'Awaiting Reply/High',   label: 'High',   dot: 'bg-red-500'   },
      { key: 'Awaiting Reply/Medium', label: 'Medium', dot: 'bg-amber-400' },
      { key: 'Awaiting Reply/Low',    label: 'Low',    dot: 'bg-slate-300' },
    ],
  },
  {
    key: 'follow_up',
    label: 'Follow Up',
    Icon: Tag,
    color: {
      parent: 'text-sky-600',
      activeBg: 'bg-sky-50',
      dot: 'bg-sky-500',
    },
    children: [
      { key: 'Follow Up/High',   label: 'High',   dot: 'bg-red-500'   },
      { key: 'Follow Up/Medium', label: 'Medium', dot: 'bg-amber-400' },
      { key: 'Follow Up/Low',    label: 'Low',    dot: 'bg-slate-300' },
    ],
  },
];

const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onOpenSettings
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const isTheme   = location.pathname === '/theme';
  const isInbox   = location.pathname === '/inbox';
  const isNewChat = location.pathname === '/chat/new';
  const currentLabel = new URLSearchParams(location.search).get('label') ?? '';

  const toggleExpand = (key: string) =>
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col h-full hidden md:flex">
      {/* Header */}
      <div
        className="p-6 flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => navigate('/')}
      >
        <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-blue-100">Y</div>
        <h1 className="font-bold text-slate-800 tracking-tight text-lg">{APP_NAME}</h1>
      </div>

      {/* New Chat Button */}
      <div className="px-4 mb-6">
        <button
          onClick={onNewChat}
          className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-2xl text-sm font-bold transition-all shadow-sm ${isNewChat ? 'bg-blue-600 text-white border-transparent' : 'bg-white border border-slate-200 text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700'}`}
        >
          <Plus size={18} />
          New Chat
        </button>
      </div>

      {/* Navigation */}
      <div className="px-4 mb-4 space-y-1">

        <button
          onClick={() => navigate('/inbox')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${isInbox && !currentLabel ? 'bg-blue-50 text-blue-700 shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
        >
          <Mail size={18} />
          Gmail Inbox
        </button>

        <button
          onClick={() => navigate('/theme')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${isTheme ? 'bg-blue-50 text-blue-700 shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
        >
          <Palette size={18} />
          Theme &amp; Fonts
        </button>

        {/* Smart Categories — Collapsible nested label tree */}
        <div className="pt-4 pb-2">
          <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-3 px-3">
            Smart Categories
          </div>
          <div className="space-y-1">
            {LABEL_TREE.map(cat => {
              const { Icon, color } = cat;
              const isOpen         = !!expanded[cat.key];
              const isParentActive = currentLabel.startsWith(cat.label);

              return (
                <div key={cat.key}>
                  {/* Parent row — click to expand/collapse */}
                  <button
                    onClick={() => toggleExpand(cat.key)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-bold transition-all
                      ${isParentActive
                        ? `${color.activeBg} ${color.parent}`
                        : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
                  >
                    <div className={`w-2 h-2 rounded-full ${isParentActive ? color.dot : 'bg-slate-300'}`} />
                    <Icon size={14} className="opacity-70" />
                    <span className="flex-1 text-left">{cat.label}</span>
                    {isOpen
                      ? <ChevronDown size={13} className="opacity-40" />
                      : <ChevronExpand size={13} className="opacity-40" />}
                  </button>

                  {/* Priority sub-items */}
                  {isOpen && (
                    <div className="ml-6 mt-0.5 space-y-0.5">
                      {cat.children.map(child => {
                        const isActive = currentLabel === child.key;
                        return (
                          <button
                            key={child.key}
                            onClick={() => navigate(`/inbox?label=${encodeURIComponent(child.key)}`)}
                            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all
                              ${isActive
                                ? `${color.activeBg} ${color.parent}`
                                : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'}`}
                          >
                            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${child.dot}`} />
                            {child.label}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-4 px-3 flex items-center justify-between">
          <span>Recent Conversations</span>
          <span className="bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded-md text-[9px]">{sessions.length}</span>
        </div>
        <div className="space-y-1">
          {sessions.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <div className="text-slate-300 mb-2"><MessageSquare size={24} className="mx-auto" /></div>
              <div className="text-xs text-slate-400 italic">No history yet</div>
            </div>
          ) : (
            sessions.map(session => (
              <div
                key={session.id}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all border ${currentSessionId === session.id ? 'bg-white border-blue-200 text-blue-800 shadow-sm' : 'border-transparent text-slate-600 hover:bg-slate-200/50'}`}
                onClick={() => onSelectSession(session.id)}
              >
                <MessageSquare size={16} className={`shrink-0 ${currentSessionId === session.id ? 'text-blue-500' : 'opacity-40'}`} />
                <span className="flex-1 truncate text-xs font-semibold">
                  {session.title || 'Untitled Chat'}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-600 transition-opacity"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Footer Settings */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-100 hover:text-blue-600 transition-all group"
        >
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-blue-50 transition-colors">
            <Settings size={18} />
          </div>
          Settings
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
