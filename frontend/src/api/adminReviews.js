import client from "./client";

export async function getAdminReviews({
  page = 1,
  limit = 20,
  status,
  search,
  rating,
} = {}) {
  const params = { page, limit };

  if (status) params.status = status;
  if (search) params.search = search;
  if (rating) params.rating = rating;

  const { data, headers } = await client.get("/admin/reviews", {
    params,
  });

  return {
    reviews: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function updateAdminReviewStatus(reviewId, status) {
  const { data } = await client.patch(
    `/admin/reviews/${reviewId}`,
    { status }
  );
  return data;
}

export async function deleteAdminReview(reviewId) {
  await client.delete(`/admin/reviews/${reviewId}`);
}
