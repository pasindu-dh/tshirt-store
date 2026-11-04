import client from "./client";

export async function getAdminOrders(params = {}) {
  const { data, headers } = await client.get("/admin/orders", {
    params,
  });

  return {
    orders: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getAdminOrder(orderId) {
  const { data } = await client.get(`/admin/orders/${orderId}`);
  return data;
}

export async function getAdminOrderPayments(orderId) {
  const { data } = await client.get(
    `/admin/orders/${orderId}/payments`
  );
  return data;
}

export async function reconcileAdminPayment(
  orderId,
  paymentId,
  payload
) {
  const { data } = await client.post(
    `/admin/orders/${orderId}/payments/${paymentId}/reconcile`,
    payload
  );
  return data;
}

export async function reconcileAdminPaymentWithProvider(
  orderId,
  paymentId
) {
  const { data } = await client.post(
    `/admin/orders/${orderId}/payments/${paymentId}/reconcile-provider`
  );
  return data;
}

export async function getAdminOrderRefunds(orderId) {
  const { data } = await client.get(
    `/admin/orders/${orderId}/refunds`
  );
  return data;
}

export async function createAdminRefund(
  orderId,
  paymentId,
  payload
) {
  const { data } = await client.post(
    `/admin/orders/${orderId}/payments/${paymentId}/refunds`,
    payload
  );
  return data;
}

export async function updateAdminRefund(
  orderId,
  refundId,
  payload
) {
  const { data } = await client.patch(
    `/admin/orders/${orderId}/refunds/${refundId}`,
    payload
  );
  return data;
}

export async function getAdminOrderReturns(orderId) {
  const { data } = await client.get(
    `/admin/orders/${orderId}/returns`
  );
  return data;
}

export async function reviewAdminOrderReturn(
  orderId,
  returnId,
  payload
) {
  const { data } = await client.patch(
    `/admin/orders/${orderId}/returns/${returnId}`,
    payload
  );
  return data;
}

export async function linkAdminReturnRefund(
  orderId,
  returnId,
  refundId
) {
  const { data } = await client.patch(
    `/admin/orders/${orderId}/returns/${returnId}/refund`,
    { refund_id: refundId }
  );
  return data;
}

export async function updateAdminOrderStatus(orderId, status) {
  const { data } = await client.patch(
    `/admin/orders/${orderId}/status`,
    { status }
  );
  return data;
}

export async function getAdminStats() {
  const { data } = await client.get("/admin/stats");
  return data;
}
