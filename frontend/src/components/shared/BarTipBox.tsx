import { createPortal } from "react-dom";
import { fmtCost, fmtTokens } from "../../lib/format";
import { shareLabel, type Slice } from "./accountSplit";

export interface Tip {
  x: number;
  y: number;
  heading: string;
  slices: Slice[];
}

export function BarTipBox({ tip }: { tip: Tip }) {
  const total = tip.slices.reduce((sum, slice) => sum + slice.amount, 0);
  // The bar stacks its slices bottom to top; list them the way they look, top first.
  const rows = tip.slices.filter((slice) => slice.amount > 0).reverse();
  // Near the right edge the box opens to the left of the pointer so it is never cut off.
  const flip = tip.x > window.innerWidth - 280;
  return createPortal(
    <div
      role="presentation"
      className="pointer-events-none fixed z-50 rounded-md border border-[#262b36] bg-[#0d1017] px-3 py-2 text-[0.75rem] whitespace-nowrap text-[#e6e6e6] shadow-lg"
      style={{ left: tip.x + (flip ? -14 : 14), top: tip.y + 14, transform: flip ? "translateX(-100%)" : undefined }}
    >
      <div className="mb-1.5 font-semibold">{tip.heading}</div>
      <div className="grid grid-cols-[auto_auto_auto_auto] items-center gap-x-3 gap-y-1 tabular-nums">
        {rows.map((slice) => (
          <div key={slice.id} className="contents">
            <span className="flex items-center gap-1.5 text-[#c7cbd4]">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-[2px] ${slice.className ?? ""}`}
                style={slice.color ? { backgroundColor: slice.color } : undefined}
              />
              {slice.label}
            </span>
            <span className="text-right">{fmtTokens(slice.amount)}</span>
            <span className="text-right text-[#8a8f98]">{shareLabel(slice.amount, total)}</span>
            <span className="text-right text-[#8a8f98]">{slice.cost === undefined ? "" : fmtCost(slice.cost)}</span>
          </div>
        ))}
      </div>
    </div>,
    document.body,
  );
}
