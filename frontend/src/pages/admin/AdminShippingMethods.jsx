import { useEffect, useState } from "react";
import {
  createAdminShippingMethod,
  deleteAdminShippingMethod,
  getAdminShippingMethods,
  updateAdminShippingMethod,
} from "../../api/adminShipping";
import { getApiError } from "../../utils/errors";

const EMPTY_FORM = {
  name: "",
  description: "",
  fee_lkr: "",
  is_active: true,
  sort_order: "0",
};

function AdminShippingMethods() {
  const [methods, setMethods] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = () => {
    setLoading(true);
    setError("");

    return getAdminShippingMethods()
      .then((data) => {
        setMethods(data);
      })
      .catch((requestError) => {
        setError(
          getApiError(
            requestError,
            "Could not load shipping methods."
          )
        );
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, []);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const handleEdit = (method) => {
    setEditingId(method.id);
    setForm({
      name: method.name,
      description: method.description,
      fee_lkr: String(method.fee_lkr),
      is_active: method.is_active,
      sort_order: String(method.sort_order),
    });
    setError("");
    setMessage("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    const fee = Number(form.fee_lkr);
    const sortOrder = Number(form.sort_order);

    if (!form.name.trim()) {
      setError("Enter a shipping method name.");
      return;
    }

    if (!Number.isInteger(fee) || fee < 0) {
      setError("Shipping fee must be a whole number of 0 or more.");
      return;
    }

    if (!Number.isInteger(sortOrder) || sortOrder < 0) {
      setError("Sort order must be a whole number of 0 or more.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      fee_lkr: fee,
      is_active: form.is_active,
      sort_order: sortOrder,
    };
    setSaving(true);

    try {
      if (editingId) {
        await updateAdminShippingMethod(editingId, payload);
        setMessage("Shipping method updated.");
      } else {
        await createAdminShippingMethod(payload);
        setMessage("Shipping method created.");
      }

      resetForm();
      await load();
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not save the shipping method."
        )
      );
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (method) => {
    setBusyId(method.id);
    setError("");
    setMessage("");

    try {
      await updateAdminShippingMethod(method.id, {
        is_active: !method.is_active,
      });
      await load();
      setMessage(
        method.is_active
          ? "Shipping method deactivated."
          : "Shipping method activated."
      );
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not update the shipping method."
        )
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (method) => {
    if (
      !window.confirm(
        `Delete shipping method "${method.name}"? Existing orders keep their snapshotted method and fee.`
      )
    ) {
      return;
    }

    setBusyId(method.id);
    setError("");
    setMessage("");

    try {
      await deleteAdminShippingMethod(method.id);
      await load();
      setMessage("Shipping method deleted.");
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not delete the shipping method."
        )
      );
    } finally {
      setBusyId(null);
    }
  };

  const inputClass =
    "mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400";

  return (
    <div>
      <div>
        <h2 className="text-2xl font-bold">Shipping methods</h2>
        <p className="text-gray-400 text-sm mt-1">
          Manage the delivery options and fees shown at checkout.
        </p>
      </div>

      {message && (
        <p className="text-sm text-green-400 mt-3">{message}</p>
      )}
      {error && (
        <p className="text-sm text-red-400 mt-3">{error}</p>
      )}

      <form
        onSubmit={handleSubmit}
        className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5"
      >
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">
            {editingId
              ? "Edit shipping method"
              : "Add shipping method"}
          </h3>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="text-sm text-gray-400 hover:text-cyan-400"
            >
              Cancel edit
            </button>
          )}
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          <label className="block text-xs text-gray-300">
            Name
            <input
              value={form.name}
              onChange={(event) =>
                updateField("name", event.target.value)
              }
              maxLength={80}
              required
              className={inputClass}
            />
          </label>

          <label className="block text-xs text-gray-300">
            Fee (LKR)
            <input
              type="number"
              min="0"
              step="1"
              value={form.fee_lkr}
              onChange={(event) =>
                updateField("fee_lkr", event.target.value)
              }
              required
              className={inputClass}
            />
          </label>

          <label className="block text-xs text-gray-300">
            Sort order
            <input
              type="number"
              min="0"
              step="1"
              value={form.sort_order}
              onChange={(event) =>
                updateField("sort_order", event.target.value)
              }
              className={inputClass}
            />
          </label>

          <label className="flex items-center gap-2 text-xs text-gray-300 mt-5">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                updateField("is_active", event.target.checked)
              }
              className="accent-cyan-400"
            />
            Active at checkout
          </label>
        </div>

        <label className="block text-xs text-gray-300 mt-3">
          Description
          <input
            value={form.description}
            onChange={(event) =>
              updateField("description", event.target.value)
            }
            maxLength={500}
            className={inputClass}
          />
        </label>

        <button
          type="submit"
          disabled={saving}
          className="mt-4 bg-cyan-400 text-black px-5 py-2 rounded-lg font-semibold hover:bg-cyan-300 disabled:opacity-50"
        >
          {saving
            ? "Saving..."
            : editingId
              ? "Save changes"
              : "Add method"}
        </button>
      </form>

      {loading ? (
        <p className="mt-8 text-gray-400">
          Loading shipping methods...
        </p>
      ) : methods.length === 0 ? (
        <div className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">
            No shipping methods yet. Checkout falls back to the
            configured flat fee until one is added.
          </p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto bg-[#020617] border border-gray-800 rounded-2xl">
          <table className="w-full text-sm min-w-[720px]">
            <thead className="text-left text-gray-400 border-b border-gray-800">
              <tr>
                <th className="p-4">Method</th>
                <th className="p-4">Fee</th>
                <th className="p-4">Sort</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((method) => (
                <tr
                  key={method.id}
                  className="border-b border-gray-800/60 last:border-0"
                >
                  <td className="p-4">
                    <p className="text-gray-200">
                      {method.name}
                    </p>
                    {method.description && (
                      <p className="text-xs text-gray-500">
                        {method.description}
                      </p>
                    )}
                  </td>
                  <td className="p-4 text-cyan-400">
                    LKR {method.fee_lkr}
                  </td>
                  <td className="p-4 text-gray-300">
                    {method.sort_order}
                  </td>
                  <td className="p-4">
                    <span
                      className={
                        method.is_active
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {method.is_active
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => handleEdit(method)}
                        className="text-cyan-400 hover:text-cyan-300"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={busyId === method.id}
                        onClick={() => handleToggle(method)}
                        className="text-yellow-400 hover:text-yellow-300 disabled:opacity-50"
                      >
                        {method.is_active
                          ? "Deactivate"
                          : "Activate"}
                      </button>
                      <button
                        type="button"
                        disabled={busyId === method.id}
                        onClick={() => handleDelete(method)}
                        className="text-red-400 hover:text-red-300 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AdminShippingMethods;
