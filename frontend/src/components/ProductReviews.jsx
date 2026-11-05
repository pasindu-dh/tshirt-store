import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  createReview,
  deleteReview,
  getProductReviews,
  updateReview,
} from "../api/reviews";
import useAuth from "../hooks/useAuth";
import { getApiError } from "../utils/errors";

function Stars({ rating }) {
  const rounded = Math.max(1, Math.min(5, Math.round(rating)));

  return (
    <span
      aria-label={`${rating} out of 5 stars`}
      className="text-yellow-400 tracking-wide"
    >
      {"★".repeat(rounded)}
      {"☆".repeat(5 - rounded)}
    </span>
  );
}

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function ProductReviews({ productId }) {
  const { user } = useAuth();
  const location = useLocation();
  const [summary, setSummary] = useState({
    items: [],
    count: 0,
    average: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    rating: 5,
    title: "",
    comment: "",
  });

  useEffect(() => {
    let cancelled = false;

    getProductReviews(productId)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load reviews.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [productId]);

  const myReview = user
    ? (summary.my_review ??
      summary.items.find((review) => review.user_id === user.id))
    : null;

  const reload = async () => {
    const data = await getProductReviews(productId);
    setSummary(data);
  };

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const startEditing = () => {
    if (!myReview) return;

    setForm({
      rating: myReview.rating,
      title: myReview.title,
      comment: myReview.comment,
    });
    setEditing(true);
    setMessage("");
    setFormError("");
  };

  const cancelEditing = () => {
    setEditing(false);
    setFormError("");
    setForm({ rating: 5, title: "", comment: "" });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError("");
    setMessage("");

    try {
      let saved;

      if (editing && myReview) {
        saved = await updateReview(myReview.id, form);
        setMessage(
          saved.status === "pending"
            ? "Your updated review is awaiting moderation."
            : "Your review was updated."
        );
      } else {
        saved = await createReview(productId, form);
        setMessage(
          saved.status === "pending"
            ? "Thanks! Your review is awaiting moderation."
            : "Thanks for reviewing this product."
        );
      }

      setEditing(false);
      setForm({ rating: 5, title: "", comment: "" });
      await reload();
    } catch (requestError) {
      setFormError(
        getApiError(requestError, "Could not save your review.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!myReview || !window.confirm("Delete your review?")) {
      return;
    }

    setSubmitting(true);
    setFormError("");
    setMessage("");

    try {
      await deleteReview(myReview.id);
      setEditing(false);
      setForm({ rating: 5, title: "", comment: "" });
      setMessage("Your review was deleted.");
      await reload();
    } catch (requestError) {
      setFormError(
        getApiError(requestError, "Could not delete your review.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400";

  return (
    <section
      aria-labelledby="reviews-heading"
      className="border-t border-gray-800 pt-10"
    >
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h2 id="reviews-heading" className="text-2xl font-bold">
            Customer reviews
          </h2>
          <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
            {summary.count > 0 ? (
              <>
                <Stars rating={summary.average} />
                <span>
                  {summary.average.toFixed(1)} · {summary.count}{" "}
                  review{summary.count === 1 ? "" : "s"}
                </span>
              </>
            ) : (
              <span>No reviews yet.</span>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <p className="mt-6 text-gray-400">Loading reviews...</p>
      ) : error ? (
        <p className="mt-6 text-red-400">{error}</p>
      ) : (
        <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-8 mt-8">
          <div className="space-y-4">
            {summary.items.length === 0 ? (
              <p className="text-sm text-gray-500">
                Be the first customer to review this product.
              </p>
            ) : (
              summary.items.map((review) => (
                <article
                  key={review.id}
                  className="bg-[#020617] border border-gray-800 rounded-2xl p-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{review.user_name}</p>
                      <p className="text-xs text-gray-500">
                        {formatDate(review.created_at)}
                      </p>
                    </div>
                    <Stars rating={review.rating} />
                  </div>

                  {review.title && (
                    <h3 className="font-semibold mt-3">
                      {review.title}
                    </h3>
                  )}

                  {review.comment && (
                    <p className="text-sm text-gray-300 mt-2 whitespace-pre-line">
                      {review.comment}
                    </p>
                  )}
                </article>
              ))
            )}
          </div>

          <aside className="bg-[#020617] border border-gray-800 rounded-2xl p-5 h-fit">
            <h3 className="text-lg font-semibold">
              {editing ? "Edit your review" : "Write a review"}
            </h3>
            {editing && myReview?.status !== "published" && (
              <p className="text-xs text-gray-500 mt-1">
                Edited reviews may need moderator approval before
                they appear publicly.
              </p>
            )}

            {!user ? (
              <p className="text-sm text-gray-400 mt-3">
                <Link
                  to="/login"
                  state={{ from: location.pathname }}
                  className="text-cyan-400 hover:text-cyan-300"
                >
                  Sign in
                </Link>{" "}
                to share your experience.
              </p>
            ) : myReview && !editing ? (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-gray-400">
                  You already reviewed this product.
                </p>
                {myReview.status === "pending" && (
                  <p className="text-xs text-yellow-400">
                    Your review is awaiting moderation and is not
                    public yet.
                  </p>
                )}
                {myReview.status === "rejected" && (
                  <p className="text-xs text-red-400">
                    Your review was not published. Edit it to
                    resubmit for review.
                  </p>
                )}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={startEditing}
                    className="px-4 py-2 rounded-lg border border-gray-700 text-sm text-gray-200 hover:border-cyan-400 hover:text-cyan-400"
                  >
                    Edit review
                  </button>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={submitting}
                    className="px-4 py-2 rounded-lg border border-red-500/50 text-sm text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                <label className="block">
                  <span className="text-sm text-gray-300">Rating</span>
                  <select
                    value={form.rating}
                    onChange={(event) =>
                      updateField("rating", Number(event.target.value))
                    }
                    className={inputClass}
                  >
                    {[5, 4, 3, 2, 1].map((rating) => (
                      <option key={rating} value={rating}>
                        {rating} star{rating === 1 ? "" : "s"}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="text-sm text-gray-300">
                    Title (optional)
                  </span>
                  <input
                    value={form.title}
                    onChange={(event) =>
                      updateField("title", event.target.value)
                    }
                    maxLength={120}
                    className={inputClass}
                  />
                </label>

                <label className="block">
                  <span className="text-sm text-gray-300">
                    Review (optional)
                  </span>
                  <textarea
                    value={form.comment}
                    onChange={(event) =>
                      updateField("comment", event.target.value)
                    }
                    rows={4}
                    maxLength={2000}
                    className={inputClass}
                  />
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
                    disabled={submitting}
                    className="flex-1 bg-cyan-400 text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50"
                  >
                    {submitting
                      ? "Saving..."
                      : editing
                        ? "Update review"
                        : "Submit review"}
                  </button>

                  {editing && (
                    <button
                      type="button"
                      onClick={cancelEditing}
                      disabled={submitting}
                      className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            )}

            {myReview && !editing && message && (
              <p className="text-sm text-green-400 mt-3">{message}</p>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}

export default ProductReviews;
