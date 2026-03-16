export interface DamageCode {
  code: string;
  name: string;
  unit: string;
  fields?: string[];
  abbreviation?: string;
}

export interface DrawingType {
  code: string;
  name: string;
}

export interface SeverityGrade {
  grade: string;
  description: string;
  color: string;
}

export interface FacilityPlugin {
  facilityType: string;
  name: string;
  damageCodes: DamageCode[];
  drawingTypes: DrawingType[];
  severityGrades: SeverityGrade[];
  geofence?: { radius_m: number };
  locationSchema?: Record<string, unknown>;
}

const cache: Map<string, FacilityPlugin> = new Map();

export async function loadPlugin(facilityType: string): Promise<FacilityPlugin> {
  const key = facilityType.toLowerCase();
  if (cache.has(key)) return cache.get(key)!;

  const url = `/plugins/${key}_config.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Plugin not found: ${facilityType}`);
  const data = (await res.json()) as FacilityPlugin;
  cache.set(key, data);
  return data;
}

// Default BR plugin (fallback when fetch is not available)
export const DEFAULT_DAMAGE_CODES: DamageCode[] = [
  { code: 'C1', name: '균열', unit: 'm', abbreviation: 'CR' },
  { code: 'S1', name: '박리·박락', unit: '㎡', abbreviation: 'SP' },
  { code: 'E1', name: '백태·누수', unit: '㎡', abbreviation: 'EF' },
  { code: 'L1', name: '철근노출', unit: '㎡', abbreviation: 'RE' },
  { code: 'D1', name: '변색·오염', unit: '㎡', abbreviation: 'DC' },
  { code: 'W1', name: '세굴·파임', unit: '㎡', abbreviation: 'SC' },
];
