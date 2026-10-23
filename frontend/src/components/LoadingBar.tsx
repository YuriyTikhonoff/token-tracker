// A thin bar along the top edge: it shows that something is loading without
// covering the page or blocking clicks, so what has already arrived stays usable.
export function LoadingBar() {
  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[100] h-[2px] overflow-hidden bg-[#262b36]">
      <div className="h-full w-1/3 animate-[loading-bar_1.1s_ease-in-out_infinite] bg-[#5b8def]" />
    </div>
  );
}
