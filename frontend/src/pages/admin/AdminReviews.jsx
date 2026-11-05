import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteAdminReview,
  getAdminReviews,
  updateAdminReviewStatus,
} from "../../api/adminReviews";
import { getApiError } from "../../utils/errors";

const PAGE_SIZE = 20;

const STATUS_CLASSES = {
  pending: "text-yellow-400",
  published: "text-green-400",
  rejected: "text-red-400",
};

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Stars({ rating }) {
  return (
    <span
      aria-label={`${rating} out of 5 stars`}
      className="text-yellow-400"
    >
      {"★".repeat(rating)}
      {"☆".repeat(5 - rating)}
    </span>
  );
}

function AdminReviews() {
  const [reviews, setReviews] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [rating, setRating] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const appliedSearchRef = useRef("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const resetResults = useCallback(() => {
    setPage(1);
    setReviews([]);
    setTotal(0);
    setError("");
    setLoading(true);
  }, []);

  useEffect(() => {
    const trimmed = search.trim();
    const timeout = setTimeout(() => {
      if (appliedSearchRef.current === trimmed) return;

      appliedSearchRef.current = trimmed;
      setAppliedSearch(trimmed);
      resetResults();
    }, 300);

    return () => clearTimeout(timeout);
  }, [search, resetResults]);

  useEffect(() => {
    let cancelled = false;

    getAdminReviews({
      page,
      limit: PAGE_SIZE,
      status: status || undefined,
      rating: rating || undefined,
      search: appliedSearch || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setReviews(result.reviews);
        setTotal(result.total);
        setError("");
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
  }, [page, status, rating, appliedSearch, refreshKey]);

  const refresh = () => {
    setRefreshKey((current) => current + 1);
  };

  const changeStatus = async (review, nextStatus) => {
    setBusyId(review.id);
    setError("");
    setMessage("");

    try {
      await updateAdminReviewStatus(review.id, nextStatus);
      setMessage(`Review ${nextStatus}.`);
      setLoading(true);
      refresh();
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not update the review."
        )
      );
    } finally {
      setBusyId(null);
    }
  };

  const removeReview = async (review) => {
    if (
      !window.confirm(
        "Delete this review? This cannot be undone."
      )
    ) {
      return;
    }

    setBusyId(review.id);
    setError("");
    setMessage("");

    try {
      await deleteAdminReview(review.id);
      setMessage("Review deleted.");
      setLoading(true);
      refresh();
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not delete the review."
        )
      );
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">Reviews</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} review{total === 1 ? "" : "s"} found
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-6">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search product, customer, or review text"
          aria-label="Search reviews"
          className="flex-1 p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        />

        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            resetResults();
          }}
          aria-label="Filter by status"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="published">Published</option>
          <option value="rejected">Rejected</option>
        </select>

        <select
          value={rating}
          onChange={(event) => {
            setRating(event.target.value);
            resetResults();
          }}
          aria-label="Filter by rating"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          <option value="">All ratings</option>
          {[5, 4, 3, 2, 1].map((value) => (
            <option key={value} value={value}>
              {value} star{value === 1 ? "" : "s"}
            </option>
          ))}
        </select>
      </div>

      {message && (
        <p className="text-sm text-green-400 mt-3">{message}</p>
      )}
      {error && (
        <p className="text-sm text-red-400 mt-3">{error}</p>
      )}

      {loading ? (
        <p className="mt-8 text-gray-400">Loading reviews...</p>
      ) : reviews.length === 0 ? (
        <div className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">No reviews found.</p>
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {reviews.map((review) => (
            <article
              key={review.id}
              className="bg-[#020617] border border-gray-800 rounded-2xl p-5"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div>
                  <Link
                    to={`/admin/products/${review.product_id}/edit`}
                    className="font-semibold text-cyan-400 hover:text-cyan-300"
                  >
                    {review.product_name}
                  </Link>
                  <p className="text-sm text-gray-400 mt-1">
                    {review.user_name} · {review.user_email}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatDate(review.created_at)}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <Stars rating={review.rating} />
                  <span
                    className={`text-xs font-semibold capitalize ${
                      STATUS_CLASSES[review.status] ??
                      "text-gray-400"
                    }`}
                  >
                    {review.status}
                  </span>
                </div>
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

              <div className="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-gray-800">
                {review.status !== "published" && (
                  <button
                    type="button"
                    disabled={busyId === review.id}
                    onClick={() =>
                      changeStatus(review, "published")
                    }
                    className="bg-cyan-400 text-black px-4 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-300 disabled:opacity-50"
                  >
                    Approve
                  </button>
                )}

                {review.status !== "rejected" && (
                  <button
                    type="button"
                    disabled={busyId === review.id}
                    onClick={() =>
                      changeStatus(review, "rejected")
                    }
                    className="border border-yellow-500/60 text-yellow-400 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-yellow-500/10 disabled:opacity-50"
                  >
                    Reject
                  </button>
                )}

                {review.status !== "pending" && (
                  <button
                    type="button"
                    disabled={busyId === review.id}
                    onClick={() =>
                      changeStatus(review, "pending")
                    }
                    className="border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400 disabled:opacity-50"
                  >
                    Send to pending
                  </button>
                )}

                <button
                  type="button"
                  disabled={busyId === review.id}
                  onClick={() => removeReview(review)}
                  className="ml-auto text-sm text-red-400 hover:text-red-300 disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => {
              setLoading(true);
              setPage((current) => current - 1);
            }}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => {
              setLoading(true);
              setPage((current) => current + 1);
            }}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminReviews;
