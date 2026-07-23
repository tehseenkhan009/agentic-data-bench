// Groups a flat run trace into renderable timeline items: Planner/Reporter
// entries stand alone, while consecutive Analyst+Reviewer entries for the
// same plan step are folded into one "step" group (one entry per retry
// attempt), so the Analyst<->Reviewer retry loop reads as a single unit
// instead of a scattered list (see src/graph.py's REVIEW_POLICY retry loop).
export function groupTrace(trace) {
  const groups = [];
  let i = 0;

  while (i < trace.length) {
    const entry = trace[i];

    if (entry.agent === "Analyst") {
      const step = entry.step;
      const attempts = [];
      let j = i;

      while (j < trace.length && trace[j].agent === "Analyst" && trace[j].step === step) {
        const analystEntry = trace[j];
        const reviewerEntry = trace[j + 1] && trace[j + 1].agent === "Reviewer" ? trace[j + 1] : null;
        attempts.push({ analyst: analystEntry, reviewer: reviewerEntry });
        j += reviewerEntry ? 2 : 1;
      }

      groups.push({ type: "step", step, attempts });
      i = j;
    } else {
      groups.push({ type: "single", entry });
      i += 1;
    }
  }

  return groups;
}
