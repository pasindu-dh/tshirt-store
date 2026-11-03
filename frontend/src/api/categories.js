import client from "./client";

export async function getCategories() {
  const { data } = await client.get("/categories");
  return data;
}

export async function createCategory(name) {
  const { data } = await client.post("/admin/categories", { name });
  return data;
}

export async function updateCategory(categoryId, name) {
  const { data } = await client.put(`/admin/categories/${categoryId}`, {
    name,
  });
  return data;
}

export async function deleteCategory(categoryId) {
  await client.delete(`/admin/categories/${categoryId}`);
}
