import client from "./client";

export async function getProductReviews(productId) {
  const { data } = await client.get(
    `/reviews/product/${productId}`
  );
  return data;
}

export async function createReview(productId, payload) {
  const { data } = await client.post(
    `/reviews/product/${productId}`,
    payload
  );
  return data;
}

export async function updateReview(reviewId, payload) {
  const { data } = await client.put(
    `/reviews/${reviewId}`,
    payload
  );
  return data;
}

export async function deleteReview(reviewId) {
  await client.delete(`/reviews/${reviewId}`);
}
