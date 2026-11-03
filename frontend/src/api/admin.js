import client from "./client";

export async function getAdminProducts(params = {}) {
  const { data, headers } = await client.get("/admin/products", { params });

  return {
    products: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}
