'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { uploadPhoto } from '@/lib/api/client';
import { DEFAULT_DAMAGE_CODES, type DamageCode } from '@/lib/plugins/facility-plugin';
import { Button } from '@/components/ui/Button';

type CaptureState = 'preview' | 'captured' | 'uploading';

export default function CameraPage() {
  const params = useParams<{ inspectionId: string }>();
  const inspectionId = params.inspectionId;
  const router = useRouter();
  const { isLoggedIn, isInitialized, restoreSession } = useAuthStore();

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [state, setState] = useState<CaptureState>('preview');
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [damageCodes] = useState<DamageCode[]>(DEFAULT_DAMAGE_CODES);
  const [selectedCode, setSelectedCode] = useState('');
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  const [gps, setGps] = useState<{ lat: number; lng: number; accuracy: number } | null>(null);
  const [cameraError, setCameraError] = useState('');

  useEffect(() => { restoreSession(); }, [restoreSession]);
  useEffect(() => { if (isInitialized && !isLoggedIn) router.replace('/login/'); }, [isInitialized, isLoggedIn, router]);

  useEffect(() => {
    startCamera();
    navigator.geolocation?.getCurrentPosition(
      (pos) => setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      () => {},
    );
    return () => stopCamera();
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      setCameraError('카메라 접근 권한이 필요합니다');
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth || 1920;
    canvas.height = video.videoHeight || 1080;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setCapturedBlob(blob);
        const url = URL.createObjectURL(blob);
        setCapturedUrl(url);
        setState('captured');
        stopCamera();
      },
      'image/jpeg',
      0.9,
    );
  };

  const handleRetake = () => {
    if (capturedUrl) URL.revokeObjectURL(capturedUrl);
    setCapturedBlob(null);
    setCapturedUrl(null);
    setState('preview');
    startCamera();
  };

  const handleUpload = async () => {
    if (!capturedBlob) return;
    setState('uploading');
    try {
      await uploadPhoto(inspectionId, capturedBlob, {
        damageCode: selectedCode || undefined,
        description: description || undefined,
        location: location || undefined,
        gps: gps ?? undefined,
        takenAt: new Date().toISOString(),
      });
      router.back();
    } catch {
      alert('사진 업로드에 실패했습니다.');
      setState('captured');
    }
  };

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-black/80">
        <button onClick={() => router.back()} className="p-1.5">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-sm font-medium text-white">손상 사진 촬영</h1>
        {gps && (
          <span className="ml-auto text-xs text-green-400">GPS ✓</span>
        )}
      </div>

      {/* Camera / Captured Image */}
      <div className="flex-1 relative bg-black flex items-center justify-center">
        {cameraError ? (
          <div className="text-center text-white px-6">
            <p className="text-4xl mb-3">📷</p>
            <p className="text-sm text-gray-300">{cameraError}</p>
          </div>
        ) : state === 'preview' ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          capturedUrl && (
            <img src={capturedUrl} alt="촬영된 사진" className="w-full h-full object-cover" />
          )
        )}
        <canvas ref={canvasRef} className="hidden" />
      </div>

      {/* Bottom Panel */}
      <div className="bg-white rounded-t-2xl px-4 pt-4 pb-6 space-y-3">
        {/* Damage Code */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">손상 코드</label>
          <select
            value={selectedCode}
            onChange={(e) => setSelectedCode(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
          >
            <option value="">선택 안함</option>
            {damageCodes.map((dc) => (
              <option key={dc.code} value={dc.code}>
                {dc.code} - {dc.name}
              </option>
            ))}
          </select>
        </div>

        {/* Location */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">위치</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="예: 교각 G3 하부"
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">설명</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="손상 상태 설명"
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
          />
        </div>

        {/* Action Buttons */}
        {state === 'preview' ? (
          <button
            onClick={capturePhoto}
            disabled={!!cameraError}
            className="w-full h-14 rounded-xl bg-[#2563EB] text-white font-semibold text-base flex items-center justify-center gap-2 hover:bg-[#1D4ED8] disabled:opacity-50"
          >
            📸 촬영
          </button>
        ) : (
          <div className="flex gap-3">
            <Button variant="secondary" className="flex-1 h-12" onClick={handleRetake}>
              다시 촬영
            </Button>
            <Button
              className="flex-1 h-12"
              loading={state === 'uploading'}
              onClick={handleUpload}
            >
              업로드
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
