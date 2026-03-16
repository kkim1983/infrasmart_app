'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';

export default function Home() {
  const router = useRouter();
  const { restoreSession, isLoggedIn } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (isLoggedIn) {
      router.replace('/facilities/');
    } else {
      router.replace('/login/');
    }
  }, [isLoggedIn, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
