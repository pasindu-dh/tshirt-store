import client from "./client";

export async function registerUser({ name, email, password }) {
  const { data } = await client.post("/auth/register", {
    name,
    email,
    password,
  });

  return data;
}

export async function loginUser({ email, password }) {
  const body = new URLSearchParams({ username: email, password });

  const { data } = await client.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  return data;
}

export async function getMe() {
  const { data } = await client.get("/auth/me");
  return data;
}

export async function refreshAuth(refreshToken) {
  const { data } = await client.post("/auth/refresh", {
    refresh_token: refreshToken,
  });

  return data;
}
