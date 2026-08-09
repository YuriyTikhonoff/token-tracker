import { useEffect } from "react";

export function useRefreshOnWindowFocus(onFocus: () => void) {
  useEffect(() => {
    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        onFocus();
      }
    }

    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [onFocus]);
}
