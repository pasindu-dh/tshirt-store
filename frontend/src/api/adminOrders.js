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
