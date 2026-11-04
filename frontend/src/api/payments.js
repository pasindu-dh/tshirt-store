import client from "./client";

export async function getPaymentConfig() {
  const { data } = await client.get("/payments/config");
  return data;
}

export async function createPaymentSession(orderId) {
  const { data } = await client.post(
    `/payments/orders/${orderId}/session`
  );
  return data;
}

export async function completeMockPayment(orderId) {
  const { data } = await client.post(
    `/payments/orders/${orderId}/mock-complete`
  );
  return data;
}

export function submitPayHereCheckout(session) {
  if (!session?.action_url || !session?.fields) {
    throw new Error("The payment provider did not return a checkout form.");
  }

  const form = document.createElement("form");
  form.method = "POST";
  form.action = session.action_url;
  form.style.display = "none";

  Object.entries(session.fields).forEach(([name, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  });

  document.body.appendChild(form);
  form.submit();
}
