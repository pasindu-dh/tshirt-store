import client from "./client";

export async function getShippingMethods() {
  const { data } = await client.get("/shipping-methods");
  return data;
}
