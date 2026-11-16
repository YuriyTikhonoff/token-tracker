import type { CostAuditStatus } from "../api/types";
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

function auditDate(audit: CostAuditStatus): string | null {
  if (!audit.last) return null;
  return new Date(audit.last.audited_at).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** One line for the menu: when the costs were last checked. */
function auditSummary(audit: CostAuditStatus): string {
  const date = auditDate(audit);
  if (!date) return "Cost calculation never audited";
  return `Costs audited ${date} (${audit.age_days} d ago)`;
}

export function AuditPopup({ audit }: { audit: CostAuditStatus }) {
  const last = audit.last;
  return (
    <div
      className={`${POPUP} flex w-[min(380px,calc(100vw-4rem))] flex-col gap-2 px-[0.9rem] py-[0.75rem] text-[0.8rem] text-[#c7cbd4]`}
    >
      <strong className={audit.due ? "text-[#e05a5a]" : "text-[#3ecf8e]"}>
        {audit.overdue
          ? "Cost audit overdue"
          : audit.due
            ? "Cost audit due"
            : "Cost calculation audited"}
      </strong>
      {last ? (
        <span>
          Last checked against Anthropic&apos;s prices and rules on{" "}
          {auditDate(audit)}: calculation v{last.algorithm_version}, prices of{" "}
          {last.pricing_updated ?? "unknown date"}.
          {last.note && (
            <span className="mt-1 block text-[#8a8f98]">{last.note}</span>
          )}
        </span>
      ) : (
        <span>No audit of the cost calculation is recorded yet.</span>
      )}
      {audit.due && (
        <span>
          Due: {audit.reasons.join(", ")}. The costs are checked against
          Anthropic&apos;s published prices and rules every two weeks. Check
          them, then run{" "}
          <code className="text-[#e6e6e6]">
            token-tracker audit-costs --note "…"
          </code>
          .
        </span>
      )}
    </div>
  );
}

interface MoreMenuProps {
  hasAccounts: boolean;
  unpricedCount: number;
  /** "updated … ago", or null before the first refresh of this page. */
  updated: string | null;
  audit: CostAuditStatus | null;
  onOpenAccounts: () => void;
  onOpenUnpriced: () => void;
  onOpenAudit: () => void;
}

// The ⋯ menu. On a narrow screen it also carries the unpriced-models note and
// the time of the last refresh, which have no room in the bar there.
export function MoreMenu({
  hasAccounts,
  unpricedCount,
  updated,
  audit,
  onOpenAccounts,
  onOpenUnpriced,
  onOpenAudit,
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
      {audit && (
        <button type="button" className={MENU_ITEM} onClick={onOpenAudit}>
          <span className={audit.due ? "text-[#e05a5a]" : undefined}>
            {audit.due ? "⚠ " : ""}
            {auditSummary(audit)}
          </span>
          <small className="text-[0.72rem] text-[#8a8f98]">
            {audit.due
              ? `due: ${audit.reasons.join(", ")}`
              : "against Anthropic's published prices and rules"}
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
