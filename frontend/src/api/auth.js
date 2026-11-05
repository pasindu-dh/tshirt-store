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

export async function getAuthConfig() {
  const { data } = await client.get("/auth/config");
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await client.post("/auth/password/forgot", {
    email,
  });
  return data;
}

export async function resetPassword(token, newPassword) {
  const { data } = await client.post("/auth/password/reset", {
    token,
    new_password: newPassword,
  });
  return data;
}

export async function verifyEmail(token) {
  const { data } = await client.post("/auth/verify-email", {
    token,
  });
  return data;
}

export async function resendEmailVerification(email) {
  const { data } = await client.post(
    "/auth/verify-email/resend",
    { email }
  );
  return data;
}
