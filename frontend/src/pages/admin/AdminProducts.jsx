import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  deleteAdminProduct,
  getAdminProducts,
  updateAdminProduct,
} from "../../api/admin";
import { imageUrl } from "../../api/client";
import { getCategories } from "../../api/categories";
import { downloadCatalogCsv } from "../../api/adminExports";
import ExportCsvButton from "../../components/admin/ExportCsvButton";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 10;

function AdminProducts() {
  const location = useLocation();

  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState(location.state?.message ?? "");
  const [refreshKey, setRefreshKey] = useState(0);
  const [busyId, setBusyId] = useState(null);

  const refresh = () => setRefreshKey((current) => current + 1);

  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setAppliedSearch(search.trim());
      setPage(1);
    }, 300);

    return () => clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    if (!flash) return;

    const timeout = setTimeout(() => setFlash(""), 4000);
    return () => clearTimeout(timeout);
  }, [flash]);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");

    getAdminProducts({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
      category: category || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setProducts(result.products);
        setTotal(result.total);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load products.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, appliedSearch, category, refreshKey]);

  const handleToggle = async (product) => {
    setBusyId(product.id);
    setError("");

    try {
      await updateAdminProduct(product.id, {
        is_active: !product.is_active,
      });
      setFlash(product.is_active ? "Product deactivated." : "Product activated.");
      refresh();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not update the product.")
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (product) => {
    if (!window.confirm(`Delete "${product.name}"? This cannot be undone.`)) {
      return;
    }

    setBusyId(product.id);
    setError("");

    try {
      await deleteAdminProduct(product.id);
      setFlash("Product deleted.");

      if (products.length === 1 && page > 1) {
        setPage((current) => current - 1);
      } else {
        refresh();
      }
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not delete the product.")
      );
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Products</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} product{total === 1 ? "" : "s"} in the catalog
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/admin/products/import"
            className="border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400 transition"
          >
            Import CSV
          </Link>
          <ExportCsvButton
            label="Export catalog CSV"
            onExport={() => downloadCatalogCsv()}
          />
          <Link
            to="/admin/products/new"
            className="bg-cyan-400 text-black px-5 py-2 rounded-lg font-semibold hover:bg-cyan-300 transition text-center"
          >
            Add product
          </Link>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-6">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search products..."
          className="flex-1 p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <select
          value={category}
          onChange={(event) => {
            setCategory(event.target.value);
            setPage(1);
          }}
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          <option value="">All categories</option>
          {categories.map((item) => (
            <option key={item.id} value={item.slug}>
              {item.name}
            </option>
          ))}
        </select>
      </div>

      {flash && <p className="mt-4 text-green-400 text-sm">{flash}</p>}
      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      {loading ? (
        <p className="mt-8 text-gray-400">Loading products...</p>
      ) : products.length === 0 ? (
        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">No products found.</p>
          <Link
            to="/admin/products/new"
            className="inline-block mt-4 text-cyan-400 hover:text-cyan-300"
          >
            Add your first product
          </Link>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Product</th>
                <th className="p-4">Category</th>
                <th className="p-4">Price</th>
                <th className="p-4">Stock</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {products.map((product) => {
                const stock = product.variants.reduce(
                  (sum, variant) => sum + variant.stock,
                  0
                );
                const busy = busyId === product.id;

                return (
                  <tr
                    key={product.id}
                    className="border-b border-gray-800/60 last:border-0"
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {product.image ? (
                          <img
                            src={imageUrl(product.image)}
                            alt=""
                            className="w-12 h-12 rounded object-cover"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded bg-gray-800" />
                        )}

                        <div>
                          <p className="font-medium">{product.name}</p>
                          <p className="text-xs text-gray-500">
                            {product.slug}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="p-4 text-gray-300">
                      {product.category?.name ?? "Uncategorized"}
                    </td>

                    <td className="p-4 text-gray-300">LKR {product.price}</td>

                    <td className="p-4 text-gray-300">{stock}</td>

                    <td className="p-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          product.is_active
                            ? "bg-green-500/15 text-green-400"
                            : "bg-gray-700/40 text-gray-400"
                        }`}
                      >
                        {product.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>

                    <td className="p-4">
                      <div className="flex justify-end gap-3">
                        <Link
                          to={`/admin/products/${product.id}/edit`}
                          className="text-cyan-400 hover:text-cyan-300"
                        >
                          Edit
                        </Link>

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleToggle(product)}
                          className="text-gray-300 hover:text-white disabled:opacity-50"
                        >
                          {product.is_active ? "Deactivate" : "Activate"}
                        </button>

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleDelete(product)}
                          className="text-red-400 hover:text-red-300 disabled:opacity-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => setPage((current) => current - 1)}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Previous
          </button>

          <span className="text-sm text-gray-400">
            Page {page} of {totalPages}
          </span>

          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => current + 1)}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminProducts;
