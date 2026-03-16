'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  adminListFacilities,
  adminCreateFacility,
  adminUpdateFacility,
  type Facility,
} from '@/lib/api/client';
import { FacilityTypeBadge } from '@/components/ui/StatusBadge';
import { SkeletonCard } from '@/components/ui/SkeletonLoader';
import { Button } from '@/components/ui/Button';

const FACILITY_TYPES = ['BR', 'TN', 'DM', 'RD'];
const TYPE_LABELS: Record<string, string> = { BR: '교량', TN: '터널', DM: '댐', RD: '도로' };

interface FacilityForm {
  facility_type: string;
  code: string;
  name: string;
  location_name: string;
  geofence_type: string;
  center_lat: string;
  center_lng: string;
  radius_m: string;
}

const EMPTY_FORM: FacilityForm = {
  facility_type: 'BR', code: '', name: '', location_name: '',
  geofence_type: 'circular', center_lat: '', center_lng: '', radius_m: '500',
};

export default function AdminFacilitiesPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<FacilityForm>(EMPTY_FORM);
  const [search, setSearch] = useState('');

  const { data: facilities, isLoading } = useQuery({
    queryKey: ['admin-facilities'],
    queryFn: adminListFacilities,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      adminCreateFacility({
        facility_type: form.facility_type,
        code: form.code.trim(),
        name: form.name.trim(),
        location_name: form.location_name.trim() || undefined,
        geofence_type: form.geofence_type,
        geofence_data: form.geofence_type === 'circular' && form.center_lat
          ? {
              center_lat: parseFloat(form.center_lat),
              center_lng: parseFloat(form.center_lng),
              radius_m: parseInt(form.radius_m) || 500,
            }
          : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-facilities'] });
      qc.invalidateQueries({ queryKey: ['admin-stats'] });
      setShowModal(false);
      setForm(EMPTY_FORM);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(msg || '시설물 생성에 실패했습니다.');
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminUpdateFacility(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-facilities'] }),
  });

  const filtered = facilities?.filter((f) =>
    !search || f.name.includes(search) || f.code?.includes(search) || f.location_name?.includes(search),
  );

  const setField = (k: keyof FacilityForm, v: string) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">시설물 관리</h1>
          <p className="text-sm text-gray-500 mt-0.5">총 {facilities?.length ?? 0}개</p>
        </div>
        <Button onClick={() => setShowModal(true)}>+ 시설물 추가</Button>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="시설물명, 코드, 위치 검색..."
          className="w-full max-w-sm border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">시설물</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">코드</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">위치</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">상태</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">등록일</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="px-5 py-3" colSpan={6}>
                      <SkeletonCard />
                    </td>
                  </tr>
                ))
              : filtered?.map((f) => (
                  <tr key={f.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <FacilityTypeBadge type={f.facility_type} />
                        <span className="font-medium text-gray-900">{f.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500 text-xs whitespace-nowrap">{f.code}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{f.location_name ?? '-'}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        f.is_active
                          ? 'bg-green-50 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {f.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {new Date(f.created_at).toLocaleDateString('ko-KR')}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <button
                        onClick={() => toggleActiveMutation.mutate({
                          id: f.id,
                          is_active: !f.is_active,
                        })}
                        className="text-xs text-gray-400 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
                      >
                        {f.is_active ? '비활성화' : '활성화'}
                      </button>
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
            <h2 className="text-base font-semibold text-gray-900 mb-5">시설물 추가</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">시설물 유형</label>
                  <select
                    value={form.facility_type}
                    onChange={(e) => setField('facility_type', e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  >
                    {FACILITY_TYPES.map((t) => (
                      <option key={t} value={t}>{t} - {TYPE_LABELS[t]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">시설물 코드 *</label>
                  <input
                    value={form.code}
                    onChange={(e) => setField('code', e.target.value)}
                    placeholder="BR-001"
                    className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">시설물명 *</label>
                <input
                  value={form.name}
                  onChange={(e) => setField('name', e.target.value)}
                  placeholder="오원4교"
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">위치</label>
                <input
                  value={form.location_name}
                  onChange={(e) => setField('location_name', e.target.value)}
                  placeholder="강원도 강릉시"
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">지오펜스 (선택)</label>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    value={form.center_lat}
                    onChange={(e) => setField('center_lat', e.target.value)}
                    placeholder="위도 37.12"
                    className="border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                  <input
                    value={form.center_lng}
                    onChange={(e) => setField('center_lng', e.target.value)}
                    placeholder="경도 128.45"
                    className="border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                  <input
                    value={form.radius_m}
                    onChange={(e) => setField('radius_m', e.target.value)}
                    placeholder="반경(m) 500"
                    className="border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="secondary" className="flex-1" onClick={() => setShowModal(false)}>
                취소
              </Button>
              <Button
                className="flex-1"
                loading={createMutation.isPending}
                disabled={!form.code || !form.name}
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
