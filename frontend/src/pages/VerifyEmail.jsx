import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  resendEmailVerification,
  verifyEmail,
} from "../api/auth";
import useAuth from "../hooks/useAuth";
import { getApiError } from "../utils/errors";

function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { user, refreshUser } = useAuth();
  const [email, setEmail] = useState(user?.email ?? "");
  const [verifying, setVerifying] = useState(Boolean(token));
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    verifyEmail(token)
      .then((result) => {
        if (!cancelled) {
          setMessage(
            result.message ||
              "Your email address has been verified."
          );

          if (refreshUser) {
            refreshUser().catch(() => {});
          }
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not verify this email address."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setVerifying(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token, refreshUser]);

  useEffect(() => {
    if (user?.email && !email) {
      setEmail(user.email);
    }
  }, [user, email]);

  const handleResend = async (event) => {
    event.preventDefault();
    setSending(true);
    setError("");
    setMessage("");

    try {
      const result = await resendEmailVerification(
        email.trim()
      );
      setMessage(
        result.message ||
          "If that account needs verification, a new link has been sent."
      );
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not send a verification email."
        )
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen px-6 pb-20 pt-16 flex justify-center">
      <div className="w-full max-w-md">
        <h1 className="text-4xl font-bold text-center">
          Verify email
        </h1>
        <p className="text-center text-gray-400 mt-3">
          Confirm your email address to finish setting up your
          account.
        </p>

        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
          {verifying ? (
            <p className="text-gray-300">
              Verifying your email address...
            </p>
          ) : null}

          {message && (
            <p className="text-green-400 text-sm">{message}</p>
          )}
          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          {!verifying && (
            <form onSubmit={handleResend} className="space-y-4">
              <label className="block">
                <span className="text-sm text-gray-300">
                  Account email
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  required
                  autoComplete="email"
                  className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
                />
              </label>

              <button
                type="submit"
                disabled={sending}
                className="w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending
                  ? "Sending..."
                  : "Send a new verification link"}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-gray-400 mt-6">
          <Link
            to={user ? "/shop" : "/login"}
            className="text-cyan-400 hover:text-cyan-300"
          >
            {user ? "Continue shopping" : "Back to sign in"}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default VerifyEmail;
