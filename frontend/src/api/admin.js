import client from "./client";

export async function getAdminProducts(params = {}) {
  const { data, headers } = await client.get("/admin/products", { params });

  return {
    products: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getAdminProduct(productId) {
  const { data } = await client.get(`/admin/products/${productId}`);
  return data;
}

export async function createAdminProduct(payload) {
  const { data } = await client.post("/admin/products", payload);
  return data;
}

export async function updateAdminProduct(productId, payload) {
  const { data } = await client.put(`/admin/products/${productId}`, payload);
  return data;
}

export async function deleteAdminProduct(productId) {
  await client.delete(`/admin/products/${productId}`);
}

export async function uploadProductImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post("/admin/uploads", formData);
  return data;
}
