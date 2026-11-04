import { useState } from "react";

const FIELDS = [
  {
    name: "contact_name",
    label: "Contact name",
    required: true,
    minLength: 2,
    maxLength: 120,
  },
  {
    name: "contact_email",
    label: "Contact email",
    type: "email",
    required: true,
  },
  {
    name: "phone",
    label: "Phone",
    required: true,
    minLength: 5,
    maxLength: 30,
  },
  {
    name: "address_line1",
    label: "Address line 1",
    required: true,
    minLength: 3,
    maxLength: 200,
  },
  {
    name: "address_line2",
    label: "Address line 2",
    maxLength: 200,
  },
  {
    name: "city",
    label: "City",
    required: true,
    minLength: 2,
    maxLength: 100,
  },
  {
    name: "postal_code",
    label: "Postal code",
    maxLength: 20,
  },
  {
    name: "country",
    label: "Country",
    required: true,
    minLength: 2,
    maxLength: 100,
  },
];

function initialValues(order) {
  return Object.fromEntries(
    FIELDS.map((field) => [
      field.name,
      order[field.name] ?? "",
    ]).concat([["notes", order.notes ?? ""]])
  );
}

function OrderEditForm({
  order,
  onSave,
  onCancel,
  saving,
  error,
}) {
  const [values, setValues] = useState(() =>
    initialValues(order)
  );

  const updateValue = (name, value) => {
    setValues((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSave(
      Object.fromEntries(
        Object.entries(values).map(([key, value]) => [
          key,
          value.trim(),
        ])
      )
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 border-t border-gray-800 pt-4"
    >
      <div>
        <h4 className="text-sm font-semibold">
          Edit customer & shipping details
        </h4>
        <p className="text-xs text-gray-500 mt-1">
          Changes are recorded in the order audit history.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        {FIELDS.map((field) => (
          <label
            key={field.name}
            className="block text-xs text-gray-300"
          >
            {field.label}
            <input
              type={field.type ?? "text"}
              value={values[field.name]}
              onChange={(event) =>
                updateValue(
                  field.name,
                  event.target.value
                )
              }
              required={field.required}
              minLength={field.minLength}
              maxLength={field.maxLength}
              className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>
        ))}
      </div>

      <label className="block text-xs text-gray-300">
        Internal notes
        <textarea
          value={values.notes}
          onChange={(event) =>
            updateValue("notes", event.target.value)
          }
          rows={2}
          maxLength={500}
          className="mt-1 w-full p-2 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
        />
      </label>

      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="bg-cyan-400 text-black px-4 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-300 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save details"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export default OrderEditForm;
