
import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Bot, Loader2 } from 'lucide-react';
import { AgentProcessing } from './AgentProcessing';
import { useNavigate } from 'react-router-dom';
import { ChatSession, Message, Role } from '../types';
import { orchestrator } from '../services/orchestratorService';
import { v4 as uuidv4 } from 'uuid';

interface ChatInterfaceProps {
  session: ChatSession | null;
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
  onNewChat: () => void;
  createSessionAndReturn: (msg: string) => ChatSession;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ session, setSessions, onNewChat, createSessionAndReturn }) => {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [session?.messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    let activeSession = session;
    const currentInput = input;
    setInput('');

    // If no session exists (Fresh Page), create one first
    if (!activeSession) {
      activeSession = createSessionAndReturn(currentInput);
      // Navigate to the new session URL without interrupting the flow
      navigate(`/chat/${activeSession.id}`, { replace: true });
    }

    const userMsg: Message = {
      id: uuidv4(),
      role: Role.USER,
      content: currentInput,
      timestamp: Date.now(),
    };

    const botMsgId = uuidv4();
    const botMsg: Message = {
      id: botMsgId,
      role: Role.MODEL,
      content: '',
      timestamp: Date.now(),
    };

    // Update session locally
    setSessions(prev => prev.map(s => {
      if (s.id === activeSession!.id) {
        return {
          ...s,
          title: s.messages.length === 0 ? currentInput.slice(0, 30) : s.title,
          messages: [...s.messages, userMsg, botMsg]
        };
      }
      return s;
    }));

    setIsTyping(true);

    try {
      let fullContent = "";
      // Pass history to orchestrator service with session ID
      const stream = orchestrator.streamChat(activeSession.messages, currentInput, activeSession.id);

      for await (const chunk of stream) {
        fullContent += chunk;
        setSessions(prev => prev.map(s => {
          if (s.id === activeSession!.id) {
            return {
              ...s,
              messages: s.messages.map(m => m.id === botMsgId ? { ...m, content: fullContent } : m)
            };
          }
          return s;
        }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsTyping(false);
    }
  };

  if (!session) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-white dark:bg-slate-950 relative">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl mb-6 flex items-center justify-center text-white shadow-xl shadow-blue-200/20">
          <Sparkles size={32} />
        </div>
        <h2 className="text-3xl font-bold text-slate-800 dark:text-slate-100 mb-2 text-center tracking-tight">How can I help you today?</h2>
        

        <div className="w-full max-w-2xl px-4">
          <div className="relative group">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Message YAKKAY..."
              className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl px-5 py-4 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-xl shadow-slate-200/10 dark:shadow-none resize-none min-h-[60px] text-slate-900 dark:text-slate-100"
              rows={1}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className={`absolute right-3 bottom-3 p-2 rounded-xl transition-all ${input.trim() ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-700' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600'}`}
            >
              <Send size={20} />
            </button>
          </div>
          
          
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-white dark:bg-slate-950 relative">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-0 py-8 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-12 pb-32">
          {session.messages.map((msg) => (
            <div key={msg.id} className={`flex gap-6 ${msg.role === Role.USER ? 'flex-row-reverse' : ''}`}>
              <div className={`w-9 h-9 shrink-0 rounded-lg flex items-center justify-center ${msg.role === Role.USER ? 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400' : 'bg-blue-600 text-white shadow-lg shadow-blue-200/10'}`}>
                {msg.role === Role.USER ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className={`flex flex-col max-w-[85%] ${msg.role === Role.USER ? 'items-end' : ''}`}>
                <div className={`prose prose-slate dark:prose-invert max-w-none text-[15px] leading-relaxed whitespace-pre-wrap ${msg.role === Role.USER ? 'bg-slate-100 dark:bg-slate-800 px-4 py-3 rounded-2xl text-slate-800 dark:text-slate-200' : 'py-1 text-slate-800 dark:text-slate-200'}`}>
                  {msg.content || (isTyping && msg.role === Role.MODEL && <div className="py-2"><AgentProcessing /></div>)}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent dark:from-slate-950 dark:via-slate-950 dark:to-transparent">
        <div className="max-w-3xl mx-auto relative group">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask YAKKAY anything..."
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl px-5 py-4 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-xl shadow-slate-200/10 dark:shadow-none resize-none min-h-[60px] max-h-48 text-slate-900 dark:text-slate-100"
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className={`absolute right-3 bottom-3 p-2 rounded-xl transition-all ${input.trim() && !isTyping ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-700' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600'}`}
          >
            <Send size={20} />
          </button>
        </div>
        <p className="text-[11px] text-center mt-3 text-slate-400 dark:text-slate-500 font-medium">
          YAKKAY AI AGENT is connected to Orchestrator Backend.
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;
