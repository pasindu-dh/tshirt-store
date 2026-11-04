import client from "./client";

export async function getAdminRefunds(params = {}) {
  const { data, headers } = await client.get(
    "/admin/refunds",
    { params }
  );

  return {
    refunds: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}
