import type { AccountLabel } from "../api/types";

const CURRENT_TITLE = "logged in to Claude Code now";

interface AccountSwitcherProps {
  accounts: (AccountLabel & { email?: string | null })[];
  selected: string | null;
  onSelect: (account: string | null) => void;
}

export function AccountSwitcher({
  accounts,
  selected,
  onSelect,
}: AccountSwitcherProps) {
  const options: {
    key: string | null;
    label: string;
    title?: string;
    current?: boolean;
  }[] = [
    { key: null, label: "All accounts" },
    ...accounts.map((account) => ({
      key: account.account_uuid,
      label: account.label,
      title:
        [account.email, account.is_current ? CURRENT_TITLE : null]
          .filter(Boolean)
          .join(" · ") || undefined,
      current: account.is_current,
    })),
  ];

  // A segmented control: one outlined group, the chosen account filled. It
  // scrolls sideways rather than wrapping when the accounts do not fit.
  return (
    <div
      role="group"
      aria-label="Account"
      className="flex w-max max-w-full gap-0.5 overflow-x-auto rounded-lg border border-[#262b36] p-0.5 text-[0.8rem] [scrollbar-width:none]"
    >
      {options.map((option) => {
        const isActive = option.key === selected;
        return (
          <button
            key={option.key ?? "all"}
            type="button"
            aria-pressed={isActive}
            title={option.title}
            onClick={() => onSelect(option.key)}
            className={`inline-flex shrink-0 cursor-pointer items-center gap-[0.4rem] rounded-md px-[0.7rem] py-[0.25rem] whitespace-nowrap ${
              isActive
                ? "bg-[#5b8def]/15 text-[#c7cbd4]"
                : "bg-transparent text-[#8a8f98] hover:text-[#c7cbd4]"
            }`}
          >
            {option.current && (
              <span
                aria-hidden="true"
                className="size-[7px] shrink-0 rounded-full bg-[#3ecf8e] shadow-[0_0_0_3px_rgba(62,207,142,0.2)]"
              />
            )}
            {option.label}
            {option.current && (
              <span className="sr-only"> ({CURRENT_TITLE})</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
