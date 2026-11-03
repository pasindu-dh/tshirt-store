import axios from "axios";
import { getAccessToken } from "./tokens";

export const API_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8005";

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
