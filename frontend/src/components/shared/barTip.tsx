import { useState, type PointerEvent } from "react";
import { fmtCost, fmtTokens } from "../../lib/format";
import { sliceLines, type Slice } from "./accountSplit";
import { BarTipBox, type Tip } from "./BarTipBox";

/**
 * An instant tooltip that follows the pointer, in place of the browser's `title`, which waits a
 * second or two before it shows. Spread `bind(heading, slices)` on each bar and render `node` once.
 */
export function useBarTip() {
  const [tip, setTip] = useState<Tip | null>(null);

  const bind = (heading: string, slices: Slice[]) => ({
    role: "img" as const,
    "aria-label": [heading, ...sliceLines(slices, fmtTokens, fmtCost)].join(", "),
    onPointerEnter: (e: PointerEvent) => setTip({ x: e.clientX, y: e.clientY, heading, slices }),
    onPointerMove: (e: PointerEvent) => setTip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : t)),
    onPointerLeave: () => setTip(null),
  });

  return { bind, node: tip ? <BarTipBox tip={tip} /> : null };
}
