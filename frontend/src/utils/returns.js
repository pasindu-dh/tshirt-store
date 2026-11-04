export const FALLBACK_RETURN_REASONS = [
  { code: "size_fit", label: "Size or fit" },
  { code: "damaged", label: "Item arrived damaged" },
  { code: "wrong_item", label: "Wrong item received" },
  { code: "not_as_described", label: "Not as described" },
  { code: "changed_mind", label: "Changed my mind" },
  { code: "other", label: "Other" },
];

export const RETURN_REASON_LABELS = Object.fromEntries(
  FALLBACK_RETURN_REASONS.map((reason) => [
    reason.code,
    reason.label,
  ])
);

export function getReturnDeadline(deliveredAt, windowDays) {
  if (!deliveredAt) return null;

  const days = Number(windowDays);

  if (!Number.isFinite(days) || days <= 0) return null;

  const delivered = new Date(deliveredAt);

  if (Number.isNaN(delivered.getTime())) return null;

  return new Date(
    delivered.getTime() + days * 24 * 60 * 60 * 1000
  );
}

export function isReturnWindowOpen(
  deliveredAt,
  windowDays,
  now = new Date()
) {
  const deadline = getReturnDeadline(deliveredAt, windowDays);

  if (!deadline) return true;

  return now.getTime() <= deadline.getTime();
}
