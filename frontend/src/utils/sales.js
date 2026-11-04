function isoDate(value) {
  return value.toISOString().slice(0, 10);
}

export function dateRangeDays(days, now = new Date()) {
  const count = Math.max(1, Number(days) || 1);
  const end = new Date(
    Date.UTC(
      now.getUTCFullYear(),
      now.getUTCMonth(),
      now.getUTCDate()
    )
  );
  const start = new Date(end);
  start.setUTCDate(end.getUTCDate() - (count - 1));

  return {
    dateFrom: isoDate(start),
    dateTo: isoDate(end),
  };
}

export function buildDailySeries(
  periods,
  dateFrom,
  dateTo,
  valueKey
) {
  if (!dateFrom || !dateTo) return [];

  const start = new Date(`${dateFrom}T00:00:00Z`);
  const end = new Date(`${dateTo}T00:00:00Z`);

  if (
    Number.isNaN(start.getTime()) ||
    Number.isNaN(end.getTime()) ||
    start > end
  ) {
    return [];
  }

  const byPeriod = new Map(
    (periods ?? []).map((period) => [
      period.period,
      period,
    ])
  );
  const series = [];

  for (
    const cursor = new Date(start);
    cursor <= end;
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  ) {
    const period = isoDate(cursor);
    series.push({
      period,
      value: Number(byPeriod.get(period)?.[valueKey] ?? 0),
    });
  }

  return series;
}
