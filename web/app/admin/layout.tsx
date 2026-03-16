'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/stores/auth-store';

const NAV_ITEMS = [
  { href: '/admin/', label: '대시보드', icon: '📊' },
  { href: '/admin/facilities/', label: '시설물 관리', icon: '🏗️' },
  { href: '/admin/inspectors/', label: '점검자 관리', icon: '👷' },
  { href: '/admin/inspections/', label: '점검 이력', icon: '📋' },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoggedIn, isAdmin, inspector, logout, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (!isLoggedIn) {
      router.replace('/login/');
    } else if (!isAdmin) {
      router.replace('/facilities/');
    }
  }, [isLoggedIn, isAdmin, router]);

  const handleLogout = () => {
    logout();
    router.replace('/login/');
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col fixed inset-y-0 left-0 z-20">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2563EB] flex items-center justify-center">
              <span className="text-white text-xs font-bold">IS</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">InfraSmart</p>
              <p className="text-[10px] text-[#EF4444] font-medium">관리자</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname === item.href.slice(0, -1);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#EFF6FF] text-[#2563EB]'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="px-3 py-4 border-t border-gray-200">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-full bg-[#DBEAFE] flex items-center justify-center">
              <span className="text-[#2563EB] text-xs font-bold">
                {inspector?.name?.[0] ?? 'A'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">{inspector?.name}</p>
              <p className="text-[10px] text-gray-400 truncate">{inspector?.license_no}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-xs text-gray-500 py-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-56">
        {children}
      </main>
    </div>
  );
}
