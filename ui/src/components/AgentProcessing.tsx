import React, { useState, useEffect } from 'react';
import { Sparkles, Activity, Server, Database, CheckCircle2, Loader2 } from 'lucide-react';

export const AgentProcessing: React.FC = () => {
    const [step, setStep] = useState(0);
    const [isLongRunning, setIsLongRunning] = useState(false);

    const steps = [
        { text: "Analyzing request...", icon: Sparkles, color: "text-blue-500" },
        { text: "Routing to agent...", icon: Activity, color: "text-purple-500" },
        { text: "Executing task...", icon: Server, color: "text-amber-500" },
        { text: "Processing results...", icon: Database, color: "text-emerald-500" },
        { text: "Finalizing...", icon: CheckCircle2, color: "text-blue-600" }
    ];

    useEffect(() => {
        // Switch to "Agent Execution" mode if response takes longer than 1.5s
        const modeTimer = setTimeout(() => {
            setIsLongRunning(true);
        }, 1500);

        const interval = setInterval(() => {
            setStep((prev) => (prev + 1) % steps.length);
        }, 2500); // Change step every 2.5 seconds

        return () => {
            clearTimeout(modeTimer);
            clearInterval(interval);
        };
    }, []);

    const CurrentIcon = steps[step].icon;

    if (!isLongRunning) {
        return (
            <div className="flex items-center justify-center p-3">
                <Loader2 className="animate-spin text-blue-600" size={24} />
            </div>
        );
    }

    return (
        <div className="flex flex-col items-start gap-3 p-4 bg-slate-50/50 rounded-2xl border border-slate-100 max-w-sm animate-in fade-in zoom-in-95 duration-500">
            <div className="flex items-center gap-3">
                <div className="relative">
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center bg-white shadow-sm border border-slate-100 ${steps[step].color}`}>
                        <CurrentIcon size={18} className="animate-pulse" />
                    </div>
                    {/* Ping animation for active state */}
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${steps[step].color.replace('text-', 'bg-')}`}></span>
                        <span className={`relative inline-flex rounded-full h-3 w-3 ${steps[step].color.replace('text-', 'bg-')}`}></span>
                    </span>
                </div>

                <div className="flex flex-col">
                    <span className="text-sm font-semibold text-slate-700 animate-in fade-in slide-in-from-bottom-1 duration-500 key={step}">
                        {steps[step].text}
                    </span>
                    <span className="text-xs text-slate-400">
                        YAKKAY Agent is working...
                    </span>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-200 rounded-full h-1 mt-1 overflow-hidden">
                <div
                    className="bg-blue-600 h-1 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${((step + 1) / steps.length) * 100}%` }}
                />
            </div>
        </div>
    );
};
