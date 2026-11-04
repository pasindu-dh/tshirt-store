import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { downloadStockMovementsCsv } from "../../api/adminExports";
import {
  adjustStock,
  getLowStock,
  getStockMovements,
} from "../../api/adminInventory";
import ExportCsvButton from "../../components/admin/ExportCsvButton";
import { getApiError } from "../../utils/errors";

const MOVEMENT_PAGE_SIZE = 20;
const MOVEMENT_TYPE_OPTIONS = [
  { value: "", label: "All movements" },
  { value: "order_placed", label: "Order placed" },
  { value: "order_cancelled", label: "Order cancelled" },
  {
    value: "reservation_expired",
    label: "Reservation expired",
  },
  { value: "return_restocked", label: "Return restocked" },
  { value: "manual_adjustment", label: "Manual adjustment" },
  { value: "initial_stock", label: "Initial stock" },
  { value: "variant_removed", label: "Variant removed" },
  { value: "product_deleted", label: "Product deleted" },
];
const MOVEMENT_LABELS = Object.fromEntries(
  MOVEMENT_TYPE_OPTIONS.filter((option) => option.value).map(
    (option) => [option.value, option.label]
  )
);

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AdminInventory() {
  const [lowStock, setLowStock] = useState([]);
  const [lowTotal, setLowTotal] = useState(0);
  const [lowSearch, setLowSearch] = useState("");
  const [appliedLowSearch, setAppliedLowSearch] = useState("");
  const lowSearchRef = useRef("");
  const [lowLoading, setLowLoading] = useState(true);
  const [lowError, setLowError] = useState("");
  const [lowRefreshKey, setLowRefreshKey] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [adjustDelta, setAdjustDelta] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjusting, setAdjusting] = useState(false);
  const [adjustError, setAdjustError] = useState("");
  const [adjustMessage, setAdjustMessage] = useState("");

  const [movements, setMovements] = useState([]);
  const [movementTotal, setMovementTotal] = useState(0);
  const [movementPage, setMovementPage] = useState(1);
  const [movementType, setMovementType] = useState("");
  const [movementSearch, setMovementSearch] = useState("");
  const [appliedMovementSearch, setAppliedMovementSearch] =
    useState("");
  const movementSearchRef = useRef("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [movementLoading, setMovementLoading] = useState(true);
  const [movementError, setMovementError] = useState("");
  const [movementRefreshKey, setMovementRefreshKey] =
    useState(0);

  const resetMovements = useCallback(() => {
    setMovementPage(1);
    setMovements([]);
    setMovementTotal(0);
    setMovementError("");
    setMovementLoading(true);
  }, []);

  useEffect(() => {
    const trimmed = lowSearch.trim();
    const timeout = setTimeout(() => {
      if (lowSearchRef.current === trimmed) return;

      lowSearchRef.current = trimmed;
      setAppliedLowSearch(trimmed);
      setLowLoading(true);
      setLowError("");
    }, 300);

    return () => clearTimeout(timeout);
  }, [lowSearch]);

  useEffect(() => {
    let cancelled = false;

    getLowStock({
      search: appliedLowSearch || undefined,
      limit: 100,
    })
      .then((result) => {
        if (cancelled) return;

        setLowStock(result.variants);
        setLowTotal(result.total);
        setLowError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setLowError(
            getApiError(
              requestError,
              "Could not load low-stock variants."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLowLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [appliedLowSearch, lowRefreshKey]);

  useEffect(() => {
    const trimmed = movementSearch.trim();
    const timeout = setTimeout(() => {
      if (movementSearchRef.current === trimmed) return;

      movementSearchRef.current = trimmed;
      setAppliedMovementSearch(trimmed);
      resetMovements();
    }, 300);

    return () => clearTimeout(timeout);
  }, [movementSearch, resetMovements]);

  useEffect(() => {
    let cancelled = false;

    getStockMovements({
      page: movementPage,
      limit: MOVEMENT_PAGE_SIZE,
      movement_type: movementType || undefined,
      search: appliedMovementSearch || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setMovements(result.movements);
        setMovementTotal(result.total);
        setMovementError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setMovementError(
            getApiError(
              requestError,
              "Could not load stock movements."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setMovementLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    movementPage,
    movementType,
    appliedMovementSearch,
    dateFrom,
    dateTo,
    movementRefreshKey,
  ]);

  const handleMovementTypeChange = (event) => {
    setMovementType(event.target.value);
    resetMovements();
  };

  const handleDateChange = (setter) => (event) => {
    setter(event.target.value);
    resetMovements();
  };

  const startAdjustment = (variant) => {
    setSelectedVariant(variant);
    setAdjustDelta("");
    setAdjustReason("");
    setAdjustError("");
    setAdjustMessage("");
  };

  const cancelAdjustment = () => {
    setSelectedVariant(null);
    setAdjustDelta("");
    setAdjustReason("");
    setAdjustError("");
  };

  const handleAdjust = async (event) => {
    event.preventDefault();
    setAdjustError("");
    setAdjustMessage("");

    if (!selectedVariant) return;

    const delta = Number(adjustDelta);

    if (!Number.isInteger(delta) || delta === 0) {
      setAdjustError(
        "Enter a non-zero whole-number stock change."
      );
      return;
    }

    if (adjustReason.trim().length < 3) {
      setAdjustError("Describe why the stock is being adjusted.");
      return;
    }

    setAdjusting(true);

    try {
      const result = await adjustStock(selectedVariant.id, {
        quantity_delta: delta,
        reason: adjustReason.trim(),
      });
      setAdjustMessage(
        `Stock updated for ${result.variant.product_name} (${result.variant.size}/${result.variant.color}): ${result.movement.stock_before} → ${result.movement.stock_after}.`
      );
      setSelectedVariant(null);
      setAdjustDelta("");
      setAdjustReason("");
      setLowRefreshKey((current) => current + 1);
      setMovementRefreshKey((current) => current + 1);
    } catch (requestError) {
      setAdjustError(
        getApiError(requestError, "Could not adjust stock.")
      );
    } finally {
      setAdjusting(false);
    }
  };

  const movementPages = Math.max(
    1,
    Math.ceil(movementTotal / MOVEMENT_PAGE_SIZE)
  );

  return (
    <div>
      <div>
        <h2 className="text-2xl font-bold">Inventory</h2>
        <p className="text-gray-400 text-sm mt-1">
          Low-stock alerts and a full history of stock changes.
        </p>
      </div>

      <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Low stock</h3>
            <p className="text-sm text-gray-400 mt-1">
              Active variants at or below their alert threshold.
            </p>
          </div>
          <span className="text-sm text-gray-400">
            {lowTotal} variant{lowTotal === 1 ? "" : "s"}
          </span>
        </div>

        <input
          value={lowSearch}
          onChange={(event) => setLowSearch(event.target.value)}
          placeholder="Search by product, SKU, size, or color"
          aria-label="Search low-stock variants"
          className="mt-4 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
        />

        {adjustMessage && (
          <p className="text-sm text-green-400 mt-3">
            {adjustMessage}
          </p>
        )}

        {selectedVariant && (
          <form
            onSubmit={handleAdjust}
            className="mt-4 border border-cyan-500/40 rounded-xl p-4 space-y-3"
          >
            <div>
              <p className="font-semibold">
                Adjust {selectedVariant.product_name}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {selectedVariant.size} / {selectedVariant.color} ·{" "}
                {selectedVariant.sku} · current stock{" "}
                {selectedVariant.stock}
              </p>
            </div>

            <div className="grid sm:grid-cols-[160px_1fr] gap-3">
              <label className="block text-xs text-gray-300">
                Change (+/−)
                <input
                  type="number"
                  step="1"
                  value={adjustDelta}
                  onChange={(event) =>
                    setAdjustDelta(event.target.value)
                  }
                  aria-label="Stock adjustment quantity"
                  className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
                />
              </label>

              <label className="block text-xs text-gray-300">
                Reason
                <input
                  value={adjustReason}
                  onChange={(event) =>
                    setAdjustReason(event.target.value)
                  }
                  maxLength={300}
                  aria-label="Stock adjustment reason"
                  placeholder="Cycle count, damaged stock, restock..."
                  className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
                />
              </label>
            </div>

            {adjustError && (
              <p className="text-sm text-red-400">{adjustError}</p>
            )}

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={adjusting}
                className="bg-cyan-400 text-black px-4 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-300 disabled:opacity-50"
              >
                {adjusting ? "Saving..." : "Save adjustment"}
              </button>
              <button
                type="button"
                onClick={cancelAdjustment}
                className="border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {lowError ? (
          <p className="text-sm text-red-400 mt-4">{lowError}</p>
        ) : lowLoading ? (
          <p className="text-sm text-gray-400 mt-4">
            Loading low-stock variants...
          </p>
        ) : lowStock.length === 0 ? (
          <p className="text-sm text-gray-400 mt-4">
            No active variants are at or below their threshold.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead className="text-left text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="py-2 pr-4">Product</th>
                  <th className="py-2 pr-4">Variant</th>
                  <th className="py-2 pr-4">Stock</th>
                  <th className="py-2 pr-4">Alert at</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {lowStock.map((variant) => (
                  <tr
                    key={variant.id}
                    className="border-b border-gray-800/60 last:border-0"
                  >
                    <td className="py-3 pr-4">
                      <p className="text-gray-200">
                        {variant.product_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {variant.sku}
                      </p>
                    </td>
                    <td className="py-3 pr-4 text-gray-300">
                      {variant.size} / {variant.color}
                    </td>
                    <td
                      className={`py-3 pr-4 font-semibold ${
                        variant.stock === 0
                          ? "text-red-400"
                          : "text-yellow-400"
                      }`}
                    >
                      {variant.stock}
                    </td>
                    <td className="py-3 pr-4 text-gray-400">
                      {variant.low_stock_threshold}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        type="button"
                        onClick={() => startAdjustment(variant)}
                        className="text-cyan-400 hover:text-cyan-300"
                      >
                        Adjust
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">
              Stock movement history
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              Orders, cancellations, expiries, returns, and admin
              adjustments.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">
              {movementTotal} movement
              {movementTotal === 1 ? "" : "s"}
            </span>
            <ExportCsvButton
              label="Export movements CSV"
              onExport={() =>
                downloadStockMovementsCsv({
                  movement_type: movementType || undefined,
                  search: appliedMovementSearch || undefined,
                  date_from: dateFrom || undefined,
                  date_to: dateTo || undefined,
                })
              }
            />
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          <input
            value={movementSearch}
            onChange={(event) =>
              setMovementSearch(event.target.value)
            }
            placeholder="Search product, SKU, or reason"
            aria-label="Search stock movements"
            className="p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
          />

          <select
            value={movementType}
            onChange={handleMovementTypeChange}
            aria-label="Filter by movement type"
            className="p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
          >
            {MOVEMENT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <input
            type="date"
            value={dateFrom}
            onChange={handleDateChange(setDateFrom)}
            aria-label="Movements from date"
            className="p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
          />

          <input
            type="date"
            value={dateTo}
            onChange={handleDateChange(setDateTo)}
            aria-label="Movements to date"
            className="p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
          />
        </div>

        {movementError ? (
          <p className="text-sm text-red-400 mt-4">
            {movementError}
          </p>
        ) : movementLoading ? (
          <p className="text-sm text-gray-400 mt-4">
            Loading stock movements...
          </p>
        ) : movements.length === 0 ? (
          <p className="text-sm text-gray-400 mt-4">
            No stock movements match these filters.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm min-w-[960px]">
              <thead className="text-left text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Type</th>
                  <th className="py-2 pr-4">Product</th>
                  <th className="py-2 pr-4">Change</th>
                  <th className="py-2 pr-4">Stock</th>
                  <th className="py-2 pr-4">Reference</th>
                  <th className="py-2 pr-4">By</th>
                </tr>
              </thead>
              <tbody>
                {movements.map((movement) => (
                  <tr
                    key={movement.id}
                    className="border-b border-gray-800/60 last:border-0"
                  >
                    <td className="py-3 pr-4 text-gray-400">
                      {formatDate(movement.created_at)}
                    </td>
                    <td className="py-3 pr-4 text-gray-200">
                      {MOVEMENT_LABELS[movement.movement_type] ??
                        movement.movement_type}
                    </td>
                    <td className="py-3 pr-4">
                      <p className="text-gray-200">
                        {movement.product_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {movement.size} / {movement.color} ·{" "}
                        {movement.sku}
                      </p>
                      {movement.reason && (
                        <p className="text-xs text-gray-500 mt-1">
                          {movement.reason}
                        </p>
                      )}
                    </td>
                    <td
                      className={`py-3 pr-4 font-semibold ${
                        movement.quantity_delta >= 0
                          ? "text-green-400"
                          : "text-red-400"
                      }`}
                    >
                      {movement.quantity_delta > 0 ? "+" : ""}
                      {movement.quantity_delta}
                    </td>
                    <td className="py-3 pr-4 text-gray-300">
                      {movement.stock_before} →{" "}
                      {movement.stock_after}
                    </td>
                    <td className="py-3 pr-4 text-gray-400">
                      {movement.order_id && (
                        <Link
                          to={`/admin/orders/${movement.order_id}`}
                          className="block text-cyan-400 hover:text-cyan-300"
                        >
                          Order #{movement.order_id}
                        </Link>
                      )}
                      {movement.return_request_id && (
                        <span className="block text-xs text-gray-500">
                          Return #{movement.return_request_id}
                        </span>
                      )}
                      {!movement.order_id &&
                        !movement.return_request_id &&
                        "—"}
                    </td>
                    <td className="py-3 pr-4 text-gray-500">
                      {movement.actor_user_id
                        ? `Admin #${movement.actor_user_id}`
                        : "System"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {movementPages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-5">
            <button
              type="button"
              disabled={movementPage === 1}
              onClick={() => {
                setMovementLoading(true);
                setMovementPage((current) => current - 1);
              }}
              className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
            >
              Previous
            </button>

            <span className="text-sm text-gray-400">
              Page {movementPage} of {movementPages}
            </span>

            <button
              type="button"
              disabled={movementPage >= movementPages}
              onClick={() => {
                setMovementLoading(true);
                setMovementPage((current) => current + 1);
              }}
              className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

export default AdminInventory;
