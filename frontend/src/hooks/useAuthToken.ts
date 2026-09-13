export function useAuthToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem("nway_access_token");
}
