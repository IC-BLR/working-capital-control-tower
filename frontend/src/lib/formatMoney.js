export function formatMoney(value, currency = "INR") {
  const n = Number(value || 0);
  const code = !currency || currency === "USD" ? "INR" : currency;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: code,
    maximumFractionDigits: 0,
  }).format(Number.isFinite(n) ? n : 0);
}
