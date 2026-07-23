// Fixed categorical hue order (never cycled/re-ranked) so a model keeps the
// same color across every chart and re-fetch, regardless of position.
const PALETTE = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];

export function buildModelColorMap(models) {
  const map = {};
  [...models].sort().forEach((model, i) => {
    map[model] = PALETTE[i % PALETTE.length];
  });
  return map;
}
