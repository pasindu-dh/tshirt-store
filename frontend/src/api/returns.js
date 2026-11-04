import client from "./client";

export async function getOrderReturns(orderId) {
  const { data } = await client.get(
    `/orders/${orderId}/returns`
  );
  return data;
}

export async function createOrderReturn(orderId, payload) {
  const { data } = await client.post(
    `/orders/${orderId}/returns`,
    payload
  );
  return data;
}

export async function cancelOrderReturn(orderId, returnId) {
  const { data } = await client.post(
    `/orders/${orderId}/returns/${returnId}/cancel`
  );
  return data;
}
