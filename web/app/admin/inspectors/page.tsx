'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  adminListInspectors,
  adminCreateInspector,
  adminUpdateInspector,
  type Inspector,
} from '@/lib/api/client';
import { SkeletonLine } from '@/components/ui/SkeletonLoader';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/lib/stores/auth-store';

interface InspectorForm {
  name: string;
  license_no: string;
  password: string;
  license_type: string;
  phone: string;
  email: string;
}

const EMPTY_FORM: InspectorForm = {
  name: '', license_no: '', password: '', license_type: '', phone: '', email: '',
};

export default function AdminInspectorsPage() {
  const qc = useQueryClient();
  const { inspector: me } = useAuthStore();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<InspectorForm>(EMPTY_FORM);
  const [search, setSearch] = useState('');

  const { data: inspectors, isLoading } = useQuery({
    queryKey: ['admin-inspectors'],
    queryFn: adminListInspectors,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      adminCreateInspector({
        name: form.name.trim(),
        license_no: form.license_no.trim(),
        password: form.password,
        license_type: form.license_type || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-inspectors'] });
      qc.invalidateQueries({ queryKey: ['admin-stats'] });
      setShowModal(false);
      setForm(EMPTY_FORM);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(msg || '점검자 생성에 실패했습니다.');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminUpdateInspector(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-inspectors'] }),
  });

  const filtered = inspectors?.filter(
    (i) =>
      !search ||
      i.name.includes(search) ||
      i.license_no.includes(search) ||
      i.email?.includes(search),
  );

  const setField = (k: keyof InspectorForm, v: string) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">점검자 관리</h1>
          <p className="text-sm text-gray-500 mt-0.5">총 {inspectors?.length ?? 0}명</p>
        </div>
        <Button onClick={() => setShowModal(true)}>+ 점검자 추가</Button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="이름, 면허번호, 이메일 검색..."
          className="w-full max-w-sm border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
        />
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">이름</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">면허번호</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">자격종류</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">연락처</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">권한</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">상태</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td colSpan={7} className="px-5 py-3">
                      <SkeletonLine className="h-3 w-full" />
                    </td>
                  </tr>
                ))
              : filtered?.map((ins: Inspector) => (
                  <tr key={ins.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-[#DBEAFE] flex items-center justify-center shrink-0">
                          <span className="text-[#2563EB] text-xs font-bold">
                            {ins.name[0]}
                          </span>
                        </div>
                        <span className="font-medium text-gray-900">{ins.name}</span>
                        {ins.id === me?.id && (
                          <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">나</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500 text-xs whitespace-nowrap">{ins.license_no}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{ins.license_type ?? '-'}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{ins.phone ?? ins.email ?? '-'}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {ins.is_admin ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-600">
                          관리자
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-600">
                          점검자
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        ins.is_active
                          ? 'bg-green-50 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {ins.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {ins.id !== me?.id && (
                        <button
                          onClick={() => toggleMutation.mutate({ id: ins.id, is_active: !ins.is_active })}
                          className="text-xs text-gray-400 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
                        >
                          {ins.is_active ? '비활성화' : '활성화'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
        {!isLoading && filtered?.length === 0 && (
          <div className="py-12 text-center text-gray-400 text-sm">검색 결과가 없습니다</div>
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
            <h2 className="text-base font-semibold text-gray-900 mb-5">점검자 추가</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">이름 *</label>
                  <input
                    value={form.name}
                    onChange={(e) => setField('name', e.target.value)}
                    placeholder="홍길동"
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">면허번호 *</label>
                  <input
                    value={form.license_no}
                    onChange={(e) => setField('license_no', e.target.value)}
                    placeholder="INS-2024-001"
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">임시 비밀번호 *</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setField('password', e.target.value)}
                  placeholder="8자 이상"
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">자격종류</label>
                  <input
                    value={form.license_type}
                    onChange={(e) => setField('license_type', e.target.value)}
                    placeholder="토목기사"
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">연락처</label>
                  <input
                    value={form.phone}
                    onChange={(e) => setField('phone', e.target.value)}
                    placeholder="010-0000-0000"
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">이메일</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setField('email', e.target.value)}
                  placeholder="example@company.com"
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="secondary" className="flex-1" onClick={() => setShowModal(false)}>
                취소
              </Button>
              <Button
                className="flex-1"
                loading={createMutation.isPending}
                disabled={!form.name || !form.license_no || !form.password}
                onClick={() => createMutation.mutate()}
              >
                추가
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
