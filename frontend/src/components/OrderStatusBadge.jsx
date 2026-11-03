const STATUS_STYLES = {
  pending: "bg-yellow-500/15 text-yellow-400",
  confirmed: "bg-blue-500/15 text-blue-400",
  shipped: "bg-cyan-500/15 text-cyan-400",
  delivered: "bg-green-500/15 text-green-400",
  cancelled: "bg-red-500/15 text-red-400",
};

function OrderStatusBadge({ status }) {
  const style =
    STATUS_STYLES[status] ?? "bg-gray-700/40 text-gray-300";

  return (
    <span
      className={`px-2 py-1 rounded-full text-xs capitalize ${style}`}
    >
      {status}
    </span>
  );
}

export default OrderStatusBadge;
