import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminProducts } from "../../api/admin";
import { getCategories } from "../../api/categories";
import { getApiError } from "../../utils/errors";

function StatCard({ label, value }) {
  return (
    <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-3xl font-bold text-cyan-400 mt-2">{value ?? "..."}</p>
    </div>
  );
}

function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    Promise.all([getAdminProducts({ limit: 100 }), getCategories()])
      .then(([productData, categories]) => {
        if (cancelled) return;

        const products = productData.products;

        setStats({
          total: productData.total,
          active: products.filter((product) => product.is_active).length,
          lowStock: products.reduce(
            (sum, product) =>
              sum +
              product.variants.filter((variant) => variant.stock <= 5).length,
            0
          ),
          categories: categories.length,
        });
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load dashboard data.")
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold">Dashboard</h2>
      <p className="text-gray-400 text-sm mt-1">
        A quick overview of your catalog.
      </p>

      {error ? (
        <p className="mt-6 text-red-400">{error}</p>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <StatCard label="Total products" value={stats?.total} />
          <StatCard label="Active products" value={stats?.active} />
          <StatCard label="Low-stock variants" value={stats?.lowStock} />
          <StatCard label="Categories" value={stats?.categories} />
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4 mt-8">
        <Link
          to="/admin/products/new"
          className="bg-[#020617] border border-cyan-500/40 rounded-2xl p-5 hover:border-cyan-400 transition"
        >
          <h3 className="font-semibold">Add a product</h3>
          <p className="text-sm text-gray-400 mt-2">
            Upload images, set sizes, and publish to the storefront.
          </p>
        </Link>

        <Link
          to="/admin/products"
          className="bg-[#020617] border border-gray-800 rounded-2xl p-5 hover:border-cyan-400 transition"
        >
          <h3 className="font-semibold">Manage products</h3>
          <p className="text-sm text-gray-400 mt-2">
            Edit prices, stock, visibility, or remove products.
          </p>
        </Link>

        <Link
          to="/admin/categories"
          className="bg-[#020617] border border-gray-800 rounded-2xl p-5 hover:border-cyan-400 transition"
        >
          <h3 className="font-semibold">Manage categories</h3>
          <p className="text-sm text-gray-400 mt-2">
            Organize the catalog into shoppable groups.
          </p>
        </Link>
      </div>
    </div>
  );
}

export default AdminDashboard;
