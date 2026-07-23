// Fixed categorical hue order (never cycled/re-ranked) so a model keeps the
// same color across every chart and re-fetch, regardless of position. 8
// slots is the full validated palette (see dataviz skill's color-formula) —
// a 9th model would need to fold into "Other" or facet rather than wrap.
const PALETTE = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
];

export function buildModelColorMap(models) {
  const map = {};
  [...models].sort().forEach((model, i) => {
    map[model] = PALETTE[i % PALETTE.length];
  });
  return map;
}
