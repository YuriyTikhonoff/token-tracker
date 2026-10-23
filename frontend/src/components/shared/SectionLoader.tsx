import type { ReactNode } from "react";

import { useSection } from "../../hooks/useSection";

interface SectionLoaderProps<T> {
  path: string;
  account: string | null;
  children: (data: T) => ReactNode;
}

// Fetches a section's data when it mounts (that is, when the section is opened)
// and shows a small spinner inside the section until it arrives.
export function SectionLoader<T>({ path, account, children }: SectionLoaderProps<T>) {
  const query = useSection<T>(path, account);

  if (query.data !== undefined) return <>{children(query.data)}</>;

  if (query.isError) {
    return (
      <div role="alert" className="py-4 text-[0.85rem] text-[#e05a5a]">
        Could not load this section: {query.error.message}{" "}
        <button
          className="cursor-pointer text-[#8a8f98] underline"
          onClick={() => void query.refetch()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div role="status" className="flex items-center gap-2 py-4 text-[0.85rem] text-[#8a8f98]">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[#262b36] border-t-[#5b8def]" />
      Loading…
    </div>
  );
}
