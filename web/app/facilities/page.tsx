'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth-store';
import { getFacilities, startInspection, checkGeofence, type Facility } from '@/lib/api/client';
import { FacilityTypeBadge } from '@/components/ui/StatusBadge';
import { SkeletonGrid } from '@/components/ui/SkeletonLoader';
import { GeofenceDialog } from '@/components/ui/GeofenceDialog';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/Toast';

interface GeofenceState {
  distanceM: number;
  radiusM: number;
  facility: Facility;
}

export default function FacilitiesPage() {
  const router = useRouter();
  const { inspector, logout, restoreSession, isLoggedIn, isInitialized } = useAuthStore();
  const [starting, setStarting] = useState<string | null>(null);
  const [geofenceState, setGeofenceState] = useState<GeofenceState | null>(null);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (isInitialized && !isLoggedIn) router.replace('/login/');
  }, [isInitialized, isLoggedIn, router]);

  const { data: facilities, isLoading, error, refetch } = useQuery({
    queryKey: ['facilities'],
    queryFn: getFacilities,
    enabled: isLoggedIn,
  });

  const getCurrentGps = (): Promise<{ lat: number; lng: number; accuracy: number } | null> =>
    new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
        () => resolve(null),
        { timeout: 5000 },
      );
    });

  const doStartInspection = async (facility: Facility) => {
    setStarting(facility.id);
    try {
      const gps = await getCurrentGps();
      if (gps) {
        try {
          const fence = await checkGeofence(facility.id, gps.lat, gps.lng, gps.accuracy);
          if (!fence.inside) {
            setGeofenceState({ distanceM: fence.distance_m, radiusM: fence.radius_m, facility });
            setStarting(null);
            return;
          }
        } catch {
          // 지오펜스 API 없으면 통과
        }
      }
      const inspection = await startInspection({ facility_id: facility.id, gps: gps ?? undefined });
      router.push(`/inspection/${inspection.id}/`);
    } catch (e) {
      console.error(e);
      toast('점검 시작에 실패했습니다', 'error');
    } finally {
      setStarting(null);
    }
  };

  const handleGeofenceConfirm = async () => {
    if (!geofenceState) return;
    const { facility } = geofenceState;
    setGeofenceState(null);
    setStarting(facility.id);
    try {
      const inspection = await startInspection({ facility_id: facility.id });
      router.push(`/inspection/${inspection.id}/`);
    } finally {
      setStarting(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4 flex items-center justify-between sticky top-0 z-10">
        <div>
          <h1 className="text-base font-semibold text-gray-900">시설물 목록</h1>
          {inspector && (
            <p className="text-xs text-gray-500 mt-0.5">{inspector.name} · {inspector.license_no}</p>
          )}
        </div>
        <button onClick={logout} className="text-xs text-gray-400 px-3 py-1.5 rounded-lg hover:bg-gray-100">
          로그아웃
        </button>
      </div>

      <div className="px-4 py-4">
        {/* Stats */}
        {facilities && (
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-white rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-500">전체 시설물</p>
              <p className="text-2xl font-bold text-gray-900">{facilities.length}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-500">온라인</p>
              <div className="flex items-center gap-1.5 mt-1">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <p className="text-sm font-medium text-gray-900">연결됨</p>
              </div>
            </div>
          </div>
        )}

        {/* List */}
        {isLoading ? (
          <SkeletonGrid count={4} />
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-sm text-gray-500 mb-4">시설물을 불러오지 못했습니다</p>
            <Button variant="secondary" onClick={() => refetch()}>다시 시도</Button>
          </div>
        ) : facilities?.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-4xl mb-3">🏗️</p>
            <p className="text-sm">등록된 시설물이 없습니다</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {facilities?.map((facility) => (
              <FacilityCard
                key={facility.id}
                facility={facility}
                loading={starting === facility.id}
                onStart={() => doStartInspection(facility)}
              />
            ))}
          </div>
        )}
      </div>

      {geofenceState && (
        <GeofenceDialog
          distanceM={geofenceState.distanceM}
          radiusM={geofenceState.radiusM}
          onConfirm={handleGeofenceConfirm}
          onCancel={() => setGeofenceState(null)}
        />
      )}
    </div>
  );
}

function FacilityCard({
  facility,
  loading,
  onStart,
}: {
  facility: Facility;
  loading: boolean;
  onStart: () => void;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <FacilityTypeBadge type={facility.facility_type} />
            <span className="text-xs text-gray-400 font-mono">{facility.code}</span>
          </div>
          <h3 className="text-sm font-semibold text-gray-900 truncate">{facility.name}</h3>
          {facility.location_name && (
            <p className="text-xs text-gray-500 mt-0.5 truncate">📍 {facility.location_name}</p>
          )}
        </div>
        <Button
          size="sm"
          loading={loading}
          onClick={onStart}
          className="shrink-0"
        >
          점검 시작
        </Button>
      </div>
    </div>
  );
}
