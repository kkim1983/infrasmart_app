'use client';

import { Button } from './Button';

interface GeofenceDialogProps {
  distanceM: number;
  radiusM: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function GeofenceDialog({
  distanceM,
  radiusM,
  onConfirm,
  onCancel,
}: GeofenceDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
            <span className="text-xl">⚠️</span>
          </div>
          <h2 className="text-base font-semibold text-gray-900">지오펜스 경고</h2>
        </div>
        <p className="text-sm text-gray-600 mb-2">
          현재 위치가 시설물 점검 구역 밖에 있습니다.
        </p>
        <div className="bg-gray-50 rounded-lg p-3 mb-4 space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">현재 거리</span>
            <span className="font-medium text-gray-900">{Math.round(distanceM)}m</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">허용 반경</span>
            <span className="font-medium text-gray-900">{radiusM}m</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-5">
          그래도 점검을 시작하시겠습니까?
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={onCancel}>
            취소
          </Button>
          <Button variant="primary" className="flex-1" onClick={onConfirm}>
            계속 진행
          </Button>
        </div>
      </div>
    </div>
  );
}
