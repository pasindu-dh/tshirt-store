import client from "./client";

export async function getAdminCoupons() {
  const { data } = await client.get("/admin/coupons");
  return data;
}

export async function createAdminCoupon(payload) {
  const { data } = await client.post("/admin/coupons", payload);
  return data;
}

export async function updateAdminCoupon(couponId, payload) {
  const { data } = await client.put(
    `/admin/coupons/${couponId}`,
    payload
  );
  return data;
}

export async function deleteAdminCoupon(couponId) {
  await client.delete(`/admin/coupons/${couponId}`);
}
