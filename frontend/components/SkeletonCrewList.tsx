/**
 * Crew List 骨架屏组件
 * 用于加载时显示占位内容，提升用户体验
 */
export function SkeletonCrewList() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array(6).fill(0).map((_, i) => (
        <div key={i} className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6 animate-pulse">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 rounded-xl bg-zinc-800" />
            <div className="w-16 h-6 rounded bg-zinc-800" />
          </div>
          <div className="h-6 w-3/4 bg-zinc-800 rounded mb-2" />
          <div className="h-10 w-full bg-zinc-800 rounded mb-6" />
          <div className="flex justify-between pt-4 border-t border-[var(--border-color)]">
            <div className="h-4 w-20 bg-zinc-800 rounded" />
            <div className="h-4 w-20 bg-zinc-800 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * 工具列表骨架屏组件
 */
export function SkeletonToolList() {
  return (
    <div className="space-y-4 p-4">
      <div className="h-4 bg-gray-300 rounded w-1/4 mb-2 animate-pulse" />
      <div className="space-y-2">
        {Array(3).fill(0).map((_, i) => (
          <div key={i} className="h-12 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}

/**
 * 加载指示器组件
 */
export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex items-center justify-center">
      <div
        className={`${sizeClasses[size]} border-2 border-zinc-600 border-t-transparent rounded-full animate-spin`}
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}
