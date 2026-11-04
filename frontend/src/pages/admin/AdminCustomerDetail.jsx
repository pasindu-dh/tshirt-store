import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAdminCustomer } from "../../api/adminCustomers";
import OrderStatusBadge from "../../components/OrderStatusBadge";
import { getApiError } from "../../utils/errors";

const RETURN_STATUS_CLASSES = {
  requested: "text-yellow-400",
  approved: "text-green-400",
  completed: "text-green-400",
  rejected: "text-red-400",
  cancelled: "text-red-400",
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

function SummaryCard({ label, value, hint }) {
  return (
    <div className="bg-[#020617] border border-gray-800 rounded-2xl p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-xl font-semibold text-gray-100 mt-1">
        {value}
      </p>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

function AdminCustomerDetail({ customerId }) {
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getAdminCustomer(customerId)
      .then((data) => {
        if (!cancelled) setCustomer(data);
      })
      .catch((requestError) => {
        if (cancelled) return;

        if (requestError.response?.status === 404) {
          setNotFound(true);
        } else {
          setError(
            getApiError(
              requestError,
              "Could not load this customer."
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
  }, [customerId]);

  if (loading) {
    return <p className="text-gray-400">Loading customer...</p>;
  }

  if (notFound) {
    return (
      <div className="text-center py-10">
        <h2 className="text-2xl font-bold">Customer not found</h2>
        <Link
          to="/admin/customers"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to customers
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-10">
        <p className="text-red-400">{error}</p>
        <Link
          to="/admin/customers"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to customers
        </Link>
      </div>
    );
  }

  if (!customer) return null;

  return (
    <div>
      <Link
        to="/admin/customers"
        className="text-sm text-gray-400 hover:text-cyan-400"
      >
        ← Back to customers
      </Link>

      <div className="mt-4">
        <h2 className="text-2xl font-bold">{customer.name}</h2>
        <p className="text-sm text-gray-400 mt-1">
          {customer.email} · Customer #{customer.id}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Joined {formatDate(customer.created_at)}
          {customer.last_order_at
            ? ` · Last order ${formatDate(
                customer.last_order_at
              )}`
            : " · No orders yet"}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <SummaryCard
          label="Net spend"
          value={`LKR ${customer.net_spend}`}
          hint="Delivered spend minus completed refunds"
        />
        <SummaryCard
          label="Gross spend"
          value={`LKR ${customer.gross_spend}`}
          hint="Delivered, paid/refunded orders"
        />
        <SummaryCard
          label="Refunds"
          value={`LKR ${customer.refunded_total}`}
          hint={
            customer.pending_refund_total > 0
              ? `Pending LKR ${customer.pending_refund_total}`
              : "No pending refunds"
          }
        />
        <SummaryCard
          label="Orders"
          value={customer.order_count}
          hint={`${customer.delivered_orders} delivered · ${customer.cancelled_orders} cancelled`}
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        <SummaryCard
          label="Returns"
          value={customer.returns_count}
          hint="All return requests"
        />
        <SummaryCard
          label="Open returns"
          value={customer.open_returns}
          hint="Requested or approved"
        />
        <SummaryCard
          label="Delivered orders"
          value={customer.delivered_orders}
          hint="Orders counted toward spend"
        />
        <SummaryCard
          label="Cancelled orders"
          value={customer.cancelled_orders}
          hint="Cancelled before delivery"
        />
      </div>

      <section className="mt-8 bg-[#020617] border border-gray-800 rounded-2xl p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Orders</h3>
          <span className="text-sm text-gray-400">
            {customer.order_count} total
          </span>
        </div>

        {customer.orders.length === 0 ? (
          <p className="text-sm text-gray-400 mt-4">
            This customer has not placed an order yet.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead className="text-left text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="py-2 pr-4">Order</th>
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Payment</th>
                  <th className="py-2 pr-4">Items</th>
                  <th className="py-2 pr-4">Total</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {customer.orders.map((order) => {
                  const itemCount = order.items.reduce(
                    (sum, item) => sum + item.quantity,
                    0
                  );

                  return (
                    <tr
                      key={order.id}
                      className="border-b border-gray-800/60 last:border-0"
                    >
                      <td className="py-3 pr-4 font-medium">
                        Order #{order.id}
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        {formatDate(order.created_at)}
                      </td>
                      <td className="py-3 pr-4">
                        <OrderStatusBadge status={order.status} />
                      </td>
                      <td className="py-3 pr-4 text-gray-300 capitalize">
                        {order.payment_method} ·{" "}
                        {order.payment_status}
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        {itemCount}
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        LKR {order.total}
                      </td>
                      <td className="py-3 text-right">
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

        {customer.order_count > customer.orders.length && (
          <p className="text-xs text-gray-500 mt-3">
            Showing the {customer.orders.length} most recent orders.
          </p>
        )}
      </section>

      <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Return requests</h3>
          <span className="text-sm text-gray-400">
            {customer.returns_count} total ·{" "}
            {customer.open_returns} open
          </span>
        </div>

        {customer.returns.length === 0 ? (
          <p className="text-sm text-gray-400 mt-4">
            This customer has no return requests.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {customer.returns.map((request) => (
              <div
                key={request.id}
                className="border border-gray-800 rounded-xl p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium">
                    Return #{request.id} ·{" "}
                    <Link
                      to={`/admin/orders/${request.order_id}`}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      Order #{request.order_id}
                    </Link>
                  </p>
                  <span
                    className={`text-xs capitalize ${
                      RETURN_STATUS_CLASSES[request.status] ??
                      "text-gray-400"
                    }`}
                  >
                    {request.status}
                  </span>
                </div>

                <p className="text-sm text-gray-300 mt-2">
                  {request.reason}
                </p>
                {request.items?.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {request.items.map((item) => (
                      <li
                        key={item.id}
                        className="text-xs text-gray-400"
                      >
                        {item.product_name} ({item.color} /{" "}
                        {item.size}) × {item.quantity}
                        {item.restocked_at
                          ? " · restocked"
                          : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {request.refund && (
                  <p className="text-xs text-cyan-400 mt-2">
                    Refund LKR {request.refund.amount} ·{" "}
                    {request.refund.status}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  Requested {formatDate(request.created_at)}
                </p>
              </div>
            ))}
          </div>
        )}

        {customer.returns_count > customer.returns.length && (
          <p className="text-xs text-gray-500 mt-3">
            Showing the {customer.returns.length} most recent return
            requests.
          </p>
        )}
      </section>
    </div>
  );
}

function AdminCustomerDetailRoute() {
  const { customerId } = useParams();
  return (
    <AdminCustomerDetail
      key={customerId}
      customerId={customerId}
    />
  );
}

export default AdminCustomerDetailRoute;
