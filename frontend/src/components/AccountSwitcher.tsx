import type { AccountSummary } from "../api/types";

interface AccountSwitcherProps {
  accounts: AccountSummary[];
  selected: string | null;
  onSelect: (account: string | null) => void;
}

export function AccountSwitcher({
  accounts,
  selected,
  onSelect,
}: AccountSwitcherProps) {
  const options: { key: string | null; label: string; title?: string }[] = [
    { key: null, label: "All accounts" },
    ...accounts.map((account) => ({
      key: account.account_uuid,
      label: account.label,
      title: account.email ?? undefined,
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
            className={`cursor-pointer rounded-md border px-[0.7rem] py-[0.25rem] ${
              isActive
                ? "border-[#5b8def] bg-[#5b8def]/15 text-[#c7cbd4]"
                : "border-[#262b36] bg-transparent text-[#8a8f98]"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
