import type { Breakdown, Slice } from "./accountSplit";

export function BreakdownToggle({ value, onChange }: { value: Breakdown; onChange: (b: Breakdown) => void }) {
  return (
    <div className="flex overflow-hidden rounded-md border border-[#262b36] text-[0.7rem]" role="group" aria-label="Split bars by">
      {(["tokens", "accounts"] as const).map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={value === option}
          onClick={() => onChange(option)}
          className={`cursor-pointer px-2 py-0.5 ${value === option ? "bg-white/10 text-[#e4e6eb]" : "text-[#8a8f98] hover:text-[#c7cbd4]"}`}
        >
          {option === "tokens" ? "Token type" : "Account"}
        </button>
      ))}
    </div>
  );
}

/** Legend entries; in the account view an account with no usage in any bar is left out. */
export function SliceLegend({ slices }: { slices: Slice[] }) {
  return (
    <>
      {slices.map(({ id, label, className, color }) => (
        <div className="flex items-center gap-[0.4rem] text-[0.75rem] text-[#8a8f98]" key={id}>
          <span
            className={`inline-block h-2.5 w-2.5 rounded-[2px] ${className ?? ""}`}
            style={color ? { backgroundColor: color } : undefined}
          />
          {label}
        </div>
      ))}
    </>
  );
}
