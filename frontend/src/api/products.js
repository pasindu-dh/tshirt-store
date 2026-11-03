import client from "./client";

export async function getProducts({ page = 1, limit = 6 } = {}) {
  const { data } = await client.get("/products", {
    params: { page, limit },
  });

  return data;
}
