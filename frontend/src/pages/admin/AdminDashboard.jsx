import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getAdminFinancialReport,
  getAdminProductReport,
  getAdminStats,
} from "../../api/adminOrders";
import SalesOverview from "../../components/admin/SalesOverview";
import { getApiError } from "../../utils/errors";
import { dateRangeDays } from "../../utils/sales";

function StatCard({ label, value, hint }) {
  return (
    <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-3xl font-bold text-cyan-400 mt-2">
        {value ?? "..."}
      </p>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

function SmallStat({ label, value }) {
  return (
    <div className="bg-[#020617] border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-xl font-semibold text-gray-100 mt-1">
        {value ?? "..."}
      </p>
    </div>
  );
}

function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [rangeDays, setRangeDays] = useState(30);
  const [salesReport, setSalesReport] = useState(null);
  const [topProducts, setTopProducts] = useState(null);
  const [salesLoading, setSalesLoading] = useState(true);
  const [salesError, setSalesError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getAdminStats()
      .then((data) => {
        if (!cancelled) {
          setStats(data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load dashboard data.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  useEffect(() => {
    let cancelled = false;
    const { dateFrom, dateTo } = dateRangeDays(rangeDays);

    Promise.all([
      getAdminFinancialReport({
        date_from: dateFrom,
        date_to: dateTo,
        group_by: "day",
      }),
      getAdminProductReport({
        date_from: dateFrom,
        date_to: dateTo,
        limit: 5,
      }),
    ])
      .then(([financial, products]) => {
        if (cancelled) return;

        setSalesReport(financial);
        setTopProducts(products);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setSalesError(
            getApiError(
              requestError,
              "Could not load the sales overview."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setSalesLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [rangeDays, refreshKey]);

  const handleRangeChange = (days) => {
    setSalesLoading(true);
    setSalesError("");
    setSalesReport(null);
    setTopProducts(null);
    setRangeDays(days);
  };

  const retry = () => {
    setLoading(true);
    setError("");
    setSalesLoading(true);
    setSalesError("");
    setRefreshKey((current) => current + 1);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold">Dashboard</h2>
      <p className="text-gray-400 text-sm mt-1">
        Store performance and order overview.
      </p>

      {error ? (
        <div className="mt-10 text-center">
          <p className="text-red-400">{error}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            <StatCard
              label="Net revenue (delivered)"
              value={stats ? `LKR ${stats.revenue}` : null}
              hint={
                stats
                  ? `Gross LKR ${stats.gross_revenue} − refunds LKR ${stats.refunded_total}`
                  : undefined
              }
            />
            <StatCard
              label="Open orders"
              value={stats?.open_orders}
              hint="Pending, confirmed, or shipped"
            />
            <StatCard
              label="Pending orders"
              value={stats?.pending_orders}
              hint="Awaiting confirmation"
            />
            <StatCard
              label="Low-stock variants"
              value={stats?.low_stock_variants}
              hint={
                stats
                  ? `At or below threshold · ${stats.out_of_stock_variants} out of stock`
                  : "At or below each variant's threshold"
              }
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
            <SmallStat
              label="Gross revenue"
              value={
                stats ? `LKR ${stats.gross_revenue}` : null
              }
            />
            <SmallStat
              label="Refunds completed"
              value={
                stats ? `LKR ${stats.refunded_total}` : null
              }
            />
            <SmallStat
              label="Pending refunds"
              value={
                stats ? `LKR ${stats.pending_refund_total}` : null
              }
            />
            <SmallStat
              label="Open returns"
              value={stats?.open_returns}
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
            <SmallStat
              label="Total orders"
              value={stats?.orders_total}
            />
            <SmallStat
              label="Delivered"
              value={stats?.delivered_orders}
            />
            <SmallStat
              label="Cancelled"
              value={stats?.cancelled_orders}
            />
            <SmallStat
              label="Products"
              value={stats?.products_total}
            />
            <SmallStat
              label="Categories"
              value={stats?.categories_total}
            />
          </div>

          <SalesOverview
            report={salesReport}
            products={topProducts}
            rangeDays={rangeDays}
            onRangeChange={handleRangeChange}
            loading={salesLoading}
            error={salesError}
          />

          {!loading && !stats && (
            <p className="mt-4 text-xs text-gray-500">
              Dashboard data is unavailable.
            </p>
          )}

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
            <Link
              to="/admin/orders"
              className="bg-[#020617] border border-cyan-500/40 rounded-2xl p-5 hover:border-cyan-400 transition"
            >
              <h3 className="font-semibold">Manage orders</h3>
              <p className="text-sm text-gray-400 mt-2">
                Confirm, ship, deliver, or cancel customer orders.
              </p>
            </Link>

            <Link
              to="/admin/products/new"
              className="bg-[#020617] border border-gray-800 rounded-2xl p-5 hover:border-cyan-400 transition"
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

            <Link
              to="/admin/reports"
              className="bg-[#020617] border border-cyan-500/40 rounded-2xl p-5 hover:border-cyan-400 transition"
            >
              <h3 className="font-semibold">Financial reports</h3>
              <p className="text-sm text-gray-400 mt-2">
                Review gross revenue, refunds, returns, and period
                summaries.
              </p>
            </Link>

            <Link
              to="/admin/inventory"
              className="bg-[#020617] border border-cyan-500/40 rounded-2xl p-5 hover:border-cyan-400 transition"
            >
              <h3 className="font-semibold">Inventory</h3>
              <p className="text-sm text-gray-400 mt-2">
                Review low-stock alerts and adjust stock with an
                audit trail.
              </p>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminDashboard;
