import { useState } from "react";
import { Link } from "react-router-dom";
import {
  applyCatalogImport,
  previewCatalogImport,
} from "../../api/adminCatalogImport";
import { downloadCatalogCsv } from "../../api/adminExports";
import ExportCsvButton from "../../components/admin/ExportCsvButton";
import { getApiError } from "../../utils/errors";

const ACTION_CLASSES = {
  create: "text-green-400",
  update: "text-cyan-400",
  error: "text-red-400",
};

function Summary({ summary }) {
  const items = [
    ["Rows", summary.total_rows],
    ["Valid", summary.valid_rows],
    ["Errors", summary.error_rows],
    ["New products", summary.products_create],
    ["Updated products", summary.products_update],
    ["New variants", summary.variants_create],
    ["Updated variants", summary.variants_update],
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
      {items.map(([label, value]) => (
        <div
          key={label}
          className="bg-[#020617] border border-gray-800 rounded-xl p-3"
        >
          <p className="text-xs text-gray-400">{label}</p>
          <p className="text-xl font-semibold mt-1">{value}</p>
        </div>
      ))}
    </div>
  );
}

function AdminCatalogImport() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    setFile(event.target.files?.[0] ?? null);
    setPreview(null);
    setResult(null);
    setError("");
  };

  const handlePreview = async () => {
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      setPreview(await previewCatalogImport(file));
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not preview the catalog CSV."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!preview?.valid) return;

    if (
      !window.confirm(
        `Apply this import? ${preview.summary.products_create} product(s) will be created and ${preview.summary.products_update} updated.`
      )
    ) {
      return;
    }

    setApplying(true);
    setError("");

    try {
      const applied = await applyCatalogImport(file);
      setResult(applied);

      if (applied.valid) {
        setPreview(applied);
      }
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not apply the catalog import."
        )
      );
    } finally {
      setApplying(false);
    }
  };

  const shown = result ?? preview;

  return (
    <div>
      <Link
        to="/admin/products"
        className="text-sm text-gray-400 hover:text-cyan-400"
      >
        ← Back to products
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mt-4">
        <div>
          <h2 className="text-2xl font-bold">
            Import product catalog
          </h2>
          <p className="text-gray-400 text-sm mt-1">
            Upload a catalog CSV, preview validation, then apply
            the changes.
          </p>
        </div>

        <ExportCsvButton
          label="Download current catalog CSV"
          onExport={() => downloadCatalogCsv()}
        />
      </div>

      <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
        <label className="block text-sm text-gray-300">
          Catalog CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            className="mt-2 block w-full text-sm text-gray-300 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-400 file:px-4 file:py-2 file:font-semibold file:text-black"
          />
        </label>

        <div className="flex flex-wrap gap-3 mt-4">
          <button
            type="button"
            onClick={handlePreview}
            disabled={loading || !file}
            className="bg-cyan-400 text-black px-5 py-2 rounded-lg font-semibold hover:bg-cyan-300 disabled:opacity-50"
          >
            {loading ? "Validating..." : "Preview CSV"}
          </button>

          {preview?.valid && !result?.valid && (
            <button
              type="button"
              onClick={handleApply}
              disabled={applying}
              className="border border-green-500/60 text-green-400 px-5 py-2 rounded-lg font-semibold hover:bg-green-500/10 disabled:opacity-50"
            >
              {applying ? "Applying..." : "Apply import"}
            </button>
          )}
        </div>

        <div className="mt-4 text-xs text-gray-500 space-y-1">
          <p>
            Existing products are matched by <code>product_slug</code>.
            Leave it blank to create a new product.
          </p>
          <p>
            Variants are matched by size/color. Variants missing from
            the CSV are not deleted.
          </p>
          <p>
            Categories must already exist and are matched by{" "}
            <code>category_slug</code>. Images are pipe-separated in{" "}
            <code>image_urls</code>.
          </p>
        </div>

        {error && (
          <p className="text-sm text-red-400 mt-4">{error}</p>
        )}

        {result?.valid && (
          <p className="text-sm text-green-400 mt-4">
            Import applied successfully.{" "}
            <Link
              to="/admin/products"
              className="underline hover:text-green-300"
            >
              View products
            </Link>
          </p>
        )}
      </section>

      {shown && (
        <section className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-semibold">
              {result?.valid
                ? "Applied import"
                : shown.valid
                  ? "Preview"
                  : "Validation errors"}
            </h3>
            <p className="text-xs text-gray-500">
              {shown.valid
                ? "No changes are written during preview."
                : "Fix the listed row errors and upload again."}
            </p>
          </div>

          <Summary summary={shown.summary} />

          {shown.rows.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm min-w-[760px]">
                <thead className="text-left text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="py-2 pr-4">Row</th>
                    <th className="py-2 pr-4">Action</th>
                    <th className="py-2 pr-4">Product</th>
                    <th className="py-2 pr-4">Variant</th>
                    <th className="py-2">Message</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.rows.map((row, index) => (
                    <tr
                      key={`${row.row}-${index}`}
                      className="border-b border-gray-800/60 last:border-0"
                    >
                      <td className="py-2 pr-4 text-gray-500">
                        {row.row}
                      </td>
                      <td
                        className={`py-2 pr-4 capitalize ${
                          ACTION_CLASSES[row.action] ??
                          "text-gray-400"
                        }`}
                      >
                        {row.action}
                      </td>
                      <td className="py-2 pr-4 text-gray-300">
                        {row.product_name || "—"}
                        {row.product_slug && (
                          <span className="block text-xs text-gray-500">
                            {row.product_slug}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-gray-400">
                        {row.variant || "—"}
                      </td>
                      <td className="py-2 text-gray-400">
                        {row.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default AdminCatalogImport;
