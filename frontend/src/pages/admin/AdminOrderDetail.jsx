import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { imageUrl } from "../../api/client";
import {
  getAdminOrder,
  updateAdminOrderStatus,
} from "../../api/adminOrders";
import OrderStatusBadge from "../../components/OrderStatusBadge";
import { getApiError } from "../../utils/errors";

const STATUS_ACTIONS = {
  pending: [
    {
      status: "confirmed",
      label: "Confirm order",
      tone: "primary",
    },
    {
      status: "cancelled",
      label: "Cancel order",
      tone: "danger",
      confirm: true,
    },
  ],
  confirmed: [
    {
      status: "shipped",
      label: "Mark as shipped",
      tone: "primary",
    },
    {
      status: "cancelled",
      label: "Cancel order",
      tone: "danger",
      confirm: true,
    },
  ],
  shipped: [
    {
      status: "delivered",
      label: "Mark as delivered",
      tone: "primary",
    },
  ],
  delivered: [],
  cancelled: [],
};

const TONE_CLASSES = {
  primary: "bg-cyan-400 text-black hover:bg-cyan-300",
  danger:
    "border border-red-500/60 text-red-400 hover:bg-red-500/10",
};

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AdminOrderDetail({ orderId }) {
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [updating, setUpdating] = useState(null);
  const [actionError, setActionError] = useState("");
  const [flash, setFlash] = useState("");

  useEffect(() => {
    let cancelled = false;

    getAdminOrder(orderId)
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((requestError) => {
        if (cancelled) return;

        if (requestError.response?.status === 404) {
          setNotFound(true);
        } else {
          setError(
            getApiError(requestError, "Could not load this order.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const handleAction = async (action) => {
    if (
      action.confirm &&
      !window.confirm(
        "Cancel this order? Reserved stock will be restored."
      )
    ) {
      return;
    }

    setUpdating(action.status);
    setActionError("");
    setFlash("");

    try {
      const updated = await updateAdminOrderStatus(
        order.id,
        action.status
      );
      setOrder(updated);
      setFlash(`Order marked as ${updated.status}.`);
    } catch (requestError) {
      setActionError(
        getApiError(requestError, "Could not update the order.")
      );
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <p className="text-gray-400">Loading order...</p>
    );
  }

  if (notFound) {
    return (
      <div className="text-center py-10">
        <h2 className="text-2xl font-bold">Order not found</h2>
        <Link
          to="/admin/orders"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-10">
        <p className="text-red-400">{error}</p>
        <Link
          to="/admin/orders"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  if (!order) return null;

  const actions = STATUS_ACTIONS[order.status] ?? [];

  return (
    <div>
      <Link
        to="/admin/orders"
        className="text-sm text-gray-400 hover:text-cyan-400"
      >
        ← Back to orders
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-4">
        <div>
          <h2 className="text-2xl font-bold">Order #{order.id}</h2>
          <p className="text-sm text-gray-400 mt-1">
            Placed {formatDate(order.created_at)}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <OrderStatusBadge status={order.status} />
          <span className="text-sm text-gray-400 capitalize">
            Payment: {order.payment_status}
          </span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.3fr_0.7fr] gap-6 mt-8">
        <div className="space-y-6">
          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-4">Items</h3>

            <div className="space-y-4">
              {order.items.map((item) => (
                <div key={item.id} className="flex items-center gap-4">
                  <img
                    src={imageUrl(item.image)}
                    alt={item.product_name}
                    className="w-16 h-16 object-cover rounded"
                  />

                  <div className="flex-1">
                    <p>{item.product_name}</p>
                    <p className="text-xs text-gray-500">
                      {item.color} / {item.size} · {item.sku}
                    </p>
                    <p className="text-sm text-gray-400">
                      {item.quantity} × LKR {item.unit_price}
                    </p>
                  </div>

                  <p className="text-cyan-400">
                    LKR {item.line_total}
                  </p>
                </div>
              ))}
            </div>

            <hr className="border-gray-800 my-5" />

            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-300">
                <span>Subtotal</span>
                <span>LKR {order.subtotal}</span>
              </div>
              {order.discount_amount > 0 && (
                <div className="flex justify-between text-green-400">
                  <span>
                    Discount
                    {order.discount_code
                      ? ` (${order.discount_code})`
                      : ""}
                  </span>
                  <span>- LKR {order.discount_amount}</span>
                </div>
              )}
              <div className="flex justify-between text-gray-300">
                <span>Shipping</span>
                <span>LKR {order.shipping_fee}</span>
              </div>
              <div className="flex justify-between text-lg font-semibold pt-2">
                <span>Total</span>
                <span className="text-cyan-400">
                  LKR {order.total}
                </span>
              </div>
            </div>
          </section>

          {order.notes && (
            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
              <h3 className="text-lg font-semibold mb-2">Notes</h3>
              <p className="text-sm text-gray-400 whitespace-pre-line">
                {order.notes}
              </p>
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section className="bg-[#020617] border border-cyan-500/30 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-4">
              Admin actions
            </h3>

            {actions.length > 0 ? (
              <div className="space-y-3">
                {actions.map((action) => (
                  <button
                    key={action.status}
                    type="button"
                    disabled={Boolean(updating)}
                    onClick={() => handleAction(action)}
                    className={`w-full py-2 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed ${TONE_CLASSES[action.tone]}`}
                  >
                    {updating === action.status
                      ? "Updating..."
                      : action.label}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                This order is {order.status}. No further actions are
                available.
              </p>
            )}

            {flash && (
              <p className="text-sm text-green-400 mt-3">{flash}</p>
            )}
            {actionError && (
              <p className="text-sm text-red-400 mt-3">
                {actionError}
              </p>
            )}
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">Customer</h3>
            <div className="text-sm text-gray-300 space-y-1">
              <p>{order.contact_name}</p>
              <p>{order.contact_email}</p>
              <p>{order.phone}</p>
            </div>
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">
              Shipping address
            </h3>
            <div className="text-sm text-gray-300 space-y-1">
              <p>{order.address_line1}</p>
              {order.address_line2 && <p>{order.address_line2}</p>}
              <p>
                {order.city}
                {order.postal_code ? `, ${order.postal_code}` : ""}
              </p>
              <p>{order.country}</p>
            </div>
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">Payment</h3>
            <p className="text-sm text-gray-300">
              {order.payment_method === "cod"
                ? "Cash on Delivery"
                : order.payment_method}
            </p>
            <p className="text-sm text-gray-400 mt-1 capitalize">
              Status: {order.payment_status}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

function AdminOrderDetailRoute() {
  const { orderId } = useParams();
  return <AdminOrderDetail key={orderId} orderId={orderId} />;
}

export default AdminOrderDetailRoute;
