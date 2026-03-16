'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { Button } from '@/components/ui/Button';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoggedIn, isAdmin, isLoading, error, restoreSession } = useAuthStore();
  const [licenseNo, setLicenseNo] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (isLoggedIn) {
      router.replace(isAdmin ? '/admin/' : '/facilities/');
    }
  }, [isLoggedIn, isAdmin, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!licenseNo.trim() || !password.trim()) return;
    const result = await login(licenseNo.trim(), password);
    if (result === 'admin') router.replace('/admin/');
    else if (result === 'inspector') router.replace('/facilities/');
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col items-center justify-center px-5">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#2563EB] mb-4 shadow-lg">
            <span className="text-white text-2xl font-bold">IS</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">InfraSmart</h1>
          <p className="text-sm text-gray-500 mt-1">시설물 안전점검 플랫폼</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4 shadow-sm">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              면허 번호
            </label>
            <input
              type="text"
              value={licenseNo}
              onChange={(e) => setLicenseNo(e.target.value)}
              placeholder="면허 번호를 입력하세요"
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent transition"
              autoCapitalize="none"
              autoCorrect="off"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              비밀번호
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 pr-11 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent transition"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 p-1"
              >
                {showPw ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <Button
            type="submit"
            loading={isLoading}
            disabled={!licenseNo || !password}
            className="w-full mt-2 h-12"
          >
            로그인
          </Button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-6">
          InfraSmart v1.0 · 시설물 안전점검
        </p>
      </div>
    </div>
  );
}
