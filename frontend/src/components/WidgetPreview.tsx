import { useState } from "react";

import { API_BASE_URL } from "../api/client";
import { CollapsibleSection } from "./shared/CollapsibleSection";

// Live preview of the standalone overlay page (backend/app/widget.html,
// served at GET /widget) — the exact same page the Hammerspoon floating
// panel loads (widgets/hammerspoon/token-tracker.lua). Iterate on the
// look/size here against real data, then copy the three values below into
// token-tracker.lua; there's no other code to keep in sync.

// Defaults mirror token-tracker.lua. The controls below let you tune them
// against live data before copying back.
const DEFAULTS = { scale: 0.85, baseWidth: 560, baseHeight: 560 };
const MIN_SCALE = 0.4;
const MAX_SCALE = 1.2;

// The Hammerspoon panel is a titled window: hs.webview sizes the web content
// to BASE_HEIGHT*SCALE and macOS adds its ~28pt title bar on top. The iframe
// here is the content area (same as the panel's), and this mock bar makes the
// framed preview match the real window pixel-for-pixel.
const TITLE_BAR = 28;

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
}) {
  return (
    <label className="flex items-center gap-1.5 text-[0.8rem] text-[#c7cbd4]">
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (!Number.isNaN(v)) onChange(Math.min(max, Math.max(min, v)));
        }}
        className="w-[4.5rem] rounded border border-[#262b36] bg-[#161a23] px-1.5 py-0.5 text-[0.8rem] tabular-nums"
      />
    </label>
  );
}

export function WidgetPreview() {
  const [scale, setScale] = useState(DEFAULTS.scale);
  const [baseWidth, setBaseWidth] = useState(DEFAULTS.baseWidth);
  const [baseHeight, setBaseHeight] = useState(DEFAULTS.baseHeight);
  const [reloadKey, setReloadKey] = useState(0);

  const width = Math.floor(baseWidth * scale);
  const height = Math.floor(baseHeight * scale);
  const dirty =
    scale !== DEFAULTS.scale ||
    baseWidth !== DEFAULTS.baseWidth ||
    baseHeight !== DEFAULTS.baseHeight;

  return (
    <CollapsibleSection
      title="Widget preview"
      subtitle={
        <span className="text-[0.8rem] font-normal text-[#8a8f98]">
          — the <code>/widget</code> page the Hammerspoon overlay loads; edit{" "}
          <code>backend/app/widget.html</code>
        </span>
      }
    >
      <div className="mt-4">
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
          <label className="flex items-center gap-2 text-[0.8rem] text-[#c7cbd4]">
            Scale
            <input
              type="range"
              min={MIN_SCALE}
              max={MAX_SCALE}
              step={0.05}
              value={scale}
              onChange={(e) => setScale(Number(e.target.value))}
              className="w-36"
            />
          </label>
          <NumberField
            label="scale"
            value={scale}
            onChange={setScale}
            min={MIN_SCALE}
            max={MAX_SCALE}
            step={0.05}
          />
          <NumberField
            label="base W"
            value={baseWidth}
            onChange={setBaseWidth}
            min={280}
            max={1200}
            step={10}
          />
          <NumberField
            label="base H"
            value={baseHeight}
            onChange={setBaseHeight}
            min={280}
            max={1200}
            step={10}
          />
          <span className="text-[0.75rem] tabular-nums text-[#8a8f98]">
            → {width}×{height + TITLE_BAR} px window ({width}×{height} content)
          </span>
          {dirty && (
            <button
              type="button"
              onClick={() => {
                setScale(DEFAULTS.scale);
                setBaseWidth(DEFAULTS.baseWidth);
                setBaseHeight(DEFAULTS.baseHeight);
              }}
              className="text-[0.75rem] text-[#5b8def] hover:underline"
            >
              reset
            </button>
          )}
          <button
            type="button"
            onClick={() => setReloadKey((k) => k + 1)}
            className="rounded border border-[#262b36] bg-[#161a23] px-3 py-1 text-[0.8rem] text-[#c7cbd4] hover:bg-[#1d2129]"
          >
            Reload preview
          </button>
        </div>

        {/* Mock macOS titled window so the preview matches the Hammerspoon
            panel pixel-for-pixel (the real one clips content by the title-bar
            height when it's missing from the math). */}
        <div
          className="overflow-hidden rounded-xl border border-[#262b36] bg-[#0b0e14]"
          style={{ width, maxWidth: "100%" }}
        >
          <div
            className="flex items-center gap-1.5 border-b border-[#262b36] bg-[#1d2129] px-3"
            style={{ height: TITLE_BAR }}
          >
            <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
            <span className="ml-2 text-[0.7rem] text-[#8a8f98]">Token Tracker</span>
          </div>
          <iframe
            key={`${reloadKey}-${scale}-${baseWidth}-${baseHeight}`}
            title="Token Tracker widget"
            src={`${API_BASE_URL}/widget?scale=${scale}`}
            width={width}
            height={height}
            className="block border-0"
            style={{ maxWidth: "100%" }}
          />
        </div>

        <p className="mt-2 text-[0.75rem] leading-relaxed text-[#5c6068]">
          Copy into <code>widgets/hammerspoon/token-tracker.lua</code> and reload
          the Hammerspoon config:
          <br />
          <code>local SCALE = {scale}</code> ·{" "}
          <code>local BASE_WIDTH = {baseWidth}</code> ·{" "}
          <code>local BASE_HEIGHT = {baseHeight}</code>
          <br />
          After changing <code>widget.html</code>, restart the backend and hit
          Reload preview.
        </p>
      </div>
    </CollapsibleSection>
  );
}
