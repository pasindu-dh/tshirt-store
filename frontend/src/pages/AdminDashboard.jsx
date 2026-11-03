import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminProducts } from "../api/admin";
import useAuth from "../hooks/useAuth";
import { getApiError } from "../utils/errors";

function AdminDashboard() {
  const { user } = useAuth();
  const [total, setTotal] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getAdminProducts({ limit: 100 })
      .then((result) => {
        if (!cancelled) {
          setTotal(result.total);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load admin data.")
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <h1 className="text-4xl font-bold text-center">Admin Dashboard</h1>
      <p className="text-center text-gray-400 mt-3">
        Signed in as {user?.name} ({user?.email})
      </p>

      <div className="max-w-3xl mx-auto mt-10 bg-[#020617] border border-gray-800 rounded-2xl p-6">
        {error ? (
          <p className="text-red-400">{error}</p>
        ) : (
          <p className="text-lg">
            Products in catalog:{" "}
            <span className="text-cyan-400 font-semibold">
              {total ?? "..."}
            </span>
          </p>
        )}

        <p className="text-gray-400 mt-4">
          Product management arrives in Phase 3.
        </p>

        <Link
          to="/shop"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          View storefront
        </Link>
      </div>
    </div>
  );
}

export default AdminDashboard;
