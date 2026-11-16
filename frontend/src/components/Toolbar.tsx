import { useCallback, useRef, useState } from "react";

import type { AccountLabel } from "../api/types";
import { useDismiss, useNow, usePageScrolled } from "../hooks/usePageUi";
import { useRefreshStatus } from "../hooks/useRefreshStatus";
import { AccountSwitcher } from "./AccountSwitcher";
import {
  MoreMenu,
  RefreshToastView,
  UnpricedPopup,
  UnpricedLabel,
} from "./ToolbarPopups";

interface ToolbarProps {
  accounts: (AccountLabel & { email?: string | null })[];
  selectedAccount: string | null;
  onSelectAccount: (account: string | null) => void;
  /** Models with no price: their costs are counted at the default rate. */
  unknownModels: string[];
  onOpenAccounts: () => void;
}

function updatedLabel(refreshedAt: number, now: number): string {
  const minutes = Math.floor((now - refreshedAt) / 60_000);
  if (minutes < 1) return "updated just now";
  if (minutes < 60) return `updated ${minutes} min ago`;
  return `updated ${Math.floor(minutes / 60)}h ago`;
}

// The one bar at the top of the page: the account switcher, a note about
// unpriced models, when the data was last refreshed, the ⋯ menu and Refresh.
// It stays at the top while the page scrolls, so switching accounts or
// refreshing never needs a trip back up. On a narrow screen the switcher
// moves to a second row.
export function Toolbar({
  accounts,
  selectedAccount,
  onSelectAccount,
  unknownModels,
  onOpenAccounts,
}: ToolbarProps) {
  const refresh = useRefreshStatus();
  const [popup, setPopup] = useState<"unpriced" | "menu" | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const now = useNow(30_000);
  const scrolled = usePageScrolled();

  const closePopup = useCallback(() => setPopup(null), []);
  useDismiss(endRef, popup !== null, closePopup);
  const toggle = (which: "unpriced" | "menu") =>
    setPopup(popup === which ? null : which);

  const updated =
    refresh.refreshedAt === null
      ? null
      : updatedLabel(refresh.refreshedAt, now);
  const hasUnpriced = unknownModels.length > 0;
  const hasMenu = accounts.length > 0 || hasUnpriced || updated !== null;

  return (
    <>
      <div
        className={`sticky top-0 z-50 -mx-8 mb-4 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b bg-[#0b0e14] px-8 py-2 [grid-template-areas:'title_end'_'seg_seg'] md:grid-cols-[auto_minmax(0,1fr)_auto] md:[grid-template-areas:'title_seg_end'] ${
          scrolled
            ? "border-[#262b36] shadow-[0_6px_16px_rgba(0,0,0,0.4)]"
            : "border-transparent"
        }`}
      >
        <h1 className="text-[1.4rem] font-bold whitespace-nowrap [grid-area:title]">
          Token Tracker
        </h1>
        {accounts.length > 0 && (
          <div className="min-w-0 [grid-area:seg]">
            <AccountSwitcher
              accounts={accounts}
              selected={selectedAccount}
              onSelect={onSelectAccount}
            />
          </div>
        )}
        <div
          ref={endRef}
          className="relative flex items-center gap-2 [grid-area:end]"
        >
          {hasUnpriced && (
            <button
              type="button"
              aria-expanded={popup === "unpriced"}
              onClick={() => toggle("unpriced")}
              className="hidden cursor-pointer items-center rounded-full border border-[#d9a441]/40 bg-[#d9a441]/12 px-[0.6rem] py-[0.1rem] text-[0.75rem] font-semibold whitespace-nowrap text-[#d9a441] md:inline-flex"
            >
              <UnpricedLabel count={unknownModels.length} />
            </button>
          )}
          {updated && (
            <span className="hidden text-[0.75rem] whitespace-nowrap text-[#8a8f98] tabular-nums md:inline">
              {updated}
            </span>
          )}
          {hasMenu && (
            <button
              type="button"
              aria-label="More"
              aria-expanded={popup === "menu"}
              onClick={() => toggle("menu")}
              className={`grid h-[28px] w-[30px] cursor-pointer place-items-center rounded-md border bg-transparent text-[1rem] leading-none text-[#c7cbd4] ${
                popup === "menu" ? "border-[#5b8def]" : "border-[#262b36]"
              }`}
            >
              ⋯
            </button>
          )}
          <button
            type="button"
            className="cursor-pointer rounded-md border border-[#262b36] bg-transparent px-[0.8rem] py-[0.3rem] text-[0.8rem] whitespace-nowrap text-[#8a8f98]"
            disabled={refresh.isPending}
            onClick={() => refresh.run(true)}
            title="Also forces a fresh Codex rate-limit reading (spends a small amount of real Codex tokens)"
          >
            {refresh.isPending ? "Refreshing…" : "Refresh"}
          </button>

          {popup === "unpriced" && <UnpricedPopup models={unknownModels} />}
          {popup === "menu" && (
            <MoreMenu
              hasAccounts={accounts.length > 0}
              unpricedCount={unknownModels.length}
              updated={updated}
              onOpenAccounts={() => {
                setPopup(null);
                onOpenAccounts();
              }}
              onOpenUnpriced={() => setPopup("unpriced")}
            />
          )}
        </div>
      </div>
      {refresh.toast && (
        <RefreshToastView
          toast={refresh.toast}
          onDismiss={refresh.dismissToast}
        />
      )}
    </>
  );
}
