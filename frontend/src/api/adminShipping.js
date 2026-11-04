import client from "./client";

export async function getAdminShippingMethods() {
  const { data } = await client.get(
    "/admin/shipping-methods"
  );
  return data;
}

export async function createAdminShippingMethod(payload) {
  const { data } = await client.post(
    "/admin/shipping-methods",
    payload
  );
  return data;
}

export async function updateAdminShippingMethod(
  methodId,
  payload
) {
  const { data } = await client.patch(
    `/admin/shipping-methods/${methodId}`,
    payload
  );
  return data;
}

export async function deleteAdminShippingMethod(methodId) {
  await client.delete(
    `/admin/shipping-methods/${methodId}`
  );
}
