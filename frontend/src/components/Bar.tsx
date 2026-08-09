interface BarProps {
  value: number;
  max: number;
}

export function Bar({ value, max }: BarProps) {
  const widthPct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <div className="mt-1 h-[6px] overflow-hidden rounded-[3px] bg-[#1d2129]">
      <div
        className="h-full bg-[#5b8def]"
        style={{ width: `${widthPct}%` }}
      />
    </div>
  );
}
