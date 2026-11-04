import client from "./client";

async function uploadCatalogCsv(file, dryRun) {
  const form = new FormData();
  form.append("file", file);

  const { data } = await client.post(
    "/admin/products/import",
    form,
    { params: { dry_run: dryRun } }
  );
  return data;
}

export function previewCatalogImport(file) {
  return uploadCatalogCsv(file, true);
}

export function applyCatalogImport(file) {
  return uploadCatalogCsv(file, false);
}
