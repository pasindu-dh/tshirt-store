import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getAuthConfig,
  requestPasswordReset,
} from "../api/auth";
import { getApiError } from "../utils/errors";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resetAvailable, setResetAvailable] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getAuthConfig()
      .then((config) => {
        if (!cancelled) {
          setResetAvailable(
            Boolean(config.password_reset_available)
          );
        }
      })
      .catch(() => {
        if (!cancelled) setResetAvailable(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);

    try {
      const result = await requestPasswordReset(email.trim());
      setMessage(
        result.message ||
          "If an account exists, a password reset email has been sent."
      );
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not request a password reset."
        )
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen px-6 pb-20 pt-16 flex justify-center">
      <div className="w-full max-w-md">
        <h1 className="text-4xl font-bold text-center">
          Forgot password
        </h1>
        <p className="text-center text-gray-400 mt-3">
          Enter your account email and we will send a reset link.
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4"
        >
          <label className="block">
            <span className="text-sm text-gray-300">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          {resetAvailable === false && (
            <p className="text-yellow-400 text-sm">
              Email delivery is not configured for this deployment,
              so password reset emails cannot be sent. Contact the
              store administrator if you need help signing in.
            </p>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}
          {message && (
            <p className="text-green-400 text-sm">{message}</p>
          )}

          <button
            type="submit"
            disabled={submitting || resetAvailable === false}
            className="w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="text-center text-gray-400 mt-6">
          <Link
            to="/login"
            className="text-cyan-400 hover:text-cyan-300"
          >
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default ForgotPassword;
