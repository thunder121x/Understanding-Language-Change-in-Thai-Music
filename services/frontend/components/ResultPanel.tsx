type ResultPanelProps = {
  content: string;
};

export function ResultPanel({ content }: ResultPanelProps) {
  if (!content) {
    return null;
    }

  return (
    <section
      style={{
        padding: "1rem",
        borderRadius: "8px",
        border: "1px solid #333",
        background: "#0f0f0f",
        overflowX: "auto"
      }}
    >
      <pre style={{ margin: 0 }}>{content}</pre>
    </section>
  );
}
