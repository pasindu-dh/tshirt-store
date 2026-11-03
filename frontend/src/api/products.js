import client from "./client";

export async function getProducts({
  page = 1,
  limit = 6,
  search,
  category,
  sort,
} = {}) {
  const params = { page, limit };

  if (search) params.search = search;
  if (category) params.category = category;
  if (sort) params.sort = sort;

  const { data, headers } = await client.get("/products", { params });

  return {
    products: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getProductBySlug(slug) {
  const { data } = await client.get(
    `/products/slug/${encodeURIComponent(slug)}`
  );
  return data;
}
