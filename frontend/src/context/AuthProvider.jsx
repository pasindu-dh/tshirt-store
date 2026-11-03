import { useEffect, useState } from "react";
import { getMe, loginUser, refreshAuth, registerUser } from "../api/auth";
import { clearStoredAuth, getStoredAuth, setStoredAuth } from "../api/tokens";
import AuthContext from "./AuthContext";

function toStoredAuth(data) {
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: data.user,
  };
}

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredAuth()?.user ?? null);
  const [loading, setLoading] = useState(() =>
    Boolean(getStoredAuth()?.access_token)
  );

  useEffect(() => {
    const stored = getStoredAuth();

    if (!stored?.access_token) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function restoreSession() {
      try {
        const me = await getMe();

        if (!cancelled) {
          setUser(me);
          setStoredAuth({ ...stored, user: me });
        }
      } catch {
        try {
          const refreshed = await refreshAuth(stored.refresh_token);

          if (!cancelled) {
            const next = toStoredAuth(refreshed);
            setStoredAuth(next);
            setUser(next.user);
          }
        } catch {
          if (!cancelled) {
            clearStoredAuth();
            setUser(null);
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (email, password) => {
    const data = await loginUser({ email, password });
    const next = toStoredAuth(data);

    setStoredAuth(next);
    setUser(next.user);

    return next.user;
  };

  const register = async ({ name, email, password }) => {
    const data = await registerUser({ name, email, password });
    const next = toStoredAuth(data);

    setStoredAuth(next);
    setUser(next.user);

    return next.user;
  };

  const logout = () => {
    clearStoredAuth();
    setUser(null);
  };

  const value = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    isAdmin: user?.role === "admin",
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
