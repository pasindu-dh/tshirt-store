import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminOrders } from "../../api/adminOrders";
import OrderStatusBadge from "../../components/OrderStatusBadge";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "shipped", label: "Shipped" },
  { value: "delivered", label: "Delivered" },
  { value: "cancelled", label: "Cancelled" },
];

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function AdminOrders() {
  const [orders, setOrders] = useState([]);
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
    setOrders([]);
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

    getAdminOrders({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
      status: statusFilter || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setOrders(result.orders);
        setTotal(result.total);
        setError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load orders.")
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
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Orders</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} order{total === 1 ? "" : "s"} found
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-6">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by order #, name, or email"
          aria-label="Search orders"
          className="flex-1 p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <select
          value={statusFilter}
          onChange={handleStatusChange}
          aria-label="Filter by order status"
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
        <p className="mt-8 text-gray-400">Loading orders...</p>
      ) : orders.length === 0 ? (
        <div className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">No orders found.</p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[820px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Order</th>
                <th className="p-4">Date</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Items</th>
                <th className="p-4">Total</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {orders.map((order) => {
                const itemCount = order.items.reduce(
                  (sum, item) => sum + item.quantity,
                  0
                );

                return (
                  <tr
                    key={order.id}
                    className="border-b border-gray-800/60 last:border-0"
                  >
                    <td className="p-4 font-medium">
                      Order #{order.id}
                    </td>

                    <td className="p-4 text-gray-300">
                      {formatDate(order.created_at)}
                    </td>

                    <td className="p-4">
                      <p className="text-gray-200">
                        {order.contact_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {order.contact_email}
                      </p>
                    </td>

                    <td className="p-4 text-gray-300">
                      {itemCount} item{itemCount === 1 ? "" : "s"}
                    </td>

                    <td className="p-4 text-gray-300">
                      LKR {order.total}
                    </td>

                    <td className="p-4">
                      <OrderStatusBadge status={order.status} />
                    </td>

                    <td className="p-4 text-right">
                      <Link
                        to={`/admin/orders/${order.id}`}
                        className="text-cyan-400 hover:text-cyan-300"
                      >
                        View
                      </Link>
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

export default AdminOrders;
