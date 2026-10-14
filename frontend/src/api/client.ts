// Empty means same origin: the packaged dashboard is served by the backend
// itself. The Vite dev server is on another port, so .env.development points
// it at the backend.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

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
