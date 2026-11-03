import client from "./client";

export async function createOrder(payload) {
  const { data } = await client.post("/orders", payload);
  return data;
}

export async function getOrders() {
  const { data } = await client.get("/orders");
  return data;
}

export async function getOrder(orderId) {
  const { data } = await client.get(`/orders/${orderId}`);
  return data;
}
