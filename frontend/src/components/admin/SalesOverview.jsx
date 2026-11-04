import { Link } from "react-router-dom";
import { buildDailySeries } from "../../utils/sales";

function formatMoney(value) {
  return `LKR ${Number(value ?? 0).toLocaleString()}`;
}

function BarChart({
  label,
  series,
  barClass,
  formatValue,
  emptyLabel,
}) {
  const max = Math.max(
    ...series.map((point) => point.value),
    1
  );
  const total = series.reduce(
    (sum, point) => sum + point.value,
    0
  );

  return (
    <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{label}</h3>
          <p className="text-xs text-gray-500 mt-1">
            {series[0]?.period} to{" "}
            {series[series.length - 1]?.period}
          </p>
        </div>
        <p className="text-sm font-semibold text-gray-200">
          {formatValue(total)}
        </p>
      </div>

      {total === 0 ? (
        <p className="text-sm text-gray-400 mt-6">
          {emptyLabel}
        </p>
      ) : (
        <>
          <div
            role="img"
            aria-label={`${label} chart`}
            className="mt-5 h-36 flex items-end gap-[2px]"
          >
            {series.map((point) => {
              const height =
                point.value > 0
                  ? Math.max(
                      (point.value / max) * 100,
                      3
                    )
                  : 0;

              return (
                <div
                  key={point.period}
                  title={`${point.period}: ${formatValue(
                    point.value
                  )}`}
                  className="flex-1 h-full flex items-end"
                >
                  <div
                    className={`w-full rounded-t-sm ${barClass}`}
                    style={{ height: `${height}%` }}
                  />
                </div>
              );
            })}
          </div>

          <div className="flex justify-between text-[10px] text-gray-600 mt-2">
            <span>{series[0]?.period}</span>
            <span>{series[series.length - 1]?.period}</span>
          </div>
        </>
      )}
    </div>
  );
}

function SalesOverview({
  report,
  products,
  rangeDays,
  onRangeChange,
  loading,
  error,
}) {
  const revenueSeries = report
    ? buildDailySeries(
        report.periods,
        report.date_from,
        report.date_to,
        "net_revenue"
      )
    : [];
  const orderSeries = report
    ? buildDailySeries(
        report.periods,
        report.date_from,
        report.date_to,
        "delivered_orders"
      )
    : [];
  const topProducts = products?.products ?? [];
  const maxProductRevenue = Math.max(
    ...topProducts.map((product) => product.gross_revenue),
    1
  );
  const hasSales =
    report != null &&
    report.summary.delivered_orders > 0;

  return (
    <section className="mt-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Sales overview</h2>
          <p className="text-sm text-gray-400 mt-1">
            Delivered revenue and order volume, plus top products.
          </p>
        </div>

        <label className="text-xs text-gray-400">
          Period
          <select
            value={rangeDays}
            onChange={(event) =>
              onRangeChange(Number(event.target.value))
            }
            aria-label="Sales overview period"
            className="ml-2 p-2 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </label>
      </div>

      {error ? (
        <p className="text-sm text-red-400 mt-4">{error}</p>
      ) : loading && !report ? (
        <p className="text-sm text-gray-400 mt-4">
          Loading sales overview...
        </p>
      ) : !report ? null : (
        <>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <BarChart
              label="Net revenue"
              series={revenueSeries}
              barClass="bg-cyan-400/80"
              formatValue={formatMoney}
              emptyLabel="No delivered revenue in this period."
            />
            <BarChart
              label="Delivered orders"
              series={orderSeries}
              barClass="bg-green-400/80"
              formatValue={(value) => `${value} orders`}
              emptyLabel="No delivered orders in this period."
            />
          </div>

          <div className="grid lg:grid-cols-[1fr_1.4fr] gap-4 mt-4">
            <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
              <h3 className="font-semibold">Period totals</h3>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-400">Net revenue</dt>
                  <dd className="text-cyan-400">
                    {formatMoney(
                      report.summary.net_revenue
                    )}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-400">
                    Delivered orders
                  </dt>
                  <dd className="text-gray-200">
                    {report.summary.delivered_orders}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-400">
                    Completed refunds
                  </dt>
                  <dd className="text-gray-200">
                    {formatMoney(
                      report.summary.refunded_total
                    )}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-400">Open returns</dt>
                  <dd className="text-gray-200">
                    {report.summary.open_returns}
                  </dd>
                </div>
              </dl>

              {!hasSales && (
                <p className="text-xs text-gray-500 mt-4">
                  Sales appear here after orders are marked
                  delivered and paid.
                </p>
              )}
            </div>

            <div className="bg-[#020617] border border-gray-800 rounded-2xl p-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold">Top products</h3>
                <Link
                  to="/admin/reports/products"
                  className="text-xs text-cyan-400 hover:text-cyan-300"
                >
                  Full report →
                </Link>
              </div>

              {topProducts.length === 0 ? (
                <p className="text-sm text-gray-400 mt-4">
                  No product sales in this period.
                </p>
              ) : (
                <div className="mt-4 space-y-3">
                  {topProducts.map((product) => (
                    <div key={`${product.product_id ?? "deleted"}-${product.product_slug}`}>
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <p className="text-gray-200 truncate">
                          {product.product_name}
                        </p>
                        <p className="text-cyan-400 shrink-0">
                          LKR {product.gross_revenue}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-cyan-400/80 rounded-full"
                            style={{
                              width: `${
                                (product.gross_revenue /
                                  maxProductRevenue) *
                                100
                              }%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 shrink-0">
                          {product.units_sold} unit
                          {product.units_sold === 1 ? "" : "s"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default SalesOverview;
