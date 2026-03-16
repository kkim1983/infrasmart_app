export function SkeletonLine({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <SkeletonLine className="h-4 w-3/4" />
      <SkeletonLine className="h-3 w-1/2" />
      <SkeletonLine className="h-3 w-2/3" />
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonPhotoGrid({ count = 9 }: { count?: number }) {
  return (
    <div className="grid grid-cols-3 gap-1">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="animate-pulse bg-gray-200 aspect-square rounded" />
      ))}
    </div>
  );
}
