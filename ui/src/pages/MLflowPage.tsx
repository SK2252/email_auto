import React from 'react';

const MLflowPage: React.FC = () => {
  return (
    <div className="flex-1 overflow-hidden h-full flex flex-col bg-white dark:bg-slate-950">
      <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-black text-slate-800 dark:text-slate-200">MLflow LLMOps Dashboard</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Real-time performance and generation traces</p>
        </div>
        <a 
          href="http://localhost:5000/#/experiments/1/overview" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-xs font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
        >
          Open in New Tab ↗
        </a>
      </div>
      <iframe 
        src="http://localhost:5000/#/experiments/1/overview" 
        className="w-full flex-1 border-0"
        title="MLflow UI"
      />
    </div>
  );
};

export default MLflowPage;
