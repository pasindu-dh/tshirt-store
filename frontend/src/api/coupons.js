import client from "./client";

export async function previewCoupon(code) {
  const { data } = await client.post("/coupons/preview", {
    code,
  });
  return data;
}
