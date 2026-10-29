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

  return (
    <div className="mb-6 flex flex-wrap items-center gap-2 text-[0.8rem]">
      <span className="text-[#8a8f98]">Account:</span>
      {options.map((option) => {
        const isActive = option.key === selected;
        return (
          <button
            key={option.key ?? "all"}
            title={option.title}
            onClick={() => onSelect(option.key)}
            className={`inline-flex cursor-pointer items-center gap-[0.4rem] rounded-md border px-[0.7rem] py-[0.25rem] ${
              isActive
                ? "border-[#5b8def] bg-[#5b8def]/15 text-[#c7cbd4]"
                : "border-[#262b36] bg-transparent text-[#8a8f98]"
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
