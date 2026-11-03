import client from "./client";

export async function getWishlist() {
  const { data } = await client.get("/wishlist");
  return data;
}

export async function addWishlistItem(productId) {
  const { data } = await client.put(
    `/wishlist/items/${productId}`
  );
  return data;
}

export async function removeWishlistItem(productId) {
  await client.delete(`/wishlist/items/${productId}`);
}
