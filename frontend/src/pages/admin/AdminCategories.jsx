import { useCallback, useEffect, useState } from "react";
import {
  createCategory,
  deleteCategory,
  getCategories,
  updateCategory,
} from "../../api/categories";
import { getApiError } from "../../utils/errors";

function AdminCategories() {
  const [categories, setCategories] = useState([]);
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const data = await getCategories();
      setCategories(data);
      setError("");
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not load categories.")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (event) => {
    event.preventDefault();

    const trimmed = name.trim();

    if (!trimmed) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await createCategory(trimmed);
      setName("");
      setMessage("Category created.");
      await load();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not create the category.")
      );
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (category) => {
    setEditingId(category.id);
    setEditingName(category.name);
    setError("");
    setMessage("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleUpdate = async (categoryId) => {
    const trimmed = editingName.trim();

    if (!trimmed) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await updateCategory(categoryId, trimmed);
      cancelEdit();
      setMessage("Category updated.");
      await load();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not update the category.")
      );
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (category) => {
    if (!window.confirm(`Delete category "${category.name}"?`)) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await deleteCategory(category.id);
      setMessage("Category deleted.");
      await load();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not delete the category.")
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold">Categories</h2>
      <p className="text-gray-400 text-sm mt-1">
        Categories organize the storefront catalog.
      </p>

      <form
        onSubmit={handleCreate}
        className="flex flex-col sm:flex-row gap-3 mt-6"
      >
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="New category name"
          className="flex-1 p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <button
          type="submit"
          disabled={busy || !name.trim()}
          className="bg-cyan-400 text-black px-5 py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add category
        </button>
      </form>

      {message && <p className="mt-4 text-green-400 text-sm">{message}</p>}
      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      {loading ? (
        <p className="mt-8 text-gray-400">Loading categories...</p>
      ) : categories.length === 0 ? (
        <p className="mt-8 text-gray-400">No categories yet.</p>
      ) : (
        <div className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl divide-y divide-gray-800">
          {categories.map((category) => (
            <div
              key={category.id}
              className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between p-4"
            >
              {editingId === category.id ? (
                <div className="flex flex-1 flex-col sm:flex-row gap-3">
                  <input
                    value={editingName}
                    onChange={(event) =>
                      setEditingName(event.target.value)
                    }
                    aria-label={`Rename ${category.name}`}
                    className="flex-1 p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
                  />

                  <button
                    type="button"
                    disabled={busy || !editingName.trim()}
                    onClick={() => handleUpdate(category.id)}
                    className="text-cyan-400 text-sm disabled:opacity-50"
                  >
                    Save
                  </button>

                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="text-gray-400 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div>
                  <p className="font-medium">{category.name}</p>
                  <p className="text-xs text-gray-500">{category.slug}</p>
                </div>
              )}

              {editingId !== category.id && (
                <div className="flex gap-4">
                  <button
                    type="button"
                    onClick={() => startEdit(category)}
                    className="text-cyan-400 text-sm hover:text-cyan-300"
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleDelete(category)}
                    className="text-red-400 text-sm hover:text-red-300 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminCategories;
