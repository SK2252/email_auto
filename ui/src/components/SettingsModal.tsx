
import React, { useState } from 'react';
import { X, Copy, Check, MessageSquare } from 'lucide-react';

interface SettingsModalProps {
  sessionId: string;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ sessionId, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [comment, setComment] = useState('');

  const copyToClipboard = () => {
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden border border-slate-200">
        <div className="flex items-center justify-between p-6 border-b border-slate-100">
          <h3 className="text-xl font-bold text-slate-800">Session Settings</h3>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
            <X size={20} className="text-slate-500" />
          </button>
        </div>
        
        <div className="p-6 space-y-8">
          {/* Session ID section */}
          <div>
            <label className="block text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Current Session ID
            </label>
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
              <code className="flex-1 text-sm font-mono text-blue-700 truncate">{sessionId}</code>
              <button 
                onClick={copyToClipboard}
                className="shrink-0 p-2 text-slate-400 hover:text-blue-600 transition-colors"
                title="Copy to clipboard"
              >
                {copied ? <Check size={18} className="text-green-500" /> : <Copy size={18} />}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-400">Unique identifier for this specific conversation trace.</p>
          </div>

          {/* Comment Box section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare size={16} className="text-blue-500" />
              <label className="block text-sm font-semibold text-slate-500 uppercase tracking-wider">
                Internal Comments
              </label>
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add notes or feedback about this session..."
              className="w-full h-32 bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
            />
          </div>
        </div>

        <div className="p-6 bg-slate-50 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-6 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-sm font-semibold hover:bg-slate-100 transition-colors shadow-sm"
          >
            Cancel
          </button>
          <button 
            onClick={() => {
              // Logic to save comment could go here
              onClose();
            }}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
