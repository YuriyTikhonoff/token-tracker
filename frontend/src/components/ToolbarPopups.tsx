import type { RefreshToast } from "../hooks/useRefreshStatus";

const POPUP =
  "absolute top-full right-0 z-[60] mt-1 rounded-lg border border-[#262b36] bg-[#161a23] shadow-[0_12px_32px_rgba(0,0,0,0.6)]";
const MENU_ITEM =
  "flex w-full cursor-pointer flex-col gap-0.5 rounded-md bg-transparent px-[0.6rem] py-[0.45rem] text-left text-[0.8rem] text-[#c7cbd4] hover:bg-[#1d2129]";

export function UnpricedLabel({ count }: { count: number }) {
  return <>{`⚠ ${count} unpriced model${count === 1 ? "" : "s"}`}</>;
}

export function UnpricedPopup({ models }: { models: string[] }) {
  return (
    <div
      className={`${POPUP} flex w-[min(360px,calc(100vw-4rem))] flex-col gap-2 px-[0.9rem] py-[0.75rem] text-[0.8rem] text-[#c7cbd4]`}
    >
      <strong className="text-[#d9a441]">Costs are rough</strong>
      <span>
        No price for {models.join(", ")}: counted at the default rate. Add{" "}
        {models.length === 1 ? "it" : "them"} to{" "}
        <code className="text-[#e6e6e6]">pricing.json</code> in your data
        directory.
      </span>
    </div>
  );
}

interface MoreMenuProps {
  hasAccounts: boolean;
  unpricedCount: number;
  /** "updated … ago", or null before the first refresh of this page. */
  updated: string | null;
  onOpenAccounts: () => void;
  onOpenUnpriced: () => void;
}

// The ⋯ menu. On a narrow screen it also carries the unpriced-models note and
// the time of the last refresh, which have no room in the bar there.
export function MoreMenu({
  hasAccounts,
  unpricedCount,
  updated,
  onOpenAccounts,
  onOpenUnpriced,
}: MoreMenuProps) {
  return (
    <div
      className={`${POPUP} flex w-[min(300px,calc(100vw-4rem))] flex-col p-1.5`}
    >
      {hasAccounts && (
        <button type="button" className={MENU_ITEM} onClick={onOpenAccounts}>
          Accounts
          <small className="text-[0.72rem] text-[#8a8f98]">
            who used this machine: totals, rename, default
          </small>
        </button>
      )}
      {unpricedCount > 0 && (
        <button
          type="button"
          className={`${MENU_ITEM} md:hidden`}
          onClick={onOpenUnpriced}
        >
          <span className="text-[#d9a441]">
            <UnpricedLabel count={unpricedCount} />
          </span>
          <small className="text-[0.72rem] text-[#8a8f98]">
            counted at the default rate
          </small>
        </button>
      )}
      {updated && (
        <div className="mt-1 border-t border-[#1d2129] px-[0.6rem] pt-[0.45rem] pb-[0.3rem] text-[0.75rem] text-[#8a8f98] md:hidden">
          {updated}
        </div>
      )}
    </div>
  );
}

export function RefreshToastView({
  toast,
  onDismiss,
}: {
  toast: RefreshToast;
  onDismiss: () => void;
}) {
  return (
    <div
      role={toast.isError ? "alert" : "status"}
      className="fixed right-4 bottom-4 z-[70] flex max-w-[min(440px,calc(100vw-2rem))] items-start gap-3 rounded-lg border border-[#262b36] bg-[#161a23] px-[0.9rem] py-[0.65rem] text-[0.8rem] text-[#c7cbd4] shadow-[0_12px_32px_rgba(0,0,0,0.6)]"
    >
      <span
        aria-hidden="true"
        className={`font-bold ${toast.isError ? "text-[#e05a5a]" : "text-[#3ecf8e]"}`}
      >
        {toast.isError ? "!" : "✓"}
      </span>
      <span className="min-w-0 flex-1">{toast.text}</span>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className="cursor-pointer bg-transparent px-1 leading-none text-[#8a8f98]"
      >
        ×
      </button>
    </div>
  );
}
