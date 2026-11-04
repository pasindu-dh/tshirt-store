import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminCustomers } from "../../api/adminCustomers";
import { downloadCustomersCsv } from "../../api/adminExports";
import ExportCsvButton from "../../components/admin/ExportCsvButton";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 10;

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function AdminCustomers() {
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const appliedSearchRef = useRef("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const resetResults = useCallback(() => {
    setPage(1);
    setCustomers([]);
    setTotal(0);
    setError("");
    setLoading(true);
  }, []);

  useEffect(() => {
    const trimmed = search.trim();
    const timeout = setTimeout(() => {
      if (appliedSearchRef.current === trimmed) return;

      appliedSearchRef.current = trimmed;
      setAppliedSearch(trimmed);
      resetResults();
    }, 300);

    return () => clearTimeout(timeout);
  }, [search, resetResults]);

  useEffect(() => {
    let cancelled = false;

    getAdminCustomers({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setCustomers(result.customers);
        setTotal(result.total);
        setError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not load customers."
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
  }, [page, appliedSearch, refreshKey]);

  const goToPage = (nextPage) => {
    setLoading(true);
    setError("");
    setPage(nextPage);
  };

  const retry = () => {
    resetResults();
    setRefreshKey((current) => current + 1);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Customers</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} customer{total === 1 ? "" : "s"} found
          </p>
        </div>

        <ExportCsvButton
          label="Export customers CSV"
          onExport={() =>
            downloadCustomersCsv({
              search: appliedSearch || undefined,
            })
          }
        />
      </div>

      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search by name, email, or customer #"
        aria-label="Search customers"
        className="mt-6 w-full p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
      />

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
      ) : loading ? (
        <p className="mt-8 text-gray-400">Loading customers...</p>
      ) : customers.length === 0 ? (
        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">No customers found.</p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[940px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Customer</th>
                <th className="p-4">Joined</th>
                <th className="p-4">Orders</th>
                <th className="p-4">Net spend</th>
                <th className="p-4">Gross / refunds</th>
                <th className="p-4">Returns</th>
                <th className="p-4">Last order</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {customers.map((customer) => (
                <tr
                  key={customer.id}
                  className="border-b border-gray-800/60 last:border-0"
                >
                  <td className="p-4">
                    <p className="text-gray-200">
                      {customer.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {customer.email}
                    </p>
                    <p className="text-xs text-gray-600">
                      Customer #{customer.id}
                    </p>
                  </td>

                  <td className="p-4 text-gray-300">
                    {formatDate(customer.created_at)}
                  </td>

                  <td className="p-4 text-gray-300">
                    <p>{customer.order_count}</p>
                    <p className="text-xs text-gray-500">
                      {customer.delivered_orders} delivered ·{" "}
                      {customer.cancelled_orders} cancelled
                    </p>
                  </td>

                  <td className="p-4 font-semibold text-cyan-400">
                    LKR {customer.net_spend}
                  </td>

                  <td className="p-4 text-gray-300">
                    <p>LKR {customer.gross_spend}</p>
                    <p className="text-xs text-gray-500">
                      Refunded LKR {customer.refunded_total}
                      {customer.pending_refund_total > 0
                        ? ` · pending LKR ${customer.pending_refund_total}`
                        : ""}
                    </p>
                  </td>

                  <td className="p-4 text-gray-300">
                    <p>{customer.returns_count} total</p>
                    <p className="text-xs text-gray-500">
                      {customer.open_returns} open
                    </p>
                  </td>

                  <td className="p-4 text-gray-300">
                    {formatDate(customer.last_order_at)}
                  </td>

                  <td className="p-4 text-right">
                    <Link
                      to={`/admin/customers/${customer.id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => goToPage(page - 1)}
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
            onClick={() => goToPage(page + 1)}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminCustomers;
