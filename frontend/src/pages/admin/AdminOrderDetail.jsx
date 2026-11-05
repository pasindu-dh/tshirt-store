import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { imageUrl } from "../../api/client";
import {
  createAdminRefund,
  getAdminOrder,
  getAdminOrderActivity,
  getAdminOrderAudit,
  getAdminOrderPayments,
  getAdminOrderReturns,
  linkAdminReturnRefund,
  reconcileAdminPayment,
  reconcileAdminPaymentWithProvider,
  reviewAdminOrderReturn,
  updateAdminOrderDetails,
  updateAdminOrderStatus,
  updateAdminRefund,
} from "../../api/adminOrders";
import OrderActivityTimeline from "../../components/admin/OrderActivityTimeline";
import OrderEditForm from "../../components/admin/OrderEditForm";
import OrderStatusBadge from "../../components/OrderStatusBadge";
import { getApiError } from "../../utils/errors";
import { RETURN_REASON_LABELS } from "../../utils/returns";

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

const RETURN_STATUS_CLASSES = {
  requested: "text-yellow-400",
  approved: "text-green-400",
  completed: "text-green-400",
  rejected: "text-red-400",
  cancelled: "text-red-400",
};

const ORDER_FIELD_LABELS = {
  contact_name: "Contact name",
  contact_email: "Contact email",
  phone: "Phone",
  address_line1: "Address line 1",
  address_line2: "Address line 2",
  city: "City",
  postal_code: "Postal code",
  country: "Country",
  notes: "Internal notes",
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
  const [refundPaymentId, setRefundPaymentId] = useState("");
  const [refundKind, setRefundKind] = useState("refund");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [refundNotes, setRefundNotes] = useState("");
  const [processWithProvider, setProcessWithProvider] = useState(false);
  const [refunding, setRefunding] = useState(false);
  const [refundError, setRefundError] = useState("");
  const [refundMessage, setRefundMessage] = useState("");
  const [providerVerifying, setProviderVerifying] = useState(null);
  const [providerError, setProviderError] = useState("");
  const [providerMessage, setProviderMessage] = useState("");
  const [returns, setReturns] = useState([]);
  const [returnsLoading, setReturnsLoading] = useState(true);
  const [returnsError, setReturnsError] = useState("");
  const [returnReviewNote, setReturnReviewNote] = useState("");
  const [returnActionId, setReturnActionId] = useState(null);
  const [linkRefundId, setLinkRefundId] = useState("");
  const [returnMessage, setReturnMessage] = useState("");
  const [audit, setAudit] = useState([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState("");
  const [activity, setActivity] = useState([]);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityError, setActivityError] = useState("");
  const [activityRefreshKey, setActivityRefreshKey] =
    useState(0);
  const [editingDetails, setEditingDetails] = useState(false);
  const [detailsSaving, setDetailsSaving] = useState(false);
  const [detailsError, setDetailsError] = useState("");
  const [detailsMessage, setDetailsMessage] = useState("");

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
        setRefundPaymentId(
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

  useEffect(() => {
    let cancelled = false;

    getAdminOrderReturns(orderId)
      .then((data) => {
        if (!cancelled) setReturns(data);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setReturnsError(
            getApiError(
              requestError,
              "Could not load return requests."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setReturnsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  useEffect(() => {
    let cancelled = false;

    getAdminOrderAudit(orderId)
      .then((data) => {
        if (!cancelled) setAudit(data);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setAuditError(
            getApiError(
              requestError,
              "Could not load the order audit history."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setAuditLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  useEffect(() => {
    let cancelled = false;

    setActivityError("");
    getAdminOrderActivity(orderId)
      .then((data) => {
        if (!cancelled) setActivity(data);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setActivityError(
            getApiError(
              requestError,
              "Could not load the order activity."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setActivityLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId, activityRefreshKey]);

  const refreshActivity = () => {
    setActivityRefreshKey((current) => current + 1);
  };

  const refreshPayments = async () => {
    const data = await getAdminOrderPayments(orderId);
    setPayments(data);
    setPaymentsError("");
    return data;
  };

  const refreshReturns = async () => {
    const data = await getAdminOrderReturns(orderId);
    setReturns(data);
    setReturnsError("");
    return data;
  };

  const handleReviewReturn = async (returnId, status) => {
    if (
      status === "completed" &&
      !window.confirm(
        "Mark this return completed? The returned items will be added back to stock."
      )
    ) {
      return;
    }

    setReturnActionId(returnId);
    setReturnsError("");
    setReturnMessage("");

    try {
      await reviewAdminOrderReturn(orderId, returnId, {
        status,
        note: returnReviewNote.trim(),
      });
      await refreshReturns();
      refreshActivity();
      setReturnReviewNote("");
      setReturnMessage(`Return request ${status}.`);
    } catch (requestError) {
      setReturnsError(
        getApiError(
          requestError,
          "Could not review the return request."
        )
      );
    } finally {
      setReturnActionId(null);
    }
  };

  const handleLinkReturnRefund = async (returnId) => {
    const refunds = payments.flatMap(
      (payment) => payment.refunds ?? []
    );
    const selected =
      linkRefundId || (refunds[0] ? String(refunds[0].id) : "");

    if (!selected) {
      setReturnsError(
        "Create a refund record in Payment history first."
      );
      return;
    }

    setReturnsError("");
    setReturnMessage("");

    try {
      await linkAdminReturnRefund(
        orderId,
        returnId,
        Number(selected)
      );
      await refreshReturns();
      setLinkRefundId("");
      setReturnMessage("Refund linked to return request.");
    } catch (requestError) {
      setReturnsError(
        getApiError(
          requestError,
          "Could not link the refund."
        )
      );
    }
  };

  const handleSaveDetails = async (payload) => {
    setDetailsSaving(true);
    setDetailsError("");
    setDetailsMessage("");

    try {
      const updated = await updateAdminOrderDetails(
        orderId,
        payload
      );
      setOrder(updated);
      setEditingDetails(false);
      setDetailsMessage("Order details updated.");
      refreshActivity();

      try {
        setAudit(await getAdminOrderAudit(orderId));
        setAuditError("");
      } catch {
        setAuditError(
          "Could not refresh the order audit history."
        );
      }
    } catch (requestError) {
      setDetailsError(
        getApiError(
          requestError,
          "Could not update the order details."
        )
      );
    } finally {
      setDetailsSaving(false);
    }
  };

  const handleProviderReconcile = async (payment) => {
    setProviderVerifying(payment.id);
    setProviderError("");
    setProviderMessage("");

    try {
      await reconcileAdminPaymentWithProvider(
        orderId,
        payment.id
      );
      const refreshedOrder = await getAdminOrder(orderId);
      setOrder(refreshedOrder);
      await refreshPayments();
      await refreshReturns().catch(() => {});
      refreshActivity();
      setProviderMessage("PayHere verification recorded.");
    } catch (requestError) {
      setProviderError(
        getApiError(
          requestError,
          "Could not verify the payment with PayHere."
        )
      );
    } finally {
      setProviderVerifying(null);
    }
  };

  const handleCreateRefund = async (event) => {
    event.preventDefault();
    setRefundError("");
    setRefundMessage("");

    if (!refundPaymentId) {
      setRefundError("Select a payment attempt.");
      return;
    }

    if (!refundAmount || Number(refundAmount) < 1) {
      setRefundError("Enter a valid refund amount.");
      return;
    }

    if (!refundReason.trim()) {
      setRefundError("Enter a refund/return reason.");
      return;
    }

    setRefunding(true);

    try {
      await createAdminRefund(orderId, refundPaymentId, {
        kind: refundKind,
        amount: Number(refundAmount),
        reason: refundReason.trim(),
        notes: refundNotes.trim(),
        process_with_provider: processWithProvider,
      });
      const refreshedOrder = await getAdminOrder(orderId);
      setOrder(refreshedOrder);
      await refreshPayments();
      await refreshReturns().catch(() => {});
      setRefundAmount("");
      setRefundReason("");
      setRefundNotes("");
      setProcessWithProvider(false);
      refreshActivity();
      setRefundMessage("Refund/return record saved.");
    } catch (requestError) {
      setRefundError(
        getApiError(
          requestError,
          "Could not save the refund/return record."
        )
      );
    } finally {
      setRefunding(false);
    }
  };

  const handleMarkRefunded = async (refund) => {
    if (
      !window.confirm(
        `Mark refund #${refund.id} as completed? This should only be done after the money has been returned.`
      )
    ) {
      return;
    }

    setRefundError("");
    setRefundMessage("");

    try {
      await updateAdminRefund(orderId, refund.id, {
        status: "refunded",
        note: "Marked completed by admin.",
      });
      const refreshedOrder = await getAdminOrder(orderId);
      setOrder(refreshedOrder);
      await refreshPayments();
      await refreshReturns().catch(() => {});
      refreshActivity();
      setRefundMessage("Refund marked completed.");
    } catch (requestError) {
      setRefundError(
        getApiError(requestError, "Could not update the refund.")
      );
    }
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
      refreshActivity();
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
      refreshActivity();
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
  const canEditDetails = ["pending", "confirmed"].includes(
    order.status
  );
  const paymentTone =
    order.payment_status === "paid"
      ? "text-green-400"
      : ["failed", "chargedback"].includes(order.payment_status)
        ? "text-red-400"
        : "text-yellow-400";
  const availableRefunds = payments.flatMap(
    (payment) => payment.refunds ?? []
  );

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
          {order.delivered_at && (
            <p className="text-sm text-gray-400 mt-1">
              Delivered {formatDate(order.delivered_at)}
            </p>
          )}
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
                <span>
                  Shipping
                  {order.shipping_method_name
                    ? ` (${order.shipping_method_name})`
                    : ""}
                </span>
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

          <OrderActivityTimeline
            events={activity}
            loading={activityLoading}
            error={activityError}
          />
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

            {canEditDetails && (
              <div className="mt-4 border-t border-gray-800 pt-4">
                {!editingDetails ? (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingDetails(true);
                      setDetailsError("");
                      setDetailsMessage("");
                    }}
                    className="w-full border border-cyan-500/50 text-cyan-400 py-2 rounded-lg font-semibold hover:bg-cyan-500/10 transition"
                  >
                    Edit order details
                  </button>
                ) : (
                  <OrderEditForm
                    key={order.id}
                    order={order}
                    onSave={handleSaveDetails}
                    onCancel={() => {
                      setEditingDetails(false);
                      setDetailsError("");
                    }}
                    saving={detailsSaving}
                    error={detailsError}
                  />
                )}
              </div>
            )}

            {detailsMessage && (
              <p className="text-sm text-green-400 mt-3">
                {detailsMessage}
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

                      <button
                        type="button"
                        onClick={() =>
                          handleProviderReconcile(payment)
                        }
                        disabled={providerVerifying === payment.id}
                        className="mt-3 w-full border border-cyan-500/50 text-cyan-400 py-2 rounded-lg text-xs font-semibold hover:bg-cyan-500/10 disabled:opacity-50"
                      >
                        {providerVerifying === payment.id
                          ? "Verifying with PayHere..."
                          : "Verify with PayHere"}
                      </button>

                      {payment.refunds.length > 0 && (
                        <div className="mt-3 border-t border-gray-800 pt-2 space-y-2">
                          <p className="text-xs font-medium text-gray-300">
                            Refunds / returns
                          </p>
                          {payment.refunds.map((refund) => (
                            <div
                              key={refund.id}
                              className="text-xs text-gray-400"
                            >
                              <p>
                                <span className="capitalize text-gray-300">
                                  {refund.kind}
                                </span>{" "}
                                · LKR {refund.amount} ·{" "}
                                <span className="capitalize">
                                  {refund.status}
                                </span>
                              </p>
                              <p>{refund.reason}</p>
                              {refund.provider_refund_id && (
                                <p className="break-all">
                                  Provider refund:{" "}
                                  {refund.provider_refund_id}
                                </p>
                              )}
                              {refund.status !== "refunded" && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleMarkRefunded(refund)
                                  }
                                  className="mt-1 text-cyan-400 hover:text-cyan-300"
                                >
                                  Mark refunded
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

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

                {providerError && (
                  <p className="text-sm text-red-400 mt-3">
                    {providerError}
                  </p>
                )}
                {providerMessage && (
                  <p className="text-sm text-green-400 mt-3">
                    {providerMessage}
                  </p>
                )}

                <form
                  onSubmit={handleReconcile}
                  className="mt-5 pt-4 border-t border-gray-800 space-y-3"
                >
                  <div>
                    <h4 className="text-sm font-semibold">
                      Manual reconciliation
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      If automatic verification is unavailable, verify
                      the transaction in the PayHere dashboard and
                      record the result here.
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

                <form
                  onSubmit={handleCreateRefund}
                  className="mt-5 pt-4 border-t border-gray-800 space-y-3"
                >
                  <div>
                    <h4 className="text-sm font-semibold">
                      Refund / return record
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Record a refund or return against a paid payment.
                      Provider processing requires the PayHere Merchant
                      API; otherwise record it manually.
                    </p>
                  </div>

                  <label className="block text-xs text-gray-300">
                    Payment attempt
                    <select
                      value={refundPaymentId}
                      onChange={(event) =>
                        setRefundPaymentId(event.target.value)
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

                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-xs text-gray-300">
                      Type
                      <select
                        value={refundKind}
                        onChange={(event) =>
                          setRefundKind(event.target.value)
                        }
                        className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                      >
                        <option value="refund">Refund</option>
                        <option value="return">Return</option>
                      </select>
                    </label>

                    <label className="block text-xs text-gray-300">
                      Amount (LKR)
                      <input
                        type="number"
                        min="1"
                        value={refundAmount}
                        onChange={(event) =>
                          setRefundAmount(event.target.value)
                        }
                        required
                        className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                      />
                    </label>
                  </div>

                  <label className="block text-xs text-gray-300">
                    Reason
                    <input
                      value={refundReason}
                      onChange={(event) =>
                        setRefundReason(event.target.value)
                      }
                      maxLength={300}
                      required
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    />
                  </label>

                  <label className="block text-xs text-gray-300">
                    Internal notes (optional)
                    <textarea
                      value={refundNotes}
                      onChange={(event) =>
                        setRefundNotes(event.target.value)
                      }
                      rows={2}
                      maxLength={1000}
                      className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                    />
                  </label>

                  <label className="flex items-start gap-2 text-xs text-gray-300">
                    <input
                      type="checkbox"
                      checked={processWithProvider}
                      onChange={(event) =>
                        setProcessWithProvider(event.target.checked)
                      }
                      className="mt-0.5 accent-cyan-400"
                    />
                    Process through PayHere Merchant API
                  </label>

                  {refundError && (
                    <p className="text-sm text-red-400">
                      {refundError}
                    </p>
                  )}
                  {refundMessage && (
                    <p className="text-sm text-green-400">
                      {refundMessage}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={refunding}
                    className="w-full bg-cyan-400 text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50"
                  >
                    {refunding
                      ? "Saving..."
                      : "Save refund / return"}
                  </button>
                </form>
              </>
            )}
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">Returns</h3>

            {returnsLoading ? (
              <p className="text-sm text-gray-400">
                Loading return requests...
              </p>
            ) : returnsError && returns.length === 0 ? (
              <p className="text-sm text-red-400">{returnsError}</p>
            ) : returns.length === 0 ? (
              <p className="text-sm text-gray-400">
                No return requests for this order.
              </p>
            ) : (
              <div className="space-y-4">
                {returns.map((request) => (
                  <div
                    key={request.id}
                    className="border border-gray-800 rounded-xl p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">
                        Return #{request.id}
                      </p>
                      <span
                        className={`text-xs capitalize ${
                          RETURN_STATUS_CLASSES[
                            request.status
                          ] ?? "text-gray-400"
                        }`}
                      >
                        {request.status}
                      </span>
                    </div>

                    {request.reason_code && (
                      <p className="text-xs text-cyan-400">
                        {RETURN_REASON_LABELS[
                          request.reason_code
                        ] ?? request.reason_code}
                      </p>
                    )}
                    <p className="text-sm text-gray-300">
                      {request.reason}
                    </p>
                    {request.items?.length > 0 && (
                      <ul className="space-y-1">
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
                    {request.stock_restocked_at && (
                      <p className="text-xs text-green-400">
                        Items restocked{" "}
                        {formatDate(request.stock_restocked_at)}
                      </p>
                    )}
                    {request.notes && (
                      <p className="text-xs text-gray-500">
                        {request.notes}
                      </p>
                    )}
                    {request.review_note && (
                      <p className="text-xs text-gray-400">
                        Review note: {request.review_note}
                      </p>
                    )}

                    {request.status === "requested" && (
                      <div className="space-y-2 pt-2 border-t border-gray-800">
                        <label className="block text-xs text-gray-300">
                          Review note (optional)
                          <input
                            value={returnReviewNote}
                            onChange={(event) =>
                              setReturnReviewNote(
                                event.target.value
                              )
                            }
                            maxLength={500}
                            className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                          />
                        </label>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            disabled={returnActionId === request.id}
                            onClick={() =>
                              handleReviewReturn(
                                request.id,
                                "approved"
                              )
                            }
                            className="flex-1 bg-cyan-400 text-black py-2 rounded-lg text-sm font-semibold hover:bg-cyan-300 disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            disabled={returnActionId === request.id}
                            onClick={() =>
                              handleReviewReturn(
                                request.id,
                                "rejected"
                              )
                            }
                            className="flex-1 border border-red-500/60 text-red-400 py-2 rounded-lg text-sm font-semibold hover:bg-red-500/10 disabled:opacity-50"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    )}

                    {request.status === "approved" && (
                      <div className="space-y-1 pt-2 border-t border-gray-800">
                        <button
                          type="button"
                          disabled={returnActionId === request.id}
                          onClick={() =>
                            handleReviewReturn(
                              request.id,
                              "completed"
                            )
                          }
                          className="w-full bg-cyan-400 text-black py-2 rounded-lg text-sm font-semibold hover:bg-cyan-300 disabled:opacity-50"
                        >
                          {returnActionId === request.id
                            ? "Completing..."
                            : "Mark completed & restock"}
                        </button>
                        <p className="text-xs text-gray-500">
                          Only complete this after the returned items
                          have been received.
                        </p>
                      </div>
                    )}

                    {["approved", "completed"].includes(
                      request.status
                    ) &&
                      !request.refund_id && (
                        <div className="space-y-2 pt-2 border-t border-gray-800">
                          {availableRefunds.length > 0 ? (
                            <>
                              <label className="block text-xs text-gray-300">
                                Link a refund
                                <select
                                  value={
                                    linkRefundId ||
                                    String(
                                      availableRefunds[0]?.id ?? ""
                                    )
                                  }
                                  onChange={(event) =>
                                    setLinkRefundId(
                                      event.target.value
                                    )
                                  }
                                  className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm"
                                >
                                  {availableRefunds.map(
                                    (refund) => (
                                      <option
                                        key={refund.id}
                                        value={refund.id}
                                      >
                                        Refund #{refund.id} · LKR{" "}
                                        {refund.amount} ·{" "}
                                        {refund.status}
                                      </option>
                                    )
                                  )}
                                </select>
                              </label>
                              <button
                                type="button"
                                onClick={() =>
                                  handleLinkReturnRefund(
                                    request.id
                                  )
                                }
                                className="w-full border border-cyan-500/50 text-cyan-400 py-2 rounded-lg text-xs font-semibold hover:bg-cyan-500/10"
                              >
                                Link refund
                              </button>
                            </>
                          ) : (
                            <p className="text-xs text-yellow-400">
                              Create a refund in Payment history
                              before linking it.
                            </p>
                          )}
                        </div>
                      )}

                    {request.refund && (
                      <p className="text-xs text-cyan-400">
                        Linked refund #{request.refund.id} · LKR{" "}
                        {request.refund.amount} ·{" "}
                        {request.refund.status}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {returnsError && returns.length > 0 && (
              <p className="text-sm text-red-400 mt-3">
                {returnsError}
              </p>
            )}
            {returnMessage && (
              <p className="text-sm text-green-400 mt-3">
                {returnMessage}
              </p>
            )}
          </section>

          <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-3">
              Edit history
            </h3>

            {auditLoading ? (
              <p className="text-sm text-gray-400">
                Loading edit history...
              </p>
            ) : auditError ? (
              <p className="text-sm text-red-400">
                {auditError}
              </p>
            ) : audit.length === 0 ? (
              <p className="text-sm text-gray-400">
                No customer or shipping edits recorded.
              </p>
            ) : (
              <div className="space-y-4">
                {audit.map((event) => (
                  <div
                    key={event.id}
                    className="border border-gray-800 rounded-xl p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium">
                        {event.action === "details_edited"
                          ? "Details edited"
                          : event.action}
                      </p>
                      <p className="text-xs text-gray-500 shrink-0">
                        {formatDate(event.created_at)}
                      </p>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {event.actor_user_id
                        ? `Admin #${event.actor_user_id}`
                        : "System"}
                    </p>

                    {Object.entries(event.changes ?? {})
                      .length > 0 && (
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        {Object.entries(event.changes).map(
                          ([field, change]) => (
                            <li
                              key={field}
                              className="break-words"
                            >
                              <span className="text-gray-300">
                                {ORDER_FIELD_LABELS[field] ??
                                  field}
                              </span>
                              :{" "}
                              <span className="text-gray-500">
                                {change.from || "—"}
                              </span>{" "}
                              →{" "}
                              <span>{change.to || "—"}</span>
                            </li>
                          )
                        )}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
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
