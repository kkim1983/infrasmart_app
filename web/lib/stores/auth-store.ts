'use client';

import { create } from 'zustand';
import { login as apiLogin, setToken, type Inspector } from '@/lib/api/client';

interface AuthState {
  isLoggedIn: boolean;
  isAdmin: boolean;
  isInitialized: boolean; // restoreSession 완료 여부 — 초기값 false에서 리다이렉트 오작동 방지
  inspector: Inspector | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (licenseNo: string, password: string) => Promise<'inspector' | 'admin' | false>;
  logout: () => void;
  restoreSession: () => void;
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  isLoggedIn: false,
  isAdmin: false,
  isInitialized: false,
  inspector: null,
  token: null,
  isLoading: false,
  error: null,

  login: async (licenseNo, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiLogin(licenseNo, password);
      const { access_token, inspector } = data;
      setToken(access_token);
      if (typeof window !== 'undefined') {
        localStorage.setItem('infrasmart_token', access_token);
        localStorage.setItem('infrasmart_inspector', JSON.stringify(inspector));
      }
      set({ isLoggedIn: true, isAdmin: inspector.is_admin, inspector, token: access_token, isLoading: false });
      return inspector.is_admin ? 'admin' : 'inspector';
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '로그인에 실패했습니다.';
      set({ isLoading: false, error: msg });
      return false;
    }
  },

  logout: () => {
    setToken(null);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('infrasmart_token');
      localStorage.removeItem('infrasmart_inspector');
    }
    set({ isLoggedIn: false, isAdmin: false, inspector: null, token: null });
  },

  restoreSession: () => {
    if (typeof window === 'undefined') return;
    const t = localStorage.getItem('infrasmart_token');
    const raw = localStorage.getItem('infrasmart_inspector');
    if (t && raw) {
      try {
        const inspector = JSON.parse(raw) as Inspector;
        setToken(t);
        set({ isLoggedIn: true, isAdmin: inspector.is_admin ?? false, inspector, token: t, isInitialized: true });
      } catch {
        localStorage.removeItem('infrasmart_token');
        localStorage.removeItem('infrasmart_inspector');
        set({ isInitialized: true });
      }
    } else {
      set({ isInitialized: true });
    }
  },
}));
