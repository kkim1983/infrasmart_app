'use client';

import { useQuery } from '@tanstack/react-query';
import { getAdminStats, type Inspection } from '@/lib/api/client';
import { useAuthStore } from '@/lib/stores/auth-store';
import { InspectionStatusBadge } from '@/components/ui/StatusBadge';
import { SkeletonLine } from '@/components/ui/SkeletonLoader';

export default function AdminDashboard() {
  const { isLoggedIn } = useAuthStore();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: getAdminStats,
    enabled: isLoggedIn,
    refetchInterval: 30_000,
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">대시보드</h1>
        <p className="text-sm text-gray-500 mt-0.5">시스템 현황 요약</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="등록 시설물"
          value={stats?.facility_count}
          icon="🏗️"
          color="blue"
          loading={isLoading}
        />
        <StatCard
          label="점검자"
          value={stats?.inspector_count}
          icon="👷"
          color="purple"
          loading={isLoading}
        />
        <StatCard
          label="진행 중 점검"
          value={stats?.inspection_in_progress}
          icon="🔍"
          color="amber"
          loading={isLoading}
        />
        <StatCard
          label="완료 점검"
          value={stats?.inspection_completed}
          icon="✅"
          color="green"
          loading={isLoading}
        />
      </div>

      {/* Recent Inspections */}
      <div className="bg-white rounded-2xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">최근 점검 이력</h2>
          <span className="text-xs text-gray-400">총 {stats?.inspection_total ?? 0}건</span>
        </div>

        {isLoading ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <SkeletonLine className="h-3 w-32" />
                <SkeletonLine className="h-3 w-20" />
                <SkeletonLine className="h-3 w-16" />
              </div>
            ))}
          </div>
        ) : stats?.recent_inspections?.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">점검 이력이 없습니다</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {stats?.recent_inspections?.map((ins: Inspection) => (
              <div key={ins.id} className="px-5 py-3 flex items-center gap-4 hover:bg-gray-50">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    점검 #{ins.id.slice(0, 8).toUpperCase()}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {ins.started_at ? new Date(ins.started_at).toLocaleDateString('ko-KR', {
                      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    }) : '-'}
                  </p>
                </div>
                <div className="shrink-0">
                  <InspectionStatusBadge status={ins.status} />
                </div>
                <span className="text-xs font-mono text-gray-400 shrink-0">
                  {ins.inspection_type ?? 'ROUTINE'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
  loading,
}: {
  label: string;
  value?: number;
  icon: string;
  color: 'blue' | 'purple' | 'amber' | 'green';
  loading: boolean;
}) {
  const BG = { blue: 'bg-blue-50', purple: 'bg-purple-50', amber: 'bg-amber-50', green: 'bg-green-50' };
  const TEXT = { blue: 'text-blue-600', purple: 'text-purple-600', amber: 'text-amber-600', green: 'text-green-600' };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5">
      <div className={`w-10 h-10 rounded-xl ${BG[color]} flex items-center justify-center mb-3`}>
        <span className="text-xl">{icon}</span>
      </div>
      {loading ? (
        <SkeletonLine className="h-7 w-16 mb-1" />
      ) : (
        <p className={`text-3xl font-bold ${TEXT[color]}`}>{value ?? 0}</p>
      )}
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}
