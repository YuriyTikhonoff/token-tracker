import { useCallback, useState } from "react";

const STORAGE_KEY = "token-tracker:selected-account";

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

// null = every account combined. Remembered across reloads, best effort.
export function useSelectedAccount() {
  const [account, setAccountState] = useState<string | null>(readStored);
  const setAccount = useCallback((next: string | null) => {
    setAccountState(next);
    try {
      if (next) localStorage.setItem(STORAGE_KEY, next);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      // storage unavailable: the selection just won't survive a reload
    }
  }, []);
  return [account, setAccount] as const;
}
