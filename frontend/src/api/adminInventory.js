import client from "./client";

export async function getLowStock(params = {}) {
  const { data, headers } = await client.get(
    "/admin/inventory/low-stock",
    { params }
  );

  return {
    variants: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getStockMovements(params = {}) {
  const { data, headers } = await client.get(
    "/admin/inventory/movements",
    { params }
  );

  return {
    movements: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function adjustStock(variantId, payload) {
  const { data } = await client.post(
    `/admin/inventory/variants/${variantId}/adjust`,
    payload
  );
  return data;
}
