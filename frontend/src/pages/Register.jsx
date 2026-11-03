import { useState } from "react";
import {
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";
import useAuth from "../hooks/useAuth";
import { getApiError } from "../utils/errors";

function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return (
      <Navigate to={location.state?.from ?? "/"} replace />
    );
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

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
      await register({ name, email, password });
      navigate(location.state?.from ?? "/shop", { replace: true });
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Unable to create your account. Please try again."
        )
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen px-6 pb-20 pt-16 flex justify-center">
      <div className="w-full max-w-md">
        <h1 className="text-4xl font-bold text-center">Create account</h1>
        <p className="text-center text-gray-400 mt-3">
          Join FURZY and start shopping
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4"
        >
          <label className="block">
            <span className="text-sm text-gray-300">Name</span>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              autoComplete="name"
              className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

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

          <label className="block">
            <span className="text-sm text-gray-300">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-300">Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="mt-1 w-full p-3 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-gray-400 mt-6">
          Already have an account?{" "}
          <Link
            to="/login"
            state={location.state}
            className="text-cyan-400 hover:text-cyan-300"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default Register;
