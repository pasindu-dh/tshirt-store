import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createAdminProduct,
  getAdminProduct,
  updateAdminProduct,
  uploadProductImage,
} from "../../api/admin";
import { getCategories } from "../../api/categories";
import ImageManager from "../../components/admin/ImageManager";
import VariantEditor from "../../components/admin/VariantEditor";
import { getApiError } from "../../utils/errors";

const EMPTY_VARIANT = { size: "M", color: "Black", sku: "", stock: "0" };
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

function AdminProductForm() {
  const { productId } = useParams();
  const isEditing = Boolean(productId);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "",
    category_id: "",
    is_active: true,
  });
  const [images, setImages] = useState([]);
  const [variants, setVariants] = useState([{ ...EMPTY_VARIANT }]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(isEditing);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getCategories()
      .then((data) => {
        if (!cancelled) setCategories(data);
      })
      .catch(() => {
        if (!cancelled) setCategories([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isEditing) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    setLoading(true);
    setError("");

    getAdminProduct(productId)
      .then((product) => {
        if (cancelled) return;

        setForm({
          name: product.name,
          description: product.description,
          price: String(product.price),
          category_id: product.category ? String(product.category.id) : "",
          is_active: product.is_active,
        });
        setImages(product.images.map((image) => image.url));
        setVariants(
          product.variants.length > 0
            ? product.variants.map((variant) => ({
                size: variant.size,
                color: variant.color,
                sku: variant.sku,
                stock: String(variant.stock),
              }))
            : [{ ...EMPTY_VARIANT }]
        );
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load the product.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isEditing, productId]);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleUpload = async (event) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";

    if (files.length === 0) return;

    setUploading(true);
    setError("");

    try {
      const uploadedUrls = [];

      for (const file of files) {
        if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
          throw new Error(
            `${file.name} must be a JPEG, PNG, or WebP image.`
          );
        }

        if (file.size > MAX_IMAGE_BYTES) {
          throw new Error(`${file.name} is larger than 5 MB.`);
        }

        const result = await uploadProductImage(file);
        uploadedUrls.push(result.url);
      }

      setImages((current) => [...current, ...uploadedUrls]);
    } catch (requestError) {
      setError(
        requestError.response
          ? getApiError(requestError, "Image upload failed.")
          : requestError.message || "Image upload failed."
      );
    } finally {
      setUploading(false);
    }
  };

  const removeImage = (index) => {
    setImages((current) =>
      current.filter((_, currentIndex) => currentIndex !== index)
    );
  };

  const makePrimary = (index) => {
    setImages((current) => {
      if (index === 0) return current;

      const next = [...current];
      const [selected] = next.splice(index, 1);
      next.unshift(selected);
      return next;
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const name = form.name.trim();
    const price = Number(form.price);

    if (!name) {
      setError("Product name is required.");
      return;
    }

    if (!Number.isInteger(price) || price < 0) {
      setError("Price must be a whole number of LKR.");
      return;
    }

    if (images.length === 0) {
      setError("Add at least one product image.");
      return;
    }

    if (variants.length === 0) {
      setError("Add at least one size variant.");
      return;
    }

    const normalizedVariants = variants.map((variant) => ({
      size: variant.size.trim(),
      color: variant.color.trim(),
      sku: variant.sku.trim(),
      stock: Number(variant.stock),
    }));

    if (
      normalizedVariants.some(
        (variant) => !variant.size || !variant.color || !variant.sku
      )
    ) {
      setError("Every variant needs a size, color, and SKU.");
      return;
    }

    if (
      normalizedVariants.some(
        (variant) => !Number.isInteger(variant.stock) || variant.stock < 0
      )
    ) {
      setError("Variant stock must be a whole number of 0 or more.");
      return;
    }

    const skus = normalizedVariants.map((variant) =>
      variant.sku.toLowerCase()
    );

    if (new Set(skus).size !== skus.length) {
      setError("Variant SKUs must be unique.");
      return;
    }

    const combinations = normalizedVariants.map(
      (variant) =>
        `${variant.size.toLowerCase()}|${variant.color.toLowerCase()}`
    );

    if (new Set(combinations).size !== combinations.length) {
      setError("Each size/color combination can appear only once.");
      return;
    }

    const payload = {
      name,
      description: form.description.trim(),
      price,
      category_id: form.category_id ? Number(form.category_id) : null,
      is_active: form.is_active,
      images,
      variants: normalizedVariants,
    };

    setSaving(true);

    try {
      if (isEditing) {
        await updateAdminProduct(productId, payload);
      } else {
        await createAdminProduct(payload);
      }

      navigate("/admin/products", {
        state: {
          message: isEditing ? "Product updated." : "Product created.",
        },
      });
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not save the product.")
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-gray-400">Loading product...</p>;
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-bold">
          {isEditing ? "Edit product" : "Add product"}
        </h2>

        <Link
          to="/admin/products"
          className="text-gray-400 hover:text-cyan-400 text-sm"
        >
          Back to products
        </Link>
      </div>

      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-lg font-semibold">Details</h3>

          <label className="block">
            <span className="text-sm text-gray-300">Name</span>
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              required
              className="mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-300">Description</span>
            <textarea
              value={form.description}
              onChange={(event) =>
                updateField("description", event.target.value)
              }
              rows={4}
              className="mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
            />
          </label>

          <div className="grid sm:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-gray-300">Price (LKR)</span>
              <input
                type="number"
                min="0"
                step="1"
                value={form.price}
                onChange={(event) =>
                  updateField("price", event.target.value)
                }
                required
                className="mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
              />
            </label>

            <label className="block">
              <span className="text-sm text-gray-300">Category</span>
              <select
                value={form.category_id}
                onChange={(event) =>
                  updateField("category_id", event.target.value)
                }
                aria-label="Category"
                className="mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400"
              >
                <option value="">Uncategorized</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                updateField("is_active", event.target.checked)
              }
              className="h-4 w-4 accent-cyan-400"
            />
            <span className="text-sm text-gray-300">
              Visible on the storefront
            </span>
          </label>
        </section>

        <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-4">Images</h3>
          <ImageManager
            images={images}
            uploading={uploading}
            onUpload={handleUpload}
            onRemove={removeImage}
            onMakePrimary={makePrimary}
          />
        </section>

        <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-4">Sizes & stock</h3>
          <VariantEditor variants={variants} onChange={setVariants} />
        </section>

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saving || uploading}
            className="bg-cyan-400 text-black px-6 py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving
              ? "Saving..."
              : isEditing
                ? "Save changes"
                : "Create product"}
          </button>

          <Link
            to="/admin/products"
            className="text-gray-400 hover:text-cyan-400"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

export default AdminProductForm;
