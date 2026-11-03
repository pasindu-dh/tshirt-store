function VariantEditor({ variants, onChange }) {
  const updateVariant = (index, field, value) => {
    onChange(
      variants.map((variant, currentIndex) =>
        currentIndex === index ? { ...variant, [field]: value } : variant
      )
    );
  };

  const addVariant = () => {
    onChange([
      ...variants,
      { size: "M", color: "Black", sku: "", stock: "0" },
    ]);
  };

  const removeVariant = (index) => {
    onChange(variants.filter((_, currentIndex) => currentIndex !== index));
  };

  const inputClass =
    "w-full p-2 rounded bg-black border border-gray-700 outline-none focus:border-cyan-400 text-sm";

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead className="text-left text-gray-400">
            <tr>
              <th className="pb-2">Size</th>
              <th className="pb-2">Color</th>
              <th className="pb-2">SKU</th>
              <th className="pb-2">Stock</th>
              <th className="pb-2" />
            </tr>
          </thead>

          <tbody>
            {variants.map((variant, index) => (
              <tr key={index}>
                <td className="pr-2 py-1">
                  <input
                    value={variant.size}
                    onChange={(event) =>
                      updateVariant(index, "size", event.target.value)
                    }
                    aria-label={`Variant ${index + 1} size`}
                    className={inputClass}
                  />
                </td>

                <td className="pr-2 py-1">
                  <input
                    value={variant.color}
                    onChange={(event) =>
                      updateVariant(index, "color", event.target.value)
                    }
                    aria-label={`Variant ${index + 1} color`}
                    className={inputClass}
                  />
                </td>

                <td className="pr-2 py-1">
                  <input
                    value={variant.sku}
                    onChange={(event) =>
                      updateVariant(index, "sku", event.target.value)
                    }
                    aria-label={`Variant ${index + 1} SKU`}
                    placeholder="FZ-01-M"
                    className={inputClass}
                  />
                </td>

                <td className="pr-2 py-1">
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={variant.stock}
                    onChange={(event) =>
                      updateVariant(index, "stock", event.target.value)
                    }
                    aria-label={`Variant ${index + 1} stock`}
                    className={inputClass}
                  />
                </td>

                <td className="py-1">
                  <button
                    type="button"
                    onClick={() => removeVariant(index)}
                    aria-label={`Remove variant ${index + 1}`}
                    className="text-red-400 hover:text-red-300"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {variants.length === 0 && (
        <p className="text-gray-500 text-sm mt-2">
          No variants yet. Add at least one size.
        </p>
      )}

      <button
        type="button"
        onClick={addVariant}
        className="mt-4 px-4 py-2 rounded-lg border border-cyan-400 text-cyan-400 text-sm font-semibold hover:bg-cyan-400 hover:text-black transition"
      >
        Add variant
      </button>
    </div>
  );
}

export default VariantEditor;
