
import React from 'react';
import { Type, Check, Moon, Sun, Palette } from 'lucide-react';
import { ThemeConfig } from '../types';

interface ThemePageProps {
  theme: ThemeConfig;
  setTheme: React.Dispatch<React.SetStateAction<ThemeConfig>>;
}

const ThemePage: React.FC<ThemePageProps> = ({ theme, setTheme }) => {
  const fontOptions: { id: ThemeConfig['fontFamily']; name: string; description: string }[] = [
    { id: 'inter', name: 'Inter (Standard)', description: 'Modern, clean, and highly readable for chat interfaces.' },
    { id: 'mono', name: 'JetBrains Mono', description: 'Perfect for developers and technical documentation.' },
    { id: 'serif', name: 'Playfair Display', description: 'Elegant and classic feel for editorial content.' },
  ];

  const colorOptions = [
    { name: 'YAKKAY Blue', value: '#2563eb' },
    { name: 'Electric Purple', value: '#7c3aed' },
    { name: 'Modern Teal', value: '#0d9488' },
    { name: 'Rosewood', value: '#e11d48' },
    { name: 'Deep Slate', value: '#334155' },
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <header className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <Palette className="text-blue-600" size={32} />
            <h2 className="text-3xl font-bold text-slate-800 dark:text-slate-100">Visual Identity</h2>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-lg">Customize how YAKKAY AI AGENT looks and feels for your workspace.</p>
        </header>

        <div className="grid grid-cols-1 gap-12">
          {/* Typography Section */}
          <section className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm transition-colors duration-300">
            <div className="flex items-center gap-2 mb-6">
              <Type className="text-blue-500" size={20} />
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-sm">Typography</h3>
            </div>
            
            <div className="space-y-4">
              {fontOptions.map((font) => (
                <button
                  key={font.id}
                  onClick={() => setTheme(prev => ({ ...prev, fontFamily: font.id }))}
                  className={`w-full flex items-center justify-between p-5 rounded-2xl border-2 transition-all text-left ${theme.fontFamily === font.id ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-900/20' : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 bg-slate-50/30 dark:bg-slate-800/30'}`}
                >
                  <div>
                    <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-1">{font.name}</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{font.description}</p>
                  </div>
                  {theme.fontFamily === font.id && <Check className="text-blue-600" size={24} />}
                </button>
              ))}
            </div>
          </section>

          {/* Colors Section */}
          <section className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm transition-colors duration-300">
            <div className="flex items-center gap-2 mb-6">
              <Palette className="text-blue-500" size={20} />
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-sm">Primary Accents</h3>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {colorOptions.map((color) => (
                <button
                  key={color.value}
                  onClick={() => setTheme(prev => ({ ...prev, primaryColor: color.value }))}
                  className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all ${theme.primaryColor === color.value ? 'border-slate-800 dark:border-slate-400 bg-slate-50 dark:bg-slate-800' : 'border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700'}`}
                >
                  <div className="w-8 h-8 rounded-full shadow-inner" style={{ backgroundColor: color.value }} />
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{color.name}</span>
                </button>
              ))}
            </div>
          </section>

          {/* Appearance Section */}
          <section className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm transition-colors duration-300">
            <div className="flex items-center gap-2 mb-6">
              {theme.isDarkMode ? <Moon size={20} className="text-blue-500" /> : <Sun size={20} className="text-blue-500" />}
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-sm">Appearance</h3>
            </div>
            
            <div className="flex items-center justify-between p-6 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 transition-colors duration-300">
              <div>
                <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-1">Dark Mode</h4>
                <p className="text-sm text-slate-500 dark:text-slate-400">Enable a darker interface to reduce eye strain (Preview Only).</p>
              </div>
              <button 
                onClick={() => setTheme(prev => ({ ...prev, isDarkMode: !prev.isDarkMode }))}
                className={`w-14 h-8 rounded-full transition-colors relative ${theme.isDarkMode ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}
              >
                <div className={`absolute top-1 w-6 h-6 bg-white rounded-full transition-all ${theme.isDarkMode ? 'right-1' : 'left-1'}`} />
              </button>
            </div>
          </section>
        </div>

        <footer className="mt-12 text-center text-slate-400 dark:text-slate-600 text-sm">
          Settings are saved automatically to your local browser storage.
        </footer>
      </div>
    </div>
  );
};

export default ThemePage;
