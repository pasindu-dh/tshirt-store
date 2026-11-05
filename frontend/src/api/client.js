import axios from "axios";
import {
  clearStoredAuth,
  getAccessToken,
  getStoredAuth,
  setStoredAuth,
} from "./tokens";

const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(
  /\/$/,
  ""
);

if (import.meta.env.PROD && !configuredApiUrl) {
  // Vercel must define VITE_API_URL before building. Keep the local
  // fallback for development, but make a missing production value loud.
  console.error(
    "VITE_API_URL is not set for this production build; API calls will fall back to localhost."
  );
}

export const API_URL =
  configuredApiUrl || "http://127.0.0.1:8005";

const client = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

client.interceptors.request.use((config) => {
  const token = getAccessToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const url = original?.url ?? "";

    if (
      status !== 401 ||
      !original ||
      original._retry ||
      url.startsWith("/auth/")
    ) {
      throw error;
    }

    const stored = getStoredAuth();

    if (!stored?.access_token || !stored?.refresh_token) {
      throw error;
    }

    original._retry = true;

    try {
      refreshPromise =
        refreshPromise ??
        axios.post(
          `${API_URL}/auth/refresh`,
          { refresh_token: stored.refresh_token },
          { timeout: 10000 }
        );

      const { data } = await refreshPromise;

      setStoredAuth({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        user: data.user,
      });

      original.headers = original.headers ?? {};
      original.headers.Authorization = `Bearer ${data.access_token}`;

      return client(original);
    } catch (refreshError) {
      clearStoredAuth();

      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("furzy:logout"));
      }

      throw refreshError;
    } finally {
      refreshPromise = null;
    }
  }
);

/**
 * Turn a backend image path (e.g. "/images/t_shirt_01.jpg") into a full URL.
 * Already-absolute URLs are returned unchanged.
 */
export function imageUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export default client;
