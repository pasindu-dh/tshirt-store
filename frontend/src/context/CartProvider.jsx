import { useCallback, useEffect, useRef, useState } from "react";
import {
  addCartItem as addServerCartItem,
  clearCart as clearServerCart,
  getCart as getServerCart,
  mergeCart as mergeServerCart,
  removeCartItem as removeServerCartItem,
  updateCartItem as updateServerCartItem,
} from "../api/cart";
import useAuth from "../hooks/useAuth";
import { getCartKey, normalizeCartItem } from "../utils/cart";
import { getApiError } from "../utils/errors";
import CartContext from "./CartContext";

const STORAGE_KEY = "cart";

function readStoredCart() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    return Array.isArray(parsed) ? parsed.map(normalizeCartItem) : [];
  } catch {
    return [];
  }
}

function mapServerItem(item) {
  return {
    key: getCartKey(item.product_id, item.variant_id),
    serverItemId: item.id,
    productId: item.product_id,
    variantId: item.variant_id,
    id: item.product_id,
    name: item.product_name,
    price: item.price,
    image: item.image,
    size: item.size,
    color: item.color,
    sku: item.sku,
    stock: item.stock,
    quantity: item.quantity,
  };
}

export default function CartProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [cart, setCart] = useState(readStoredCart);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [cartLoading, setCartLoading] = useState(false);
  const [cartSynced, setCartSynced] = useState(false);
  const [serverTotals, setServerTotals] = useState({
    shippingFee: 0,
    total: 0,
  });
  const syncedUserIdRef = useRef(null);

  const applyServerCart = useCallback((data) => {
    setCart(data.items.map(mapServerItem));
    setServerTotals({
      shippingFee: data.shipping_fee,
      total: data.total,
    });
  }, []);

  const refreshServerCart = useCallback(async () => {
    try {
      const data = await getServerCart();
      applyServerCart(data);
    } catch {
      // Keep the current cart if the refresh fails.
    }
  }, [applyServerCart]);

  useEffect(() => {
    if (authLoading) return;

    const userId = user?.id ?? null;
    const previousUserId = syncedUserIdRef.current;

    if (previousUserId === userId) return;

    syncedUserIdRef.current = userId;
    let cancelled = false;

    async function syncAuthCart() {
      if (!userId) {
        setCartSynced(false);

        if (previousUserId !== null) {
          setCart([]);
          setServerTotals({ shippingFee: 0, total: 0 });
          try {
            localStorage.removeItem(STORAGE_KEY);
          } catch {
            // Ignore unavailable storage.
          }
        }
        setCartLoading(false);
        return;
      }

      setCartSynced(false);
      setCartLoading(true);

      try {
        const guestItems = readStoredCart()
          .filter((item) => item.variantId)
          .map((item) => ({
            variant_id: item.variantId,
            quantity: item.quantity,
          }));

        const data =
          guestItems.length > 0
            ? await mergeServerCart(guestItems)
            : await getServerCart();

        if (cancelled) return;

        applyServerCart(data);

        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          // Ignore unavailable storage.
        }
      } catch {
        if (!cancelled) {
          setCart([]);
          setServerTotals({ shippingFee: 0, total: 0 });
        }
      } finally {
        if (!cancelled) {
          setCartLoading(false);
          setCartSynced(true);
        }
      }
    }

    const timeout = setTimeout(syncAuthCart, 0);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [user, authLoading, applyServerCart]);

  useEffect(() => {
    if (user) return;

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch {
      // Storage can be unavailable (e.g. private mode).
    }
  }, [cart, user]);

  const addToCart = async (product, variant = null) => {
    if (user) {
      if (!variant) return false;

      try {
        const data = await addServerCartItem(variant.id, 1);
        applyServerCart(data);
        return true;
      } catch (error) {
        throw new Error(
          getApiError(error, "Could not add to cart.")
        );
      }
    }

    if (variant && variant.stock <= 0) {
      return false;
    }

    const variantId = variant?.id ?? null;
    const key = getCartKey(product.id, variantId);
    const maxStock = variant?.stock ?? Infinity;
    const existing = cart.find((item) => item.key === key);

    if (existing && existing.quantity >= (existing.stock ?? maxStock)) {
      return false;
    }

    setCart((current) => {
      const currentItem = current.find((item) => item.key === key);

      if (currentItem) {
        const stock = currentItem.stock ?? maxStock;

        if (currentItem.quantity >= stock) {
          return current;
        }

        return current.map((item) =>
          item.key === key
            ? {
                ...item,
                quantity: item.quantity + 1,
                stock: variant?.stock ?? item.stock,
              }
            : item
        );
      }

      return [
        ...current,
        {
          key,
          productId: product.id,
          variantId,
          id: product.id,
          name: product.name,
          price: product.price,
          image: product.image,
          size: variant?.size ?? null,
          color: variant?.color ?? null,
          sku: variant?.sku ?? null,
          stock: variant?.stock ?? null,
          quantity: 1,
        },
      ];
    });

    return true;
  };

  const increaseQty = async (key) => {
    if (user) {
      const item = cart.find((current) => current.key === key);

      if (!item?.serverItemId) return;

      try {
        const data = await updateServerCartItem(
          item.serverItemId,
          item.quantity + 1
        );
        applyServerCart(data);
      } catch {
        await refreshServerCart();
      }
      return;
    }

    setCart((current) =>
      current.map((item) => {
        if (item.key !== key) return item;

        const maxStock = item.stock ?? Infinity;

        if (item.quantity >= maxStock) {
          return item;
        }

        return { ...item, quantity: item.quantity + 1 };
      })
    );
  };

  const decreaseQty = async (key) => {
    if (user) {
      const item = cart.find((current) => current.key === key);

      if (!item?.serverItemId) return;

      try {
        const data =
          item.quantity <= 1
            ? await removeServerCartItem(item.serverItemId)
            : await updateServerCartItem(
                item.serverItemId,
                item.quantity - 1
              );
        applyServerCart(data);
      } catch {
        await refreshServerCart();
      }
      return;
    }

    setCart((current) =>
      current
        .map((item) =>
          item.key === key
            ? { ...item, quantity: item.quantity - 1 }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const removeItem = async (key) => {
    if (user) {
      const item = cart.find((current) => current.key === key);

      if (!item?.serverItemId) return;

      try {
        const data = await removeServerCartItem(item.serverItemId);
        applyServerCart(data);
      } catch {
        await refreshServerCart();
      }
      return;
    }

    setCart((current) =>
      current.filter((item) => item.key !== key)
    );
  };

  const clearCart = async () => {
    if (user) {
      try {
        const data = await clearServerCart();
        applyServerCart(data);
      } catch {
        setCart([]);
        setServerTotals({ shippingFee: 0, total: 0 });
      }
      return;
    }

    setCart([]);
  };

  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const cartTotal = cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );
  const shippingFee = user ? serverTotals.shippingFee : 0;
  const grandTotal = user ? serverTotals.total : cartTotal;
  const isCartLoading =
    cartLoading || (Boolean(user) && !cartSynced);

  const value = {
    cart,
    addToCart,
    increaseQty,
    decreaseQty,
    removeItem,
    clearCart,
    cartCount,
    cartTotal,
    shippingFee,
    grandTotal,
    cartLoading: isCartLoading,
    isCartOpen,
    openCart: () => setIsCartOpen(true),
    closeCart: () => setIsCartOpen(false),
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
