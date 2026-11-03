import { useEffect, useState } from "react";
import {
  createAdminCoupon,
  deleteAdminCoupon,
  getAdminCoupons,
  updateAdminCoupon,
} from "../../api/adminCoupons";
import { getApiError } from "../../utils/errors";

const EMPTY_FORM = {
  code: "",
  description: "",
  discount_type: "percent",
  value: "10",
  min_subtotal: "0",
  usage_limit: "",
  starts_at: "",
  expires_at: "",
  is_active: true,
};

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function toLocalInput(value) {
  if (!value) return "";

  const date = new Date(value);
  const local = new Date(
    date.getTime() - date.getTimezoneOffset() * 60000
  );

  return local.toISOString().slice(0, 16);
}

function AdminCoupons() {
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getAdminCoupons()
      .then((data) => {
        if (!cancelled) setCoupons(data);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load coupons.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const reload = async () => {
    const data = await getAdminCoupons();
    setCoupons(data);
  };

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setFormError("");
  };

  const startEdit = (coupon) => {
    setForm({
      code: coupon.code,
      description: coupon.description,
      discount_type: coupon.discount_type,
      value: String(coupon.value),
      min_subtotal: String(coupon.min_subtotal),
      usage_limit:
        coupon.usage_limit === null
          ? ""
          : String(coupon.usage_limit),
      starts_at: toLocalInput(coupon.starts_at),
      expires_at: toLocalInput(coupon.expires_at),
      is_active: coupon.is_active,
    });
    setEditingId(coupon.id);
    setMessage("");
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setMessage("");

    if (!form.code.trim()) {
      setFormError("Enter a coupon code.");
      return;
    }

    if (!form.value || Number(form.value) < 1) {
      setFormError("Enter a discount value.");
      return;
    }

    const payload = {
      code: form.code.trim(),
      description: form.description.trim(),
      discount_type: form.discount_type,
      value: Number(form.value),
      min_subtotal: Number(form.min_subtotal) || 0,
      usage_limit:
        form.usage_limit === ""
          ? null
          : Number(form.usage_limit),
      starts_at: form.starts_at
        ? new Date(form.starts_at).toISOString()
        : null,
      expires_at: form.expires_at
        ? new Date(form.expires_at).toISOString()
        : null,
      is_active: form.is_active,
    };

    setSaving(true);

    try {
      if (editingId !== null) {
        await updateAdminCoupon(editingId, payload);
        setMessage("Coupon updated.");
      } else {
        await createAdminCoupon(payload);
        setMessage("Coupon created.");
      }

      resetForm();
      await reload();
    } catch (requestError) {
      setFormError(
        getApiError(requestError, "Could not save the coupon.")
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (coupon) => {
    if (
      !window.confirm(
        `Delete coupon ${coupon.code}? Existing orders keep their discount.`
      )
    ) {
      return;
    }

    setError("");
    setMessage("");

    try {
      await deleteAdminCoupon(coupon.id);
      setMessage("Coupon deleted.");
      await reload();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not delete the coupon.")
      );
    }
  };

  const inputClass =
    "mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400";
  const labelClass = "block text-sm text-gray-300";

  return (
    <div>
      <div>
        <h2 className="text-2xl font-bold">Coupons</h2>
        <p className="text-gray-400 text-sm mt-1">
          Create percentage or fixed-amount discounts for checkout.
        </p>
      </div>

      <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-6 mt-6">
        <form
          onSubmit={handleSubmit}
          className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4 h-fit"
        >
          <h3 className="text-lg font-semibold">
            {editingId === null ? "New coupon" : "Edit coupon"}
          </h3>

          <label className={labelClass}>
            Code
            <input
              value={form.code}
              onChange={(event) =>
                updateField("code", event.target.value)
              }
              maxLength={40}
              required
              className={inputClass}
            />
          </label>

          <label className={labelClass}>
            Description (optional)
            <input
              value={form.description}
              onChange={(event) =>
                updateField("description", event.target.value)
              }
              maxLength={200}
              className={inputClass}
            />
          </label>

          <div className="grid sm:grid-cols-2 gap-4">
            <label className={labelClass}>
              Type
              <select
                value={form.discount_type}
                onChange={(event) =>
                  updateField("discount_type", event.target.value)
                }
                className={inputClass}
              >
                <option value="percent">Percentage</option>
                <option value="fixed">Fixed amount</option>
              </select>
            </label>

            <label className={labelClass}>
              {form.discount_type === "percent"
                ? "Percentage (1-100)"
                : "Amount (LKR)"}
              <input
                type="number"
                min="1"
                value={form.value}
                onChange={(event) =>
                  updateField("value", event.target.value)
                }
                required
                className={inputClass}
              />
            </label>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <label className={labelClass}>
              Minimum subtotal (LKR)
              <input
                type="number"
                min="0"
                value={form.min_subtotal}
                onChange={(event) =>
                  updateField("min_subtotal", event.target.value)
                }
                className={inputClass}
              />
            </label>

            <label className={labelClass}>
              Usage limit (blank = unlimited)
              <input
                type="number"
                min="1"
                value={form.usage_limit}
                onChange={(event) =>
                  updateField("usage_limit", event.target.value)
                }
                className={inputClass}
              />
            </label>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <label className={labelClass}>
              Starts at (optional)
              <input
                type="datetime-local"
                value={form.starts_at}
                onChange={(event) =>
                  updateField("starts_at", event.target.value)
                }
                className={inputClass}
              />
            </label>

            <label className={labelClass}>
              Expires at (optional)
              <input
                type="datetime-local"
                value={form.expires_at}
                onChange={(event) =>
                  updateField("expires_at", event.target.value)
                }
                className={inputClass}
              />
            </label>
          </div>

          <label className="flex items-center gap-3 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                updateField("is_active", event.target.checked)
              }
              className="accent-cyan-400"
            />
            Active
          </label>

          {formError && (
            <p className="text-sm text-red-400">{formError}</p>
          )}
          {message && (
            <p className="text-sm text-green-400">{message}</p>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-cyan-400 text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50"
            >
              {saving
                ? "Saving..."
                : editingId === null
                  ? "Create coupon"
                  : "Update coupon"}
            </button>

            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                disabled={saving}
                className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 disabled:opacity-50"
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        <div className="bg-[#020617] border border-gray-800 rounded-2xl overflow-hidden">
          {loading ? (
            <p className="p-6 text-gray-400">Loading coupons...</p>
          ) : error ? (
            <p className="p-6 text-red-400">{error}</p>
          ) : coupons.length === 0 ? (
            <p className="p-6 text-gray-400">
              No coupons yet. Create one to offer a checkout discount.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[620px]">
                <thead className="text-left text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="p-4">Code</th>
                    <th className="p-4">Discount</th>
                    <th className="p-4">Used</th>
                    <th className="p-4">Expires</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {coupons.map((coupon) => (
                    <tr
                      key={coupon.id}
                      className="border-b border-gray-800/60 last:border-0"
                    >
                      <td className="p-4">
                        <p className="font-medium text-gray-200">
                          {coupon.code}
                        </p>
                        {coupon.description && (
                          <p className="text-xs text-gray-500">
                            {coupon.description}
                          </p>
                        )}
                      </td>
                      <td className="p-4 text-gray-300">
                        {coupon.discount_type === "percent"
                          ? `${coupon.value}%`
                          : `LKR ${coupon.value}`}
                        {coupon.min_subtotal > 0 && (
                          <span className="block text-xs text-gray-500">
                            Min LKR {coupon.min_subtotal}
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-gray-300">
                        {coupon.used_count} /{" "}
                        {coupon.usage_limit ?? "∞"}
                      </td>
                      <td className="p-4 text-gray-300">
                        {formatDate(coupon.expires_at)}
                      </td>
                      <td className="p-4">
                        <span
                          className={`px-2 py-1 rounded-full text-xs ${
                            coupon.is_active
                              ? "bg-green-500/15 text-green-400"
                              : "bg-gray-700/40 text-gray-300"
                          }`}
                        >
                          {coupon.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="p-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => startEdit(coupon)}
                          className="text-cyan-400 hover:text-cyan-300"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(coupon)}
                          className="ml-4 text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminCoupons;
