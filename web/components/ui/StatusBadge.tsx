interface StatusBadgeProps {
  label: string;
  color?: string;
  className?: string;
}

export function StatusBadge({ label, color, className = '' }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}
      style={color ? { backgroundColor: color + '20', color } : undefined}
    >
      {label}
    </span>
  );
}

const FACILITY_TYPE_MAP: Record<string, { label: string; color: string }> = {
  BR: { label: '교량', color: '#2563EB' },
  TN: { label: '터널', color: '#7C3AED' },
  DM: { label: '댐', color: '#0891B2' },
  RD: { label: '도로', color: '#059669' },
};

const INSPECTION_STATUS_MAP: Record<string, { label: string; color: string }> = {
  IN_PROGRESS: { label: '점검중', color: '#F59E0B' },
  COMPLETED: { label: '완료', color: '#10B981' },
  DRAFT: { label: '임시저장', color: '#6B7280' },
};

export function FacilityTypeBadge({ type }: { type: string }) {
  const info = FACILITY_TYPE_MAP[type] ?? { label: type, color: '#6B7280' };
  return <StatusBadge label={info.label} color={info.color} />;
}

export function InspectionStatusBadge({ status }: { status: string }) {
  const info = INSPECTION_STATUS_MAP[status] ?? { label: status, color: '#6B7280' };
  return <StatusBadge label={info.label} color={info.color} />;
}

const DAMAGE_LAYER_MAP: Record<string, { label: string; color: string }> = {
  damage_new: { label: '신규손상', color: '#EF4444' },
  damage_exist: { label: '기존손상', color: '#F59E0B' },
  damage_expanded: { label: '확대손상', color: '#F97316' },
  repaired: { label: '보수완료', color: '#10B981' },
  note: { label: '메모', color: '#6B7280' },
};

export function DamageLayerBadge({ layer }: { layer: string }) {
  const info = DAMAGE_LAYER_MAP[layer] ?? { label: layer, color: '#6B7280' };
  return <StatusBadge label={info.label} color={info.color} />;
}
