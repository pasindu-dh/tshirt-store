export function getCartKey(productId, variantId = null) {
  return `${productId}:${variantId ?? "default"}`;
}

export function normalizeCartItem(item) {
  const productId = item.productId ?? item.id;
  const variantId = item.variantId ?? null;

  return {
    ...item,
    productId,
    variantId,
    key: item.key ?? getCartKey(productId, variantId),
  };
}
