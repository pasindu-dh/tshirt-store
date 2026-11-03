import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BACKEND_ENV = path.resolve(HERE, "../../backend/.env");

function readBackendEnv() {
  try {
    const contents = fs.readFileSync(BACKEND_ENV, "utf8");
    const values = {};

    for (const line of contents.split(/\r?\n/)) {
      const trimmed = line.trim();

      if (!trimmed || trimmed.startsWith("#")) continue;

      const separator = trimmed.indexOf("=");

      if (separator === -1) continue;

      const key = trimmed.slice(0, separator).trim();
      let value = trimmed.slice(separator + 1).trim();

      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }

      values[key] = value;
    }

    return values;
  } catch {
    return {};
  }
}

const backendEnv = readBackendEnv();

export const API_URL = (
  process.env.E2E_API_URL || "http://127.0.0.1:8005"
).replace(/\/$/, "");

export const BASE_URL =
  process.env.E2E_BASE_URL || "http://127.0.0.1:5173";

export const adminCredentials = {
  email: process.env.E2E_ADMIN_EMAIL || backendEnv.ADMIN_EMAIL || "",
  password:
    process.env.E2E_ADMIN_PASSWORD || backendEnv.ADMIN_PASSWORD || "",
};
