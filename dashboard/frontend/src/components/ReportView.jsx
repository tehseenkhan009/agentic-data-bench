import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

export default function ReportView({ report }) {
  const html = useMemo(() => {
    if (!report) return "";
    return DOMPurify.sanitize(marked.parse(report));
  }, [report]);

  if (!report) {
    return (
      <div className="empty-state">
        <p>No report found yet. Run the pipeline once to generate one:</p>
        <code>python main.py --data data/sample_sales.csv --question "..."</code>
      </div>
    );
  }

  return <div className="report-view" dangerouslySetInnerHTML={{ __html: html }} />;
}
