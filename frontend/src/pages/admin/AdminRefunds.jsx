import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { downloadRefundsCsv } from "../../api/adminExports";
import { getAdminRefunds } from "../../api/adminRefunds";
import ExportCsvButton from "../../components/admin/ExportCsvButton";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "refunded", label: "Refunded" },
  { value: "failed", label: "Failed" },
];
const KIND_OPTIONS = [
  { value: "", label: "All types" },
  { value: "refund", label: "Refund" },
  { value: "return", label: "Return" },
];
const STATUS_CLASSES = {
  pending: "text-yellow-400",
  processing: "text-yellow-400",
  refunded: "text-green-400",
  failed: "text-red-400",
};

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AdminRefunds() {
  const [refunds, setRefunds] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const appliedSearchRef = useRef("");
  const [statusFilter, setStatusFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const resetResults = useCallback(() => {
    setPage(1);
    setRefunds([]);
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

    getAdminRefunds({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
      status: statusFilter || undefined,
      kind: kindFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setRefunds(result.refunds);
        setTotal(result.total);
        setError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not load refunds."
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
  }, [
    page,
    appliedSearch,
    statusFilter,
    kindFilter,
    dateFrom,
    dateTo,
    refreshKey,
  ]);

  const handleFilterChange = (setter) => (event) => {
    setter(event.target.value);
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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Refunds</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} refund record{total === 1 ? "" : "s"} found
          </p>
        </div>

        <ExportCsvButton
          label="Export refunds CSV"
          onExport={() =>
            downloadRefundsCsv({
              status: statusFilter || undefined,
              kind: kindFilter || undefined,
              date_from: dateFrom || undefined,
              date_to: dateTo || undefined,
            })
          }
        />
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-3 mt-6">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search refund #, order #, customer, reason, reference"
          aria-label="Search refunds"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400 lg:col-span-2"
        />

        <select
          value={statusFilter}
          onChange={handleFilterChange(setStatusFilter)}
          aria-label="Filter refund status"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          value={kindFilter}
          onChange={handleFilterChange(setKindFilter)}
          aria-label="Filter refund type"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          {KIND_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={dateFrom}
          onChange={handleFilterChange(setDateFrom)}
          aria-label="Refunds from date"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <input
          type="date"
          value={dateTo}
          onChange={handleFilterChange(setDateTo)}
          aria-label="Refunds to date"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />
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
        <p className="mt-8 text-gray-400">Loading refunds...</p>
      ) : refunds.length === 0 ? (
        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">No refunds found.</p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[1040px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Refund</th>
                <th className="p-4">Order</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Type / status</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Payment reference</th>
                <th className="p-4">Reason</th>
                <th className="p-4">Created</th>
                <th className="p-4">Completed</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {refunds.map((refund) => (
                <tr
                  key={refund.id}
                  className="border-b border-gray-800/60 last:border-0"
                >
                  <td className="p-4 font-medium">
                    #{refund.id}
                  </td>
                  <td className="p-4">
                    <Link
                      to={`/admin/orders/${refund.order_id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      Order #{refund.order_id}
                    </Link>
                  </td>
                  <td className="p-4">
                    <p className="text-gray-200">
                      {refund.order_contact_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {refund.order_contact_email}
                    </p>
                  </td>
                  <td className="p-4">
                    <p className="text-gray-300 capitalize">
                      {refund.kind}
                    </p>
                    <p
                      className={`text-xs capitalize ${
                        STATUS_CLASSES[refund.status] ??
                        "text-gray-400"
                      }`}
                    >
                      {refund.status}
                    </p>
                  </td>
                  <td className="p-4 font-semibold text-cyan-400">
                    LKR {refund.amount}
                  </td>
                  <td className="p-4 text-xs text-gray-400 break-all max-w-[180px]">
                    {refund.payment_reference}
                  </td>
                  <td className="p-4 text-gray-400 max-w-[220px]">
                    <span className="line-clamp-2">
                      {refund.reason}
                    </span>
                  </td>
                  <td className="p-4 text-xs text-gray-400">
                    {formatDate(refund.created_at)}
                  </td>
                  <td className="p-4 text-xs text-gray-400">
                    {formatDate(refund.completed_at)}
                  </td>
                  <td className="p-4 text-right">
                    <Link
                      to={`/admin/orders/${refund.order_id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      View order
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

export default AdminRefunds;
