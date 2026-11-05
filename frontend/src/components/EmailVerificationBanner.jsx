import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAuthConfig } from "../api/auth";
import useAuth from "../hooks/useAuth";

function EmailVerificationBanner() {
  const { user } = useAuth();
  const [config, setConfig] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getAuthConfig()
      .then((data) => {
        if (!cancelled) setConfig(data);
      })
      .catch(() => {
        if (!cancelled) setConfig(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (
    !user ||
    !config?.email_verification_required ||
    user.email_verified
  ) {
    return null;
  }

  return (
    <div className="px-4 pt-2">
      <div
        role="alert"
        className="mx-auto max-w-6xl rounded-xl border border-yellow-500/50 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-200"
      >
        Your email address is not verified.{" "}
        <Link
          to="/verify-email"
          className="font-semibold text-yellow-300 underline hover:text-yellow-100"
        >
          Verify your email
        </Link>{" "}
        to keep access to your account.
      </div>
    </div>
  );
}

export default EmailVerificationBanner;
