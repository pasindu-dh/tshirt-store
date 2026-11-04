import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminProductReport } from "../../api/adminOrders";
import { getApiError } from "../../utils/errors";

function formatMoney(value) {
  return `LKR ${value ?? 0}`;
}

function SummaryCard({ label, value, hint }) {
  return (
    <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-cyan-400 mt-2">
        {value}
      </p>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

function AdminProductPerformance() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [limit, setLimit] = useState("20");
  const [filters, setFilters] = useState({
    dateFrom: "",
    dateTo: "",
    limit: "20",
  });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getAdminProductReport({
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      limit: Number(filters.limit),
    })
      .then((data) => {
        if (!cancelled) {
          setReport(data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not load product performance."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, refreshKey]);

  const handleApply = (event) => {
    event.preventDefault();

    if (dateFrom && dateTo && dateFrom > dateTo) {
      setError("The start date must be on or before the end date.");
      return;
    }

    setLoading(true);
    setError("");
    setFilters({ dateFrom, dateTo, limit });
  };

  const handleReset = () => {
    setDateFrom("");
    setDateTo("");
    setLimit("20");
    setLoading(true);
    setError("");
    setFilters({ dateFrom: "", dateTo: "", limit: "20" });
  };

  const retry = () => {
    setLoading(true);
    setError("");
    setRefreshKey((current) => current + 1);
  };

  const summary = report?.summary;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">
            Product performance
          </h2>
          <p className="text-gray-400 text-sm mt-1">
            Product and category sales, returns, and current stock
            value.
          </p>
        </div>

        <Link
          to="/admin/reports"
          className="text-sm text-cyan-400 hover:text-cyan-300"
        >
          Financial reports →
        </Link>
      </div>

      <form
        onSubmit={handleApply}
        className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5"
      >
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <label className="block text-sm text-gray-300">
            From
            <input
              type="date"
              value={dateFrom}
              onChange={(event) =>
                setDateFrom(event.target.value)
              }
              className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          <label className="block text-sm text-gray-300">
            To
            <input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          <label className="block text-sm text-gray-300">
            Top products
            <select
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
              className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            >
              <option value="10">Top 10</option>
              <option value="20">Top 20</option>
              <option value="50">Top 50</option>
            </select>
          </label>

          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="flex-1 bg-cyan-400 text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition"
            >
              Apply
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="flex-1 border border-gray-700 text-gray-300 py-2 rounded-lg font-semibold hover:border-cyan-400 hover:text-cyan-400 transition"
            >
              Reset
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-500 mt-3">
          Sales use delivered orders with paid or refunded payment
          status, grouped by order date. Product revenue is the line
          total before order-level discounts and excludes shipping.
          Return rate uses completed returns. Stock figures are the
          current active catalog.
        </p>
      </form>

      {error ? (
        <div className="mt-8 text-center">
          <p className="text-red-400">{error}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
          >
            Try again
          </button>
        </div>
      ) : loading && !report ? (
        <p className="mt-8 text-gray-400">
          Loading product performance...
        </p>
      ) : !report ? null : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            <SummaryCard
              label="Units sold"
              value={summary.units_sold}
              hint={`${summary.products_sold} product${
                summary.products_sold === 1 ? "" : "s"
              } with sales`}
            />
            <SummaryCard
              label="Gross product revenue"
              value={formatMoney(summary.gross_revenue)}
              hint="Before order discounts and shipping"
            />
            <SummaryCard
              label="Returned units"
              value={summary.returned_units}
              hint="Completed returns"
            />
            <SummaryCard
              label="Return rate"
              value={`${summary.return_rate}%`}
              hint="Completed returns ÷ units sold"
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
            <SummaryCard
              label="Current stock value"
              value={formatMoney(summary.current_stock_value)}
              hint="Active variants at product price"
            />
            <SummaryCard
              label="Low-stock variants"
              value={summary.low_stock_variants}
              hint="At or below threshold"
            />
            <SummaryCard
              label="Out-of-stock variants"
              value={summary.out_of_stock_variants}
              hint="Zero units available"
            />
            <SummaryCard
              label="Products with sales"
              value={summary.products_sold}
              hint="In the selected period"
            />
          </div>

          <section className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-5">
            <h3 className="text-lg font-semibold">
              Top products
            </h3>

            {report.products.length === 0 ? (
              <p className="text-sm text-gray-400 mt-4">
                No product sales in this period.
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm min-w-[980px]">
                  <thead className="text-left text-gray-400 border-b border-gray-800">
                    <tr>
                      <th className="py-2 pr-4">#</th>
                      <th className="py-2 pr-4">Product</th>
                      <th className="py-2 pr-4">Units</th>
                      <th className="py-2 pr-4">Orders</th>
                      <th className="py-2 pr-4">Revenue</th>
                      <th className="py-2 pr-4">Returns</th>
                      <th className="py-2 pr-4">Return rate</th>
                      <th className="py-2 pr-4">Stock</th>
                      <th className="py-2 pr-4">Stock value</th>
                      <th className="py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.products.map((product, index) => (
                      <tr
                        key={`${product.product_id ?? "deleted"}-${product.product_slug}`}
                        className="border-b border-gray-800/60 last:border-0"
                      >
                        <td className="py-3 pr-4 text-gray-500">
                          {index + 1}
                        </td>
                        <td className="py-3 pr-4">
                          <p className="text-gray-200">
                            {product.product_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {product.category_name} ·{" "}
                            {product.product_slug}
                          </p>
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {product.units_sold}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {product.order_count}
                        </td>
                        <td className="py-3 pr-4 text-cyan-400">
                          LKR {product.gross_revenue}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {product.returned_units}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {product.return_rate}%
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          <p>{product.current_stock}</p>
                          {product.low_stock_variants > 0 && (
                            <p className="text-xs text-yellow-400">
                              {product.low_stock_variants} low
                            </p>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          LKR {product.stock_value}
                        </td>
                        <td className="py-3 text-right">
                          {product.product_id ? (
                            <Link
                              to={`/admin/products/${product.product_id}/edit`}
                              className="text-cyan-400 hover:text-cyan-300"
                            >
                              Edit
                            </Link>
                          ) : (
                            <span className="text-xs text-gray-500">
                              Deleted
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
            <h3 className="text-lg font-semibold">
              Category performance
            </h3>

            {report.categories.length === 0 ? (
              <p className="text-sm text-gray-400 mt-4">
                No category sales in this period.
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm min-w-[560px]">
                  <thead className="text-left text-gray-400 border-b border-gray-800">
                    <tr>
                      <th className="py-2 pr-4">Category</th>
                      <th className="py-2 pr-4">Products</th>
                      <th className="py-2 pr-4">Units</th>
                      <th className="py-2">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.categories.map((category) => (
                      <tr
                        key={
                          category.category_id ?? "uncategorized"
                        }
                        className="border-b border-gray-800/60 last:border-0"
                      >
                        <td className="py-2 pr-4 text-gray-200">
                          {category.category_name}
                        </td>
                        <td className="py-2 pr-4 text-gray-300">
                          {category.product_count}
                        </td>
                        <td className="py-2 pr-4 text-gray-300">
                          {category.units_sold}
                        </td>
                        <td className="py-2 text-cyan-400">
                          LKR {category.gross_revenue}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default AdminProductPerformance;
