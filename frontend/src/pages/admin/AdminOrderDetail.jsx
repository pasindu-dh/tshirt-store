import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { imageUrl } from "../../api/client";
import {
  getAdminOrder,
  getAdminOrderPayments,
  reconcileAdminPayment,
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
  const [payments, setPayments] = useState([]);
  const [paymentsLoading, setPaymentsLoading] = useState(true);
  const [paymentsError, setPaymentsError] = useState("");
  const [reconcilePaymentId, setReconcilePaymentId] = useState("");
  const [reconcileStatus, setReconcileStatus] = useState("paid");
  const [transactionId, setTransactionId] = useState("");
  const [reconcileNote, setReconcileNote] = useState("");
  const [reconciling, setReconciling] = useState(false);
  const [reconcileError, setReconcileError] = useState("");
  const [reconcileMessage, setReconcileMessage] = useState("");

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

  useEffect(() => {
    let cancelled = false;

    getAdminOrderPayments(orderId)
      .then((data) => {
        if (cancelled) return;

        setPayments(data);
        const candidate =
          data.find((payment) =>
            ["pending", "failed"].includes(payment.status)
          ) ?? data[0];
        setReconcilePaymentId(
          candidate ? String(candidate.id) : ""
        );
      })
      .catch((requestError) => {
        if (!cancelled) {
          setPaymentsError(
            getApiError(
              requestError,
              "Could not load payment history."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setPaymentsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const refreshPayments = async () => {
    const data = await getAdminOrderPayments(orderId);
    setPayments(data);
    setPaymentsError("");
    return data;
  };

  const handleReconcile = async (event) => {
    event.preventDefault();
    setReconcileError("");
    setReconcileMessage("");

    if (!reconcilePaymentId) {
      setReconcileError("Select a payment attempt.");
      return;
    }

    if (!reconcileNote.trim()) {
      setReconcileError(
        "Add a note explaining how the transaction was verified."
      );
      return;
    }

    setReconciling(true);

    try {
      await reconcileAdminPayment(
        orderId,
        reconcilePaymentId,
        {
          status: reconcileStatus,
          provider_payment_id: transactionId.trim(),
          note: reconcileNote.trim(),
        }
      );
      const refreshed = await getAdminOrder(orderId);
      setOrder(refreshed);
      await refreshPayments();
      setTransactionId("");
      setReconcileNote("");
      setReconcileMessage("Payment reconciliation recorded.");
    } catch (requestError) {
      setReconcileError(
        getApiError(
          requestError,
          "Could not record payment reconciliation."
        )
      );
    } finally {
      setReconciling(false);
    }
  };

  const handleAction = async (action) => {
    if (
      action.confirm &&
      !window.confirm(
        "Cancel this order? Reserved stock will be restored. If payment is already paid, handle any refund separately."
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

  const onlinePaymentUnpaid =
    order.payment_method === "online" &&
    order.payment_status !== "paid";
  const actions = (STATUS_ACTIONS[order.status] ?? []).filter(
    (action) =>
      !(action.status === "delivered" && onlinePaymentUnpaid)
  );
  const paymentTone =
    order.payment_status === "paid"
      ? "text-green-400"
      : ["failed", "chargedback"].includes(order.payment_status)
        ? "text-red-400"
        : "text-yellow-400";

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

            {onlinePaymentUnpaid && (
              <p className="text-sm text-yellow-400 mt-3">
                Online payment must be paid before this order can be
                marked delivered.
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
                : order.payment_method === "online"
                  ? "Online payment"
                  : order.payment_method}
            </p>
            <p
              className={`text-sm mt-1 capitalize ${paymentTone}`}
            >
              Status: {order.payment_status}
            </p>

            {order.payment_method === "online" &&
              order.reservation_expires_at && (
                <p className="text-xs text-gray-500 mt-2">
                  Stock reservation expires:{" "}
                  {formatDate(order.reservation_expires_at)}
                </p>
              )}

            {order.stock_released_at && (
              <p className="text-xs text-gray-500 mt-2">
                Stock released {formatDate(order.stock_released_at)}
                {order.stock_release_reason
                  ? ` (${order.stock_release_reason})`
                  : ""}
              </p>
            )}
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">
              Payment history
            </h3>

            {paymentsLoading ? (
              <p className="text-sm text-gray-400">
                Loading payment history...
              </p>
            ) : paymentsError ? (
              <p className="text-sm text-red-400">{paymentsError}</p>
            ) : payments.length === 0 ? (
              <p className="text-sm text-gray-400">
                No online payment attempts for this order.
              </p>
            ) : (
              <>
                <div className="space-y-4">
                  {payments.map((payment) => (
                    <div
                      key={payment.id}
                      className="border border-gray-800 rounded-xl p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium break-all">
                            {payment.reference}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {payment.provider} · LKR {payment.amount}
                          </p>
                        </div>
                        <span
                          className={`text-xs capitalize ${
                            payment.status === "paid"
                              ? "text-green-400"
                              : [
                                    "failed",
                                    "chargedback",
                                  ].includes(payment.status)
                                ? "text-red-400"
                                : "text-yellow-400"
                          }`}
                        >
                          {payment.status}
                        </span>
                      </div>

                      <p className="text-xs text-gray-500 mt-2 break-all">
                        Transaction:{" "}
                        {payment.provider_payment_id || "—"}
                      </p>
                      <p className="text-xs text-gray-500">
                        Created: {formatDate(payment.created_at)}
                        {payment.paid_at
                          ? ` · Paid: ${formatDate(payment.paid_at)}`
                          : ""}
                      </p>

                      <ul className="mt-3 space-y-1 border-t border-gray-800 pt-2">
                        {payment.events.map((event) => (
                          <li
                            key={event.id}
                            className="text-xs text-gray-400"
                          >
                            <span className="capitalize text-gray-300">
                              {event.status}
                            </span>{" "}
                            · {event.source} ·{" "}
                            {formatDate(event.created_at)}
                            {event.note ? ` · ${event.note}` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>

                <form
                  onSubmit={handleReconcile}
                  className="mt-5 pt-4 border-t border-gray-800 space-y-3"
                >
                  <div>
                    <h4 className="text-sm font-semibold">
                      Manual reconciliation
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Automatic PayHere lookup is not configured.
                      Verify the transaction in the PayHere dashboard
                      before recording the result here.
                    </p>
                  </div>

                  <label className="block text-xs text-gray-300">
                    Payment attempt
                    <select
                      value={reconcilePaymentId}
                      onChange={(event) =>
                        setReconcilePaymentId(event.target.value)
                      }
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    >
                      {payments.map((payment) => (
                        <option
                          key={payment.id}
                          value={payment.id}
                        >
                          {payment.reference} ({payment.status})
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="block text-xs text-gray-300">
                    Reconciled status
                    <select
                      value={reconcileStatus}
                      onChange={(event) =>
                        setReconcileStatus(event.target.value)
                      }
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    >
                      <option value="paid">Paid</option>
                      <option value="failed">Failed</option>
                      <option value="cancelled">Cancelled</option>
                      <option value="chargedback">Chargedback</option>
                    </select>
                  </label>

                  <label className="block text-xs text-gray-300">
                    PayHere transaction ID
                    <input
                      value={transactionId}
                      onChange={(event) =>
                        setTransactionId(event.target.value)
                      }
                      maxLength={100}
                      placeholder="Required for paid/chargedback"
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    />
                  </label>

                  <label className="block text-xs text-gray-300">
                    Reconciliation note
                    <textarea
                      value={reconcileNote}
                      onChange={(event) =>
                        setReconcileNote(event.target.value)
                      }
                      rows={3}
                      maxLength={500}
                      placeholder="How did you verify this transaction?"
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    />
                  </label>

                  {reconcileError && (
                    <p className="text-sm text-red-400">
                      {reconcileError}
                    </p>
                  )}
                  {reconcileMessage && (
                    <p className="text-sm text-green-400">
                      {reconcileMessage}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={reconciling}
                    className="w-full bg-cyan-400 text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50"
                  >
                    {reconciling
                      ? "Recording..."
                      : "Record reconciliation"}
                  </button>
                </form>
              </>
            )}
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
