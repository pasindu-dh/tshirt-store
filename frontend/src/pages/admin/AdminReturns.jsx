import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminReturns } from "../../api/adminOrders";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "requested", label: "Requested" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const STATUS_CLASSES = {
  requested: "text-yellow-400",
  approved: "text-green-400",
  completed: "text-green-400",
  rejected: "text-red-400",
  cancelled: "text-red-400",
};

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function AdminReturns() {
  const [returns, setReturns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const appliedSearchRef = useRef("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const resetResults = useCallback(() => {
    setPage(1);
    setReturns([]);
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

    getAdminReturns({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
      status: statusFilter || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setReturns(result.returns);
        setTotal(result.total);
        setError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not load return requests."
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
  }, [page, appliedSearch, statusFilter, refreshKey]);

  const handleStatusChange = (event) => {
    setStatusFilter(event.target.value);
    resetResults();
  };

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
      <div>
        <h2 className="text-2xl font-bold">Returns</h2>
        <p className="text-gray-400 text-sm mt-1">
          {total} return request{total === 1 ? "" : "s"} found
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-6">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by return #, order #, name, email, or reason"
          aria-label="Search return requests"
          className="flex-1 p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <select
          value={statusFilter}
          onChange={handleStatusChange}
          aria-label="Filter by return status"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

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
        <p className="mt-8 text-gray-400">
          Loading return requests...
        </p>
      ) : returns.length === 0 ? (
        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">
            No return requests found.
          </p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[880px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Return</th>
                <th className="p-4">Date</th>
                <th className="p-4">Order</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Items</th>
                <th className="p-4">Reason</th>
                <th className="p-4">Refund</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {returns.map((request) => (
                <tr
                  key={request.id}
                  className="border-b border-gray-800/60 last:border-0"
                >
                  <td className="p-4 font-medium">
                    #{request.id}
                  </td>

                  <td className="p-4 text-gray-300">
                    {formatDate(request.created_at)}
                  </td>

                  <td className="p-4 text-gray-300">
                    <Link
                      to={`/admin/orders/${request.order_id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      Order #{request.order_id}
                    </Link>
                  </td>

                  <td className="p-4">
                    <p className="text-gray-200">
                      {request.order_contact_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {request.order_contact_email}
                    </p>
                  </td>

                  <td className="p-4 text-gray-300">
                    {request.item_count} item
                    {request.item_count === 1 ? "" : "s"}
                  </td>

                  <td className="p-4 text-gray-400 max-w-[220px]">
                    <span className="line-clamp-2">
                      {request.reason}
                    </span>
                  </td>

                  <td className="p-4 text-gray-400">
                    {request.refund_id ? (
                      <span className="capitalize">
                        #{request.refund_id} ·{" "}
                        {request.refund_status}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>

                  <td className="p-4">
                    <span
                      className={`text-xs capitalize ${
                        STATUS_CLASSES[request.status] ??
                        "text-gray-400"
                      }`}
                    >
                      {request.status}
                    </span>
                  </td>

                  <td className="p-4 text-right">
                    <Link
                      to={`/admin/orders/${request.order_id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      Review
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

export default AdminReturns;
