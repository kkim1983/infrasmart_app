import axios, { type AxiosInstance, type AxiosResponse } from 'axios';

// 클라이언트 전용 모듈 — 'use client' 컴포넌트에서만 import
// BASE_URL: 브라우저 dev → /api/v1 (Next.js rewrite가 localhost:8000으로 프록시)
//           Capacitor 빌드  → NEXT_PUBLIC_API_URL에 프로덕션 서버 URL 지정
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

// 토큰은 브라우저 탭 단위로 격리 (SSR에서는 이 모듈이 실행되지 않음)
let _token: string | null = null;

export function setToken(t: string | null) {
  _token = t;
}

export function getToken(): string | null {
  return _token;
}

const api: AxiosInstance = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      _token = null;
      localStorage.removeItem('infrasmart_token');
      localStorage.removeItem('infrasmart_inspector');
      window.location.href = '/login/';
    }
    return Promise.reject(error);
  },
);

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Inspector {
  id: string;
  name: string;
  license_no: string;
  license_type?: string;
  phone?: string;
  email?: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Facility {
  id: string;
  name: string;
  code: string;
  facility_type: string;
  location_name?: string;
  geofence_type?: string;
  geofence_data?: object | null;
  is_active: boolean;
  created_at: string;
}

export interface Inspection {
  id: string;
  facility_id: string;
  inspector_id: string;
  inspection_type?: string;
  status: string;
  started_at?: string;
  ended_at?: string;
  notes?: string;
  created_at?: string;
}

export interface Drawing {
  id: string;
  inspection_id: string;
  drawing_type: string;
  drawing_name?: string;
  file_url?: string;
  created_at: string;
}

export interface Photo {
  id: string;
  inspection_id: string;
  photo_number?: string;
  damage_code?: string;
  damage_description?: string;
  file_url?: string;
  taken_at?: string;
  gps?: { lat: number; lng: number; accuracy: number };
}

export interface Annotation {
  id: string;
  drawing_id: string;
  ann_type: string;
  layer: string;
  coordinates: Array<{ x: number; y: number }>;
  content?: string;
  style?: { color: string; strokeWidth: number };
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function login(licenseNo: string, password: string) {
  const r: AxiosResponse<{ access_token: string; inspector: Inspector }> =
    await api.post('/auth/login', {
      license_no: licenseNo,
      password,
      device_info: { platform: 'web' },
    });
  return r.data;
}

export async function register(data: object) {
  const r = await api.post('/auth/register', data);
  return r.data;
}

export async function checkGeofence(
  facilityId: string,
  lat: number,
  lng: number,
  accuracy: number,
) {
  const r = await api.post('/auth/geofence/check', {
    facility_id: facilityId,
    lat,
    lng,
    accuracy,
  });
  return r.data as { inside: boolean; distance_m: number; radius_m: number };
}

// ─── Facilities ───────────────────────────────────────────────────────────────

export async function getFacilities(): Promise<Facility[]> {
  const r = await api.get('/facilities');
  return r.data;
}

export async function getFacilityPluginConfig(typeCode: string) {
  const r = await api.get(`/facilities/types/${typeCode}/config`);
  return r.data;
}

// ─── Inspections ──────────────────────────────────────────────────────────────

export async function startInspection(data: {
  facility_id: string;
  gps?: { lat: number; lng: number; accuracy: number };
}): Promise<Inspection> {
  const r = await api.post('/inspections', data);
  return r.data;
}

export async function getInspections(): Promise<Inspection[]> {
  const r = await api.get('/inspections');
  return r.data;
}

export async function appendGpsTrack(
  inspectionId: string,
  point: { lat: number; lng: number; accuracy: number },
) {
  const r = await api.post(`/inspections/${inspectionId}/gps`, point);
  return r.data;
}

// ─── Drawings ─────────────────────────────────────────────────────────────────

export async function uploadDrawing(
  inspectionId: string,
  drawingType: string,
  file: File,
  drawingName?: string,
) {
  const form = new FormData();
  form.append('inspection_id', inspectionId);
  form.append('drawing_type', drawingType);
  form.append('file', file);
  if (drawingName) form.append('drawing_name', drawingName);
  const r = await api.post('/drawings', form);
  return r.data as Drawing;
}

export async function getDrawings(inspectionId: string): Promise<Drawing[]> {
  const r = await api.get(`/drawings/inspection/${inspectionId}`);
  return r.data;
}

export async function getDrawing(drawingId: string): Promise<Drawing> {
  const r = await api.get(`/drawings/${drawingId}`);
  return r.data;
}

// ─── Annotations ──────────────────────────────────────────────────────────────

export async function syncAnnotations(annotations: Annotation[]) {
  const r = await api.post('/annotations/sync', annotations);
  return r.data;
}

export async function getAnnotations(drawingId: string): Promise<Annotation[]> {
  const r = await api.get(`/annotations/drawing/${drawingId}`);
  return r.data;
}

// ─── Photos ───────────────────────────────────────────────────────────────────

export async function uploadPhoto(
  inspectionId: string,
  file: File | Blob,
  opts?: {
    damageCode?: string;
    description?: string;
    gps?: { lat: number; lng: number; accuracy: number };
    location?: string;
    takenAt?: string;
  },
) {
  const form = new FormData();
  form.append('inspection_id', inspectionId);
  form.append('file', file, 'photo.jpg');
  if (opts?.damageCode) form.append('damage_code', opts.damageCode);
  if (opts?.description) form.append('description', opts.description);
  if (opts?.location) form.append('location', opts.location);
  if (opts?.takenAt) form.append('taken_at', opts.takenAt);
  if (opts?.gps) form.append('gps', JSON.stringify(opts.gps));
  const r = await api.post('/photos', form);
  return r.data as Photo;
}

export async function getPhotos(inspectionId: string): Promise<Photo[]> {
  const r = await api.get(`/photos/inspection/${inspectionId}`);
  return r.data;
}

// ─── Export ───────────────────────────────────────────────────────────────────

export async function exportExcel(inspectionId: string): Promise<Blob> {
  const r = await api.get(`/export/${inspectionId}/excel`, {
    responseType: 'blob',
  });
  return r.data;
}

export async function extractPdfDamageTable(
  file: File,
  bridgeName: string,
): Promise<Blob> {
  const form = new FormData();
  form.append('file', file);
  form.append('bridge_name', bridgeName);
  const r = await api.post('/ocr/extract-pdf', form, { responseType: 'blob' });
  return r.data;
}

// ─── Voice (Phase 2) ──────────────────────────────────────────────────────────

export async function transcribeVoice(audioBlob: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append('file', audioBlob, 'voice.m4a');
  const r = await api.post('/voice/transcribe', form);
  return r.data;
}

// ─── CAD (Phase 2) ────────────────────────────────────────────────────────────

export async function calibrateDrawing(
  drawingId: string,
  points: object[],
  scaleText?: string,
) {
  const r = await api.post(`/drawings/${drawingId}/calibrate`, {
    points,
    scale_text: scaleText,
  });
  return r.data;
}

export async function exportDxf(drawingId: string): Promise<Blob> {
  const r = await api.get(`/drawings/${drawingId}/export/dxf`, {
    responseType: 'blob',
  });
  return r.data;
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export interface AdminStats {
  facility_count: number;
  inspector_count: number;
  inspection_total: number;
  inspection_in_progress: number;
  inspection_completed: number;
  recent_inspections: Inspection[];
}

export async function getAdminStats(): Promise<AdminStats> {
  const r = await api.get('/admin/stats');
  return r.data;
}

export async function adminListInspectors(): Promise<Inspector[]> {
  const r = await api.get('/admin/inspectors');
  return r.data;
}

export async function adminCreateInspector(data: {
  name: string;
  license_no: string;
  password: string;
  license_type?: string;
  phone?: string;
  email?: string;
  admin_key?: string;
}): Promise<Inspector> {
  const r = await api.post('/admin/inspectors', data);
  return r.data;
}

export async function adminUpdateInspector(
  id: string,
  data: Partial<{ name: string; phone: string; email: string; is_active: boolean; is_admin: boolean }>,
): Promise<Inspector> {
  const r = await api.patch(`/admin/inspectors/${id}`, data);
  return r.data;
}

export async function adminListFacilities(): Promise<Facility[]> {
  const r = await api.get('/admin/facilities');
  return r.data;
}

export async function adminCreateFacility(data: {
  facility_type: string;
  code: string;
  name: string;
  location_name?: string;
  geofence_type?: string;
  geofence_data?: object;
}): Promise<Facility> {
  const r = await api.post('/admin/facilities', data);
  return r.data;
}

export async function adminUpdateFacility(
  id: string,
  data: Partial<{ name: string; location_name: string; is_active: boolean }>,
): Promise<Facility> {
  const r = await api.patch(`/admin/facilities/${id}`, data);
  return r.data;
}

export async function adminListInspections(opts?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<Inspection[]> {
  const r = await api.get('/admin/inspections', { params: opts });
  return r.data;
}
