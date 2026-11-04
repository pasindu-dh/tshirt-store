import client from "./client";

function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

async function downloadCsv(path, params, name) {
  const { data } = await client.get(path, {
    params,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `furzy-${name}-${dateStamp()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function downloadOrdersCsv(params = {}) {
  return downloadCsv("/admin/exports/orders.csv", params, "orders");
}

export function downloadCustomersCsv(params = {}) {
  return downloadCsv(
    "/admin/exports/customers.csv",
    params,
    "customers"
  );
}

export function downloadReturnsCsv(params = {}) {
  return downloadCsv("/admin/exports/returns.csv", params, "returns");
}

export function downloadRefundsCsv(params = {}) {
  return downloadCsv("/admin/exports/refunds.csv", params, "refunds");
}

export function downloadStockMovementsCsv(params = {}) {
  return downloadCsv(
    "/admin/exports/stock-movements.csv",
    params,
    "stock-movements"
  );
}

export function downloadFinancialCsv(params = {}) {
  return downloadCsv(
    "/admin/exports/financial.csv",
    params,
    "financial"
  );
}
