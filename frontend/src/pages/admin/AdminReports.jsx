import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminFinancialReport } from "../../api/adminOrders";
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

function AdminReports() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [groupBy, setGroupBy] = useState("month");
  const [filters, setFilters] = useState({
    dateFrom: "",
    dateTo: "",
    groupBy: "month",
  });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getAdminFinancialReport({
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      group_by: filters.groupBy,
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
              "Could not load the financial report."
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
    setFilters({ dateFrom, dateTo, groupBy });
  };

  const handleReset = () => {
    setDateFrom("");
    setDateTo("");
    setGroupBy("month");
    setLoading(true);
    setError("");
    setFilters({ dateFrom: "", dateTo: "", groupBy: "month" });
  };

  const retry = () => {
    setLoading(true);
    setError("");
    setRefreshKey((current) => current + 1);
  };

  const summary = report?.summary;

  return (
    <div>
      <div>
        <h2 className="text-2xl font-bold">Financial reports</h2>
        <p className="text-gray-400 text-sm mt-1">
          Revenue, refunds, and returns based on order date.
        </p>
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
            Group by
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value)}
              className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            >
              <option value="month">Month</option>
              <option value="day">Day</option>
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
          Gross revenue counts delivered orders with paid or refunded
          payment status. Completed refunds are subtracted; pending
          refunds are shown separately. Chargebacks are excluded.
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
          Loading financial report...
        </p>
      ) : !report ? null : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            <SummaryCard
              label="Gross revenue"
              value={formatMoney(summary.gross_revenue)}
              hint={`${summary.delivered_orders} delivered order${
                summary.delivered_orders === 1 ? "" : "s"
              }`}
            />
            <SummaryCard
              label="Refunds completed"
              value={formatMoney(summary.refunded_total)}
              hint={`${summary.refunded_count} completed refund${
                summary.refunded_count === 1 ? "" : "s"
              }`}
            />
            <SummaryCard
              label="Net revenue"
              value={formatMoney(summary.net_revenue)}
              hint="Gross revenue minus completed refunds"
            />
            <SummaryCard
              label="Pending refunds"
              value={formatMoney(summary.pending_refund_total)}
              hint="Pending or processing"
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
            <SummaryCard
              label="Return requests"
              value={summary.returns_total}
              hint="Created in the selected period"
            />
            <SummaryCard
              label="Open returns"
              value={summary.open_returns}
              hint="Requested or approved"
            />
            <SummaryCard
              label="Completed returns"
              value={summary.completed_returns}
              hint="Items received and restocked"
            />
            <SummaryCard
              label="Returned units"
              value={summary.returned_units}
              hint="Units on completed returns"
            />
          </div>

          <section className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-5">
            <h3 className="text-lg font-semibold">
              Revenue by period
            </h3>

            {report.periods.length === 0 ? (
              <p className="text-sm text-gray-400 mt-4">
                No delivered paid orders in this period.
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm min-w-[560px]">
                  <thead className="text-left text-gray-400 border-b border-gray-800">
                    <tr>
                      <th className="py-2 pr-4">Period</th>
                      <th className="py-2 pr-4">Orders</th>
                      <th className="py-2 pr-4">Gross</th>
                      <th className="py-2 pr-4">Refunds</th>
                      <th className="py-2">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.periods.map((period) => (
                      <tr
                        key={period.period}
                        className="border-b border-gray-800/60 last:border-0"
                      >
                        <td className="py-2 pr-4">
                          {period.period}
                        </td>
                        <td className="py-2 pr-4 text-gray-300">
                          {period.delivered_orders}
                        </td>
                        <td className="py-2 pr-4 text-gray-300">
                          LKR {period.gross_revenue}
                        </td>
                        <td className="py-2 pr-4 text-red-400">
                          - LKR {period.refunded_total}
                        </td>
                        <td className="py-2 text-cyan-400">
                          LKR {period.net_revenue}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
              <h3 className="text-lg font-semibold">Refunds</h3>
              {report.refund_statuses.every(
                (item) => item.count === 0
              ) ? (
                <p className="text-sm text-gray-400 mt-3">
                  No refunds in this period.
                </p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm">
                  {report.refund_statuses
                    .filter((item) => item.count > 0)
                    .map((item) => (
                      <li
                        key={item.status}
                        className="flex items-center justify-between gap-3"
                      >
                        <span className="capitalize text-gray-300">
                          {item.status}
                        </span>
                        <span className="text-gray-400">
                          {item.count} · LKR {item.amount}
                        </span>
                      </li>
                    ))}
                </ul>
              )}
            </section>

            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
              <h3 className="text-lg font-semibold">Returns</h3>
              {report.return_statuses.every(
                (item) => item.count === 0
              ) ? (
                <p className="text-sm text-gray-400 mt-3">
                  No return requests in this period.
                </p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm">
                  {report.return_statuses
                    .filter((item) => item.count > 0)
                    .map((item) => (
                      <li
                        key={item.status}
                        className="flex items-center justify-between gap-3"
                      >
                        <span className="capitalize text-gray-300">
                          {item.status}
                        </span>
                        <span className="text-gray-400">
                          {item.count}
                        </span>
                      </li>
                    ))}
                </ul>
              )}
            </section>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/admin/orders"
              className="px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
            >
              View orders
            </Link>
            <Link
              to="/admin/returns"
              className="px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
            >
              View returns
            </Link>
            <Link
              to="/admin/reports/products"
              className="px-5 py-2 rounded-lg border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
            >
              Product performance
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminReports;
