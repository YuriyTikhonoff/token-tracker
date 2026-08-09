export function LoadingOverlay() {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b0e14]/50">
      <div className="h-10 w-10 animate-[spin_0.8s_linear_infinite] rounded-full border-[3px] border-[#262b36] border-t-[#5b8def]" />
    </div>
  );
}
