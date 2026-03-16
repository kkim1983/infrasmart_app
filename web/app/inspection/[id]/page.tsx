'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getDrawings,
  getPhotos,
  uploadDrawing,
  exportExcel,
  extractPdfDamageTable,
  type Drawing,
  type Photo,
} from '@/lib/api/client';
import { useAuthStore } from '@/lib/stores/auth-store';
import { InspectionStatusBadge } from '@/components/ui/StatusBadge';
import { SkeletonLine, SkeletonPhotoGrid } from '@/components/ui/SkeletonLoader';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/Toast';

const DRAWING_TYPE = { value: 'DAMAGE_MAP', label: '외관조사망도' };

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function InspectionPage() {
  const params = useParams<{ id: string }>();
  const inspectionId = params.id;
  const router = useRouter();
  const { isLoggedIn, isInitialized, restoreSession } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'drawings' | 'photos'>('drawings');
  const [exportLoading, setExportLoading] = useState(false);
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { restoreSession(); }, [restoreSession]);
  useEffect(() => { if (isInitialized && !isLoggedIn) router.replace('/login/'); }, [isInitialized, isLoggedIn, router]);

  const { data: drawings, isLoading: drawingsLoading } = useQuery({
    queryKey: ['drawings', inspectionId],
    queryFn: () => getDrawings(inspectionId),
    enabled: isLoggedIn,
  });

  const { data: photos, isLoading: photosLoading } = useQuery({
    queryKey: ['photos', inspectionId],
    queryFn: () => getPhotos(inspectionId),
    enabled: isLoggedIn,
  });

  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: ({ file }: { file: File }) =>
      uploadDrawing(inspectionId, DRAWING_TYPE.value, file, file.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drawings', inspectionId] });
      closeUploadModal();
      toast('도면이 업로드되었습니다');
    },
    onError: () => toast('도면 업로드에 실패했습니다', 'error'),
  });

  const closeUploadModal = () => {
    setShowUploadModal(false);
    setSelectedFile(null);
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      toast('PDF 파일만 업로드할 수 있습니다', 'error');
    }
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
    e.target.value = '';
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const blob = await exportExcel(inspectionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inspection_${inspectionId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast('엑셀 파일이 다운로드됩니다');
    } catch {
      toast('엑셀 내보내기에 실패했습니다', 'error');
    } finally {
      setExportLoading(false);
    }
  };

  const toProxyUrl = (url: string) => {
    try {
      const u = new URL(url);
      if (typeof window !== 'undefined' && u.origin !== window.location.origin) {
        return u.pathname + u.search;
      }
    } catch { /* relative URL */ }
    return url;
  };

  const extractBridgeName = (drawingName: string) => {
    const SUFFIXES = ['외관조사망도', '손상물량표', '단면도', '평면도', '종단면도', '일반도면', '위치도'];
    let name = drawingName.trim();
    for (const sfx of SUFFIXES) {
      if (name.endsWith(sfx)) { name = name.slice(0, -sfx.length).trim(); break; }
    }
    return name || drawingName;
  };

  const handleExtractPdf = async (drawing: Drawing) => {
    if (!drawing.file_url) return;
    setExtractingId(drawing.id);
    try {
      toast('손상물량표 추출 중...', 'info');
      const res = await fetch(toProxyUrl(drawing.file_url));
      const blob = await res.blob();
      const file = new File([blob], drawing.drawing_name || 'drawing.pdf', { type: 'application/pdf' });
      const bridgeName = extractBridgeName(drawing.drawing_name || '');
      const excelBlob = await extractPdfDamageTable(file, bridgeName);
      const url = URL.createObjectURL(excelBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `damage_table_${drawing.id}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast('손상물량표 추출 완료');
    } catch {
      toast('손상물량표 추출에 실패했습니다', 'error');
    } finally {
      setExtractingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <button onClick={() => router.back()} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-gray-900 truncate">점검 #{inspectionId.slice(0, 8)}</h1>
            <InspectionStatusBadge status="IN_PROGRESS" />
          </div>
        </div>
        <Button size="sm" variant="ghost" loading={exportLoading} onClick={handleExport}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Excel
        </Button>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 flex sticky top-[57px] z-10">
        {(['drawings', 'photos'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab
                ? 'border-[#2563EB] text-[#2563EB]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'drawings' ? `도면 (${drawings?.length ?? 0})` : `사진 (${photos?.length ?? 0})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 px-4 py-4">
        {activeTab === 'drawings' ? (
          <DrawingsTab
            drawings={drawings}
            isLoading={drawingsLoading}
            onUpload={() => setShowUploadModal(true)}
            onAnnotate={(d) => router.push(`/annotation/${d.id}/`)}
            onExtract={handleExtractPdf}
            extractingId={extractingId}
          />
        ) : (
          <PhotosTab
            photos={photos}
            isLoading={photosLoading}
            onCamera={() => router.push(`/camera/${inspectionId}/`)}
          />
        )}
      </div>

      {/* Upload Modal — Bottom Sheet */}
      {showUploadModal && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/50"
          onClick={(e) => { if (e.target === e.currentTarget) closeUploadModal(); }}
        >
          <div className="bg-white rounded-t-3xl w-full max-w-lg">
            {/* Handle bar */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-gray-300" />
            </div>

            <div className="px-6 py-4">
              {/* Title */}
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-bold text-gray-900">도면 업로드</h2>
                <button
                  onClick={closeUploadModal}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !selectedFile && fileRef.current?.click()}
                className={`
                  rounded-2xl border-2 border-dashed transition-all
                  ${selectedFile
                    ? 'border-[#2563EB] bg-[#EFF6FF] cursor-default'
                    : isDragging
                      ? 'border-[#2563EB] bg-[#EFF6FF]'
                      : 'border-gray-200 bg-gray-50 hover:border-[#2563EB] hover:bg-[#EFF6FF]/40 cursor-pointer'
                  }
                `}
              >
                {selectedFile ? (
                  <div className="px-5 py-4 flex items-center gap-4">
                    <div className="w-11 h-11 rounded-xl bg-[#2563EB] flex items-center justify-center shrink-0">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{selectedFile.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{formatBytes(selectedFile.size)}</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                      className="p-1.5 rounded-lg hover:bg-blue-100 text-[#2563EB] transition-colors shrink-0"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <div className="py-8 flex flex-col items-center gap-3 text-center">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors ${isDragging ? 'bg-[#2563EB]' : 'bg-gray-200'}`}>
                      <svg className={`w-7 h-7 transition-colors ${isDragging ? 'text-white' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-700">
                        {isDragging ? 'PDF를 여기에 놓으세요' : 'PDF 파일을 선택하세요'}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">클릭하거나 드래그 앤 드롭</p>
                    </div>
                  </div>
                )}
              </div>

              <input
                ref={fileRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={handleFileInputChange}
              />

              {/* Actions */}
              <div className="flex gap-3 mt-5 pb-2">
                <Button variant="secondary" className="flex-1" onClick={closeUploadModal}>
                  취소
                </Button>
                <Button
                  className="flex-1"
                  disabled={!selectedFile}
                  loading={uploadMutation.isPending}
                  onClick={() => selectedFile && uploadMutation.mutate({ file: selectedFile })}
                >
                  업로드
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DrawingsTab({
  drawings,
  isLoading,
  onUpload,
  onAnnotate,
  onExtract,
  extractingId,
}: {
  drawings?: Drawing[];
  isLoading: boolean;
  onUpload: () => void;
  onAnnotate: (d: Drawing) => void;
  onExtract: (d: Drawing) => void;
  extractingId: string | null;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-2xl border border-gray-200 p-4 space-y-2">
            <SkeletonLine className="h-4 w-2/3" />
            <SkeletonLine className="h-3 w-1/3" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {drawings?.length === 0 && (
        <div className="text-center py-14 text-gray-400">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
            <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-500">업로드된 도면이 없습니다</p>
          <p className="text-xs text-gray-400 mt-1">아래 버튼으로 PDF 도면을 추가하세요</p>
        </div>
      )}

      {drawings?.map((d) => (
        <DrawingCard
          key={d.id}
          drawing={d}
          extracting={extractingId === d.id}
          onAnnotate={() => onAnnotate(d)}
          onExtract={() => onExtract(d)}
        />
      ))}

      <button
        onClick={onUpload}
        className="w-full py-4 rounded-2xl border-2 border-dashed border-gray-200 text-sm text-gray-400 hover:border-[#2563EB] hover:text-[#2563EB] hover:bg-[#EFF6FF]/50 transition-all font-medium flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        도면 업로드
      </button>
    </div>
  );
}

function DrawingCard({
  drawing,
  extracting,
  onAnnotate,
  onExtract,
}: {
  drawing: Drawing;
  extracting: boolean;
  onAnnotate: () => void;
  onExtract: () => void;
}) {
  const isDamageMap = drawing.drawing_type === 'DAMAGE_MAP';

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="p-4 flex items-start gap-3">
        {/* PDF 아이콘 */}
        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center shrink-0 mt-0.5">
          <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-full mb-1 bg-amber-50 text-amber-600">
            {DRAWING_TYPE.label}
          </span>
          <p className="text-sm font-semibold text-gray-900 truncate">
            {drawing.drawing_name || `도면 ${drawing.id.slice(0, 8)}`}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {new Date(drawing.created_at).toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })}
          </p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="border-t border-gray-100 flex divide-x divide-gray-100">
        {isDamageMap && (
          <button
            onClick={onExtract}
            disabled={extracting}
            className="flex-1 py-3 text-xs font-semibold text-amber-600 hover:bg-amber-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
          >
            {extracting ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                추출 중
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                물량표 추출
              </>
            )}
          </button>
        )}
        <button
          onClick={onAnnotate}
          className="flex-1 py-3 text-xs font-semibold text-[#2563EB] hover:bg-blue-50 transition-colors flex items-center justify-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          어노테이션
        </button>
      </div>
    </div>
  );
}

function PhotosTab({
  photos,
  isLoading,
  onCamera,
}: {
  photos?: Photo[];
  isLoading: boolean;
  onCamera: () => void;
}) {
  if (isLoading) return <SkeletonPhotoGrid />;

  return (
    <div>
      {photos?.length === 0 && (
        <div className="text-center py-14 text-gray-400 mb-4">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
            <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-500">촬영된 사진이 없습니다</p>
          <p className="text-xs text-gray-400 mt-1">아래 버튼으로 사진을 촬영하세요</p>
        </div>
      )}
      <div className="grid grid-cols-3 gap-1.5 mb-4">
        {photos?.map((p) => (
          <div key={p.id} className="relative aspect-square bg-gray-100 rounded-xl overflow-hidden">
            {p.file_url ? (
              <img src={p.file_url} alt={p.photo_number ?? ''} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">사진</div>
            )}
            {p.damage_code && (
              <div className="absolute top-1 left-1 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded-md font-mono">
                {p.damage_code}
              </div>
            )}
            {p.photo_number && (
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent text-white text-[9px] px-1.5 py-1 truncate">
                {p.photo_number}
              </div>
            )}
          </div>
        ))}
      </div>
      <Button className="w-full py-4" onClick={onCamera}>
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        사진 촬영
      </Button>
    </div>
  );
}
