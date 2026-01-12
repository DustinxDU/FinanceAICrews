"use client";

import React, { useState, useCallback, createContext, useContext } from "react";
import { AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";

const ToastContext = createContext<(message: string, type?: 'info' | 'success' | 'error' | 'warning') => void>(() => {});

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toasts, setToasts] = useState<{ id: number; message: string; type: string }[]>([]);

  const addToast = useCallback((message: string, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    // Warning toasts stay longer (5s) to give user time to read
    const duration = type === 'warning' ? 5000 : 3000;
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className={`pointer-events-auto px-4 py-3 rounded-lg shadow-lg border flex items-start gap-3 animate-in slide-in-from-right-full duration-300 max-w-md ${
            t.type === 'error' ? 'bg-red-900/90 border-red-500 text-white' :
            t.type === 'success' ? 'bg-green-900/90 border-green-500 text-white' :
            t.type === 'warning' ? 'bg-amber-900/90 border-amber-500 text-white' :
            'bg-zinc-900 border-zinc-700 text-zinc-100'
          }`}>
            {t.type === 'error' ? <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" /> :
             t.type === 'success' ? <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" /> :
             t.type === 'warning' ? <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" /> :
             <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />}
            <span className="text-sm font-medium whitespace-pre-line">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => useContext(ToastContext);
