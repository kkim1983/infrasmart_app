import Dexie, { type EntityTable } from 'dexie';

export interface LocalAnnotation {
  id: string;
  drawingId: string;
  annType: 'pen' | 'text' | 'circle' | 'rectangle' | 'arrow' | 'eraser';
  layer: 'damage_new' | 'damage_exist' | 'damage_expanded' | 'repaired' | 'note';
  coordinates: string; // JSON [{x, y}]
  content?: string;
  style?: string; // JSON {color, strokeWidth}
  damageRecordId?: string;
  localId?: string;
  isSynced: boolean;
  createdAt: string;
}

export interface LocalPhoto {
  id: string;
  inspectionId: string;
  localFilePath: string;
  photoNumber?: string;
  damageCode?: string;
  damageDescription?: string;
  gpsJson?: string; // JSON {lat, lng, accuracy}
  drawingRef?: string;
  isSynced: boolean;
  takenAt?: string;
  createdAt: string;
}

export interface LocalDamageRecord {
  id: string;
  inspectionId: string;
  damageCode: string;
  damageName?: string;
  locationJson?: string;
  dimensionsJson?: string;
  severityGrade?: string;
  isNew: boolean;
  isExpanded: boolean;
  isRepaired: boolean;
  notes?: string;
  drawingRef?: string;
  isSynced: boolean;
  createdAt: string;
}

export interface SyncQueueItem {
  id?: number;
  operation: 'CREATE' | 'UPDATE' | 'DELETE';
  entityType: 'annotation' | 'photo' | 'damage';
  entityId: string;
  payload: string; // JSON
  status: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
  retryCount: number;
  createdAt: string;
}

class InfraSmartDB extends Dexie {
  localAnnotations!: EntityTable<LocalAnnotation, 'id'>;
  localPhotos!: EntityTable<LocalPhoto, 'id'>;
  localDamageRecords!: EntityTable<LocalDamageRecord, 'id'>;
  syncQueue!: EntityTable<SyncQueueItem, 'id'>;

  constructor() {
    super('InfraSmartDB');
    this.version(1).stores({
      localAnnotations: 'id, drawingId, isSynced, createdAt',
      localPhotos: 'id, inspectionId, isSynced, takenAt',
      localDamageRecords: 'id, inspectionId, damageCode, isSynced',
      syncQueue: '++id, entityType, entityId, status, createdAt',
    });
  }
}

export const db = new InfraSmartDB();

export async function addToSyncQueue(
  operation: SyncQueueItem['operation'],
  entityType: SyncQueueItem['entityType'],
  entityId: string,
  payload: object,
) {
  await db.syncQueue.add({
    operation,
    entityType,
    entityId,
    payload: JSON.stringify(payload),
    status: 'PENDING',
    retryCount: 0,
    createdAt: new Date().toISOString(),
  });
}

export async function getPendingSync() {
  return db.syncQueue.where('status').equals('PENDING').toArray();
}

export async function markSynced(queueId: number) {
  await db.syncQueue.update(queueId, { status: 'SYNCED' });
}

export async function markFailed(queueId: number) {
  const item = await db.syncQueue.get(queueId);
  if (item) {
    await db.syncQueue.update(queueId, {
      status: 'FAILED',
      retryCount: (item.retryCount || 0) + 1,
    });
  }
}
