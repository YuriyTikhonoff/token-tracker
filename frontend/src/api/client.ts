// Base URL resolved by build target rather than hardcoded — desktop (Tauri)
// and local-web builds both point at a locally-running backend, but via
// separate .env files so there's no runtime branching logic here.
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8765";

export async function fetchJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(
      `${init?.method ?? "GET"} ${path} failed: ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}
