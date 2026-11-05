import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api/auth";
import { getApiError } from "../utils/errors";

function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const result = await resetPassword(token, password);
      setMessage(
        result.message || "Your password has been reset."
      );
      setPassword("");
      setConfirmPassword("");
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not reset your password."
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
          Reset password
        </h1>
        <p className="text-center text-gray-400 mt-3">
          Choose a new password for your FURZY account.
        </p>

        {!token ? (
          <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <p className="text-red-400 text-sm">
              This reset link is missing its token. Request a new
              link to continue.
            </p>
            <Link
              to="/forgot-password"
              className="inline-block mt-4 text-cyan-400 hover:text-cyan-300"
            >
              Request a new link
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4"
          >
            <label className="block">
              <span className="text-sm text-gray-300">
                New password
              </span>
              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                required
                minLength={8}
                autoComplete="new-password"
                className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
              />
            </label>

            <label className="block">
              <span className="text-sm text-gray-300">
                Confirm new password
              </span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) =>
                  setConfirmPassword(event.target.value)
                }
                required
                minLength={8}
                autoComplete="new-password"
                className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
              />
            </label>

            {error && (
              <p className="text-red-400 text-sm">{error}</p>
            )}
            {message && (
              <p className="text-green-400 text-sm">{message}</p>
            )}

            <button
              type="submit"
              disabled={submitting || Boolean(message)}
              className="w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Saving..." : "Set new password"}
            </button>
          </form>
        )}

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

export default ResetPassword;
