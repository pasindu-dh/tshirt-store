import client from "./client";

export async function getCart() {
  const { data } = await client.get("/cart");
  return data;
}

export async function addCartItem(variantId, quantity = 1) {
  const { data } = await client.post("/cart/items", {
    variant_id: variantId,
    quantity,
  });
  return data;
}

export async function updateCartItem(itemId, quantity) {
  const { data } = await client.put(`/cart/items/${itemId}`, {
    quantity,
  });
  return data;
}

export async function removeCartItem(itemId) {
  const { data } = await client.delete(`/cart/items/${itemId}`);
  return data;
}

export async function clearCart() {
  const { data } = await client.delete("/cart");
  return data;
}

export async function mergeCart(items) {
  const { data } = await client.post("/cart/merge", { items });
  return data;
}
