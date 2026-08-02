/**
 * Skeleton placeholder matching the dashboard's KPI + module card rhythm, so
 * the layout does not shift once real data arrives.
 */
export default function LoadingState() {
  return (
    <div className="space-y-6" aria-busy="true" aria-live="polite">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="skeleton h-9 w-9 rounded-lg" />
              <div className="skeleton h-4 w-12 rounded-full" />
            </div>
            <div className="skeleton mb-2.5 h-3 w-20" />
            <div className="skeleton h-6 w-28" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="card p-6">
            <div className="skeleton mb-4 h-9 w-9 rounded-lg" />
            <div className="skeleton mb-3 h-4 w-32" />
            <div className="skeleton mb-1.5 h-3 w-full" />
            <div className="skeleton h-3 w-3/4" />
          </div>
        ))}
      </div>
    </div>
  );
}
