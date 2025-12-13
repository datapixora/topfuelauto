"use client";

export default function JsonViewer({ value }: { value: any }) {
  return (
    <pre className="bg-slate-900 border border-slate-800 rounded p-3 text-xs overflow-auto whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}