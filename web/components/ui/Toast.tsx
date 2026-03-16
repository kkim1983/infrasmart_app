'use client';

import { useEffect, useState } from 'react';

type ToastType = 'success' | 'error' | 'info';
type ToastItem = { id: string; message: string; type: ToastType };

const TOAST_EVENT = 'infrasmart:toast';

export function toast(message: string, type: ToastType = 'success') {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: { message, type } }));
}

export function Toaster() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    const handler = (e: Event) => {
      const { message, type } = (e as CustomEvent<{ message: string; type: ToastType }>).detail;
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3200);
    };
    window.addEventListener(TOAST_EVENT, handler);
    return () => window.removeEventListener(TOAST_EVENT, handler);
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-6 left-0 right-0 z-[200] flex flex-col items-center gap-2 px-4 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`
            max-w-sm w-full px-4 py-3 rounded-2xl shadow-xl text-sm font-medium
            flex items-center gap-2.5 pointer-events-auto
            animate-[slideUp_0.2s_ease-out]
            ${t.type === 'success' ? 'bg-gray-900 text-white' : ''}
            ${t.type === 'error' ? 'bg-red-500 text-white' : ''}
            ${t.type === 'info' ? 'bg-[#2563EB] text-white' : ''}
          `}
        >
          {t.type === 'success' && (
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {t.type === 'error' && (
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          {t.type === 'info' && (
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}
