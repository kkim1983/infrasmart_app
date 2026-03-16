'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminListInspections, type Inspection } from '@/lib/api/client';
import { InspectionStatusBadge } from '@/components/ui/StatusBadge';
import { SkeletonLine } from '@/components/ui/SkeletonLoader';

const STATUS_FILTERS = [
  { value: '', label: '전체' },
  { value: 'IN_PROGRESS', label: '진행 중' },
  { value: 'COMPLETED', label: '완료' },
  { value: 'DRAFT', label: '임시저장' },
];

export default function AdminInspectionsPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const { data: inspections, isLoading } = useQuery({
    queryKey: ['admin-inspections', statusFilter, page],
    queryFn: () =>
      adminListInspections({
        status: statusFilter || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">점검 이력</h1>
        <p className="text-sm text-gray-500 mt-0.5">전체 점검 현황</p>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-4">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value); setPage(0); }}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? 'bg-[#2563EB] text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm min-w-[560px]">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">점검 ID</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">유형</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">상태</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">시작일시</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">종료일시</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td colSpan={5} className="px-5 py-3">
                      <SkeletonLine className="h-3 w-full" />
                    </td>
                  </tr>
                ))
              : inspections?.map((ins: Inspection) => (
                  <tr key={ins.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-gray-600">
                        #{ins.id.slice(0, 8).toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-xs text-gray-500">{ins.inspection_type ?? 'ROUTINE'}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <InspectionStatusBadge status={ins.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {ins.started_at
                        ? new Date(ins.started_at).toLocaleString('ko-KR', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                      {ins.ended_at
                        ? new Date(ins.ended_at).toLocaleString('ko-KR', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })
                        : '-'}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>

        {!isLoading && inspections?.length === 0 && (
          <div className="py-12 text-center text-gray-400 text-sm">
            {statusFilter ? `'${STATUS_FILTERS.find(f => f.value === statusFilter)?.label}' 점검이 없습니다` : '점검 이력이 없습니다'}
          </div>
        )}

        {/* Pagination */}
        {(inspections?.length === PAGE_SIZE || page > 0) && (
          <div className="px-5 py-3 border-t border-gray-200 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-30 hover:bg-gray-50"
            >
              이전
            </button>
            <span className="text-xs text-gray-400">{page + 1} 페이지</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={(inspections?.length ?? 0) < PAGE_SIZE}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-30 hover:bg-gray-50"
            >
              다음
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
