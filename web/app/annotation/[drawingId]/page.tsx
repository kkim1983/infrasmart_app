'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { getAnnotations, getDrawing, syncAnnotations, type Annotation, type Drawing } from '@/lib/api/client';
import { db } from '@/lib/db/local-db';
import { v4 as uuidv4 } from 'uuid';

// ─── Types ───────────────────────────────────────────────────────────────────

type LayerType = 'damage_new' | 'damage_exist' | 'damage_expanded' | 'repaired' | 'note';

interface Point { x: number; y: number }

interface Stroke {
  id: string;
  layer: LayerType;
  points: Point[];
  color: string;
  strokeWidth: number;
  isSynced: boolean;
}

const LAYER_CONFIG: Record<LayerType, { label: string; color: string }> = {
  damage_new: { label: '신규손상', color: '#EF4444' },
  damage_exist: { label: '기존손상', color: '#F59E0B' },
  damage_expanded: { label: '확대손상', color: '#F97316' },
  repaired: { label: '보수완료', color: '#10B981' },
  note: { label: '메모', color: '#6B7280' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * 백엔드 절대 URL(http://localhost:8000/files/...)을 Next.js 프록시 경로(/files/...)로 변환.
 * CORS/샌드박스 환경에서 fetch가 차단되는 것을 방지합니다.
 */
function toProxyUrl(url: string): string {
  if (typeof window === 'undefined') return url;
  // 절대 URL이고 현재 origin과 다른 경우 → 경로만 추출
  try {
    const u = new URL(url);
    if (u.origin !== window.location.origin) {
      return u.pathname + u.search;
    }
  } catch {
    // 이미 상대 경로인 경우 그대로 사용
  }
  return url;
}

// ─── PDF Renderer ─────────────────────────────────────────────────────────────

async function renderPdfPage(
  fileUrl: string,
  canvas: HTMLCanvasElement,
  pageNum: number,
  containerWidth: number,
): Promise<void> {
  // legacy 빌드: Map.getOrInsertComputed 등 최신 JS 기능 폴리필 포함
  const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf.mjs');
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

  const response = await fetch(fileUrl);
  if (!response.ok) throw new Error(`파일 로드 실패: ${response.status}`);
  const arrayBuffer = await response.arrayBuffer();

  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const page = await pdf.getPage(Math.min(pageNum, pdf.numPages));

  const scale = containerWidth / page.getViewport({ scale: 1 }).width;
  const viewport = page.getViewport({ scale });

  canvas.width = viewport.width;
  canvas.height = viewport.height;

  const ctx = canvas.getContext('2d')!;
  await page.render({ canvasContext: ctx, viewport }).promise;
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AnnotationPage() {
  const params = useParams<{ drawingId: string }>();
  const drawingId = params.drawingId;
  const router = useRouter();
  const { isLoggedIn, isInitialized, restoreSession } = useAuthStore();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [drawing, setDrawing] = useState<Drawing | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [currentLayer, setCurrentLayer] = useState<LayerType>('damage_new');
  const [strokeWidth, setStrokeWidth] = useState(3);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentStroke, setCurrentStroke] = useState<Point[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [pdfError, setPdfError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showTools, setShowTools] = useState(true);

  const drawingIdRef = useRef(drawingId);
  drawingIdRef.current = drawingId;

  useEffect(() => { restoreSession(); }, [restoreSession]);
  useEffect(() => { if (isInitialized && !isLoggedIn) router.replace('/login/'); }, [isInitialized, isLoggedIn, router]);

  // Load drawing info
  useEffect(() => {
    if (!isInitialized || !isLoggedIn) return;
    getDrawing(drawingId)
      .then(setDrawing)
      .catch(() => setPdfError('도면 정보를 불러오지 못했습니다.'));
  }, [drawingId, isLoggedIn]);

  // Render PDF when drawing is loaded
  useEffect(() => {
    if (!drawing?.file_url || !pdfCanvasRef.current || !containerRef.current) return;
    const containerWidth = containerRef.current.clientWidth || 800;

    setPdfLoaded(false);
    setPdfError('');

    (async () => {
      try {
        // Get total pages first
        const pdfjsLib = await import('pdfjs-dist');
        // CDN 대신 로컬 워커 사용 (/public/pdf.worker.min.mjs)
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
        const fileUrl = toProxyUrl(drawing.file_url!);
        const response = await fetch(fileUrl);
        const arrayBuffer = await response.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        setTotalPages(pdf.numPages);

        await renderPdfPage(fileUrl, pdfCanvasRef.current!, currentPage, containerWidth);
        setPdfLoaded(true);

        // Sync annotation canvas size to PDF canvas
        if (canvasRef.current && pdfCanvasRef.current) {
          canvasRef.current.width = pdfCanvasRef.current.width;
          canvasRef.current.height = pdfCanvasRef.current.height;
        }
      } catch (e) {
        setPdfError('PDF 로드에 실패했습니다: ' + (e instanceof Error ? e.message : String(e)));
      }
    })();
  }, [drawing, currentPage]);

  // Load existing annotations
  useEffect(() => {
    if (!isInitialized || !isLoggedIn) return;
    getAnnotations(drawingId).then((annotations: Annotation[]) => {
      const loaded: Stroke[] = annotations.map((a) => ({
        id: a.id,
        layer: a.layer as LayerType,
        points: a.coordinates,
        color: LAYER_CONFIG[a.layer as LayerType]?.color ?? '#6B7280',
        strokeWidth: a.style?.strokeWidth ?? 3,
        isSynced: true,
      }));
      setStrokes(loaded);
    }).catch(() => {});

    db.localAnnotations.where('drawingId').equals(drawingId).toArray().then((local) => {
      const localStrokes: Stroke[] = local.map((a) => ({
        id: a.id,
        layer: a.layer as LayerType,
        points: JSON.parse(a.coordinates),
        color: LAYER_CONFIG[a.layer as LayerType]?.color ?? '#6B7280',
        strokeWidth: a.style ? JSON.parse(a.style).strokeWidth ?? 3 : 3,
        isSynced: a.isSynced,
      }));
      setStrokes((prev) => {
        const serverIds = new Set(prev.filter((s) => s.isSynced).map((s) => s.id));
        const newLocal = localStrokes.filter((s) => !serverIds.has(s.id));
        return [...prev, ...newLocal];
      });
    });
  }, [drawingId, isLoggedIn]);

  // Redraw annotation canvas
  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    strokes.forEach((stroke) => {
      if (stroke.points.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = stroke.color + (stroke.isSynced ? '' : '99');
      ctx.lineWidth = stroke.strokeWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      stroke.points.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.stroke();
    });

    if (currentStroke.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = LAYER_CONFIG[currentLayer].color;
      ctx.lineWidth = strokeWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.moveTo(currentStroke[0].x, currentStroke[0].y);
      currentStroke.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.stroke();
    }
  }, [strokes, currentStroke, currentLayer, strokeWidth]);

  useEffect(() => { redrawCanvas(); }, [redrawCanvas]);

  const getPoint = (e: React.PointerEvent<HTMLCanvasElement>): Point => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    setIsDrawing(true);
    setCurrentStroke([getPoint(e)]);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    e.preventDefault();
    setCurrentStroke((prev) => [...prev, getPoint(e)]);
  };

  const handlePointerUp = async (e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!isDrawing || currentStroke.length < 2) {
      setIsDrawing(false);
      setCurrentStroke([]);
      return;
    }

    const stroke: Stroke = {
      id: uuidv4(),
      layer: currentLayer,
      points: currentStroke,
      color: LAYER_CONFIG[currentLayer].color,
      strokeWidth,
      isSynced: false,
    };

    setStrokes((prev) => [...prev, stroke]);
    setIsDrawing(false);
    setCurrentStroke([]);

    await db.localAnnotations.add({
      id: stroke.id,
      drawingId,
      annType: 'pen',
      layer: currentLayer,
      coordinates: JSON.stringify(currentStroke),
      style: JSON.stringify({ color: stroke.color, strokeWidth }),
      isSynced: false,
      createdAt: new Date().toISOString(),
    });
  };

  const handleUndo = () => {
    setStrokes((prev) => {
      const last = [...prev].reverse().find((s) => !s.isSynced);
      if (!last) return prev;
      db.localAnnotations.delete(last.id);
      return prev.filter((s) => s.id !== last.id);
    });
  };

  const handleSync = async () => {
    const unsyncedStrokes = strokes.filter((s) => !s.isSynced);
    if (unsyncedStrokes.length === 0) return;

    setSyncing(true);
    try {
      const payload: Annotation[] = unsyncedStrokes.map((s) => ({
        id: s.id,
        drawing_id: drawingId,
        ann_type: 'pen',
        layer: s.layer,
        coordinates: s.points,
        style: { color: s.color, strokeWidth: s.strokeWidth },
      }));
      await syncAnnotations(payload);

      for (const s of unsyncedStrokes) {
        await db.localAnnotations.update(s.id, { isSynced: true });
      }
      setStrokes((prev) => prev.map((s) => ({ ...s, isSynced: true })));
    } catch {
      alert('동기화에 실패했습니다.');
    } finally {
      setSyncing(false);
    }
  };

  const unsyncedCount = strokes.filter((s) => !s.isSynced).length;

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 flex items-center gap-2 px-4 py-3">
        <button onClick={() => router.back()} className="p-1.5 text-gray-300 hover:text-white">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-sm font-medium text-white flex-1 truncate">
          {drawing?.drawing_name ?? '어노테이션'}
        </h1>

        {/* Page navigation */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1 text-gray-400 hover:text-white disabled:opacity-30"
            >‹</button>
            <span className="text-xs text-gray-400 font-mono min-w-[50px] text-center">
              {currentPage}/{totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1 text-gray-400 hover:text-white disabled:opacity-30"
            >›</button>
          </div>
        )}

        <button
          onClick={handleUndo}
          disabled={unsyncedCount === 0}
          className="p-2 text-gray-300 hover:text-white disabled:opacity-30"
          title="실행 취소"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
          </svg>
        </button>
        <button
          onClick={() => setShowTools((v) => !v)}
          className="p-2 text-gray-300 hover:text-white"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </button>
        <button
          onClick={handleSync}
          disabled={unsyncedCount === 0 || syncing}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
            ${unsyncedCount > 0 ? 'bg-[#2563EB] text-white hover:bg-[#1D4ED8]' : 'bg-gray-600 text-gray-400 cursor-not-allowed'}`}
        >
          {syncing ? (
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : '☁️'}
          {unsyncedCount > 0 ? `동기화 (${unsyncedCount})` : '동기화'}
        </button>
      </div>

      {/* Canvas Area */}
      <div
        ref={containerRef}
        className="flex-1 relative overflow-auto bg-gray-700"
        style={{ minHeight: 0 }}
      >
        {/* PDF Layer */}
        <div className="relative inline-block min-w-full">
          {!pdfLoaded && !pdfError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-gray-800 min-h-[400px]">
              <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm">PDF 로드 중...</p>
            </div>
          )}
          {pdfError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-gray-800 min-h-[400px]">
              <div className="text-3xl mb-2">⚠️</div>
              <p className="text-sm text-center px-4">{pdfError}</p>
            </div>
          )}
          {/* PDF canvas (background) */}
          <canvas
            ref={pdfCanvasRef}
            className="block"
            style={{ visibility: pdfLoaded ? 'visible' : 'hidden' }}
          />
          {/* Annotation canvas (overlay) */}
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 cursor-crosshair touch-none"
            style={{ zIndex: 10 }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          />
        </div>
      </div>

      {/* Tools Panel */}
      {showTools && (
        <div className="bg-gray-800 px-4 py-3 space-y-3">
          {/* Layer Selector */}
          <div>
            <p className="text-xs text-gray-400 mb-2">레이어</p>
            <div className="flex gap-2 flex-wrap">
              {(Object.entries(LAYER_CONFIG) as [LayerType, { label: string; color: string }][]).map(([key, cfg]) => (
                <button
                  key={key}
                  onClick={() => setCurrentLayer(key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                    currentLayer === key
                      ? 'border-white bg-white/10 text-white'
                      : 'border-gray-600 text-gray-400 hover:border-gray-400'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: cfg.color }} />
                  {cfg.label}
                </button>
              ))}
            </div>
          </div>

          {/* Stroke Width */}
          <div className="flex items-center gap-3">
            <p className="text-xs text-gray-400 w-12 shrink-0">굵기 {strokeWidth}px</p>
            <input
              type="range"
              min={1}
              max={12}
              value={strokeWidth}
              onChange={(e) => setStrokeWidth(Number(e.target.value))}
              className="flex-1 accent-[#2563EB]"
            />
          </div>
        </div>
      )}
    </div>
  );
}
