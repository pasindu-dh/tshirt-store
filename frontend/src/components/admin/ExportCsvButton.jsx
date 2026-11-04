import { useState } from "react";
import { getApiError } from "../../utils/errors";

function ExportCsvButton({
  onExport,
  label = "Export CSV",
  className = "",
}) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const handleClick = async () => {
    setExporting(true);
    setError("");

    try {
      await onExport();
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not export CSV.")
      );
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={exporting}
        className={`border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400 transition disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      >
        {exporting ? "Exporting..." : label}
      </button>
      {error && (
        <p className="text-xs text-red-400 text-right">{error}</p>
      )}
    </div>
  );
}

export default ExportCsvButton;
