
import React, { useState, useEffect, useCallback } from 'react';
import { HashRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import ThemePage from './components/ThemePage';
import SettingsModal from './components/SettingsModal';
import EmailInbox from './pages/EmailInbox';
import Dashboard from './pages/Dashboard';
import { ChatSession, Message, ThemeConfig } from './types';
import { APP_NAME, FONTS } from './constants';
import { v4 as uuidv4 } from 'uuid';

const App: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<ThemeConfig>({
    fontFamily: 'inter',
    primaryColor: '#2563eb',
    isDarkMode: false,
  });

  // Persist sessions
  useEffect(() => {
    const saved = localStorage.getItem('yakkay_sessions');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSessions(parsed);
      } catch (e) {
        console.error("Failed to parse sessions", e);
      }
    }

    // Persist theme
    const savedTheme = localStorage.getItem('yakkay_theme');
    if (savedTheme) {
      try {
        setTheme(JSON.parse(savedTheme));
      } catch (e) {
        console.error("Failed to parse theme", e);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('yakkay_sessions', JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    localStorage.setItem('yakkay_theme', JSON.stringify(theme));
    
    // Apply dark mode class to html element
    if (theme.isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const handleNewChatNavigation = (navigate: any) => {
    navigate('/chat/new');
  };

  const createSessionAndReturn = (initialMessage?: string): ChatSession => {
    const newSession: ChatSession = {
      id: uuidv4(),
      title: initialMessage ? initialMessage.slice(0, 30) : 'New Chat',
      messages: [],
      createdAt: Date.now(),
    };
    setSessions(prev => [newSession, ...prev]);
    return newSession;
  };

  const deleteSession = (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
  };

  return (
    <Router>
      <AppContent
        sessions={sessions}
        setSessions={setSessions}
        theme={theme}
        setTheme={setTheme}
        isSettingsOpen={isSettingsOpen}
        setIsSettingsOpen={setIsSettingsOpen}
        createSessionAndReturn={createSessionAndReturn}
        deleteSession={deleteSession}
        handleNewChatNavigation={handleNewChatNavigation}
      />
    </Router>
  );
};

// Internal component to use navigation hooks
const AppContent: React.FC<any> = ({
  sessions,
  setSessions,
  theme,
  setTheme,
  isSettingsOpen,
  setIsSettingsOpen,
  createSessionAndReturn,
  deleteSession,
  handleNewChatNavigation
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Extract session ID from URL if applicable
  const chatIdMatch = location.pathname.match(/\/chat\/([^\/]+)/);
  const currentChatId = chatIdMatch ? chatIdMatch[1] : null;
  const currentSession = sessions.find((s: any) => s.id === currentChatId) || null;

  return (
    <div
      className="flex h-screen w-full bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-300"
      style={{ fontFamily: FONTS[theme.fontFamily] }}
    >
      <Sidebar
        sessions={sessions}
        currentSessionId={currentChatId}
        onSelectSession={(id: string) => navigate(`/chat/${id}`)}
        onNewChat={() => handleNewChatNavigation(navigate)}
        onDeleteSession={deleteSession}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <main className="flex-1 flex flex-col relative overflow-hidden">
        <Routes>
          <Route
            path="/"
            element={<Dashboard />}
          />
          <Route
            path="/dashboard"
            element={<Dashboard />}
          />
          <Route
            path="/chat/new"
            element={
              <ChatInterface
                session={null}
                setSessions={setSessions}
                onNewChat={() => { }} // Not needed here as session is created on first message
                createSessionAndReturn={createSessionAndReturn}
              />
            }
          />
          <Route
            path="/chat/:id"
            element={
              <ChatInterface
                session={currentSession}
                setSessions={setSessions}
                onNewChat={() => handleNewChatNavigation(navigate)}
                createSessionAndReturn={createSessionAndReturn}
              />
            }
          />
          <Route
            path="/inbox"
            element={<EmailInbox />}
          />
          <Route
            path="/theme"
            element={<ThemePage theme={theme} setTheme={setTheme} />}
          />
        </Routes>
      </main>

      {isSettingsOpen && (
        <SettingsModal
          sessionId={currentChatId || "N/A"}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}
    </div>
  );
};

export default App;
