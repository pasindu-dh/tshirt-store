import client from "./client";

export async function getAdminCustomers(params = {}) {
  const { data, headers } = await client.get("/admin/customers", {
    params,
  });

  return {
    customers: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getAdminCustomer(customerId) {
  const { data } = await client.get(
    `/admin/customers/${customerId}`
  );
  return data;
}
