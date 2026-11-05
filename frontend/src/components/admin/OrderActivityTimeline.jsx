const TYPE_CLASSES = {
  order: "bg-cyan-400",
  status: "bg-blue-400",
  details: "bg-purple-400",
  payment: "bg-green-400",
  refund: "bg-orange-400",
  return: "bg-yellow-400",
  inventory: "bg-red-400",
  audit: "bg-gray-400",
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

function OrderActivityTimeline({ events, loading, error }) {
  return (
    <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-3">
        Activity timeline
      </h3>

      {loading ? (
        <p className="text-sm text-gray-400">
          Loading order activity...
        </p>
      ) : error ? (
        <p className="text-sm text-red-400">{error}</p>
      ) : events.length === 0 ? (
        <p className="text-sm text-gray-400">
          No activity has been recorded for this order.
        </p>
      ) : (
        <ol className="relative border-l border-gray-800 ml-2 space-y-5">
          {events.map((event) => (
            <li key={event.id} className="ml-5">
              <span
                aria-hidden="true"
                className={`absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full ${
                  TYPE_CLASSES[event.type] ?? "bg-gray-500"
                }`}
              />
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-medium">
                  {event.title}
                </p>
                <p className="text-xs text-gray-500">
                  {formatDate(event.created_at)}
                </p>
              </div>
              {event.actor && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {event.actor}
                </p>
              )}
              {event.description && (
                <p className="text-sm text-gray-400 mt-1 whitespace-pre-line">
                  {event.description}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default OrderActivityTimeline;
