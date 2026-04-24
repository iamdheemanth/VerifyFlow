import { formatConfidence } from "@/lib/utils";

type ConfidenceBarProps = {
  value: number | null;
  width?: number;
};

function colorClass(value: number) {
  if (value >= 0.8) {
    return "bg-[#166534]";
  }

  if (value >= 0.5) {
    return "bg-[#B45309]";
  }

  return "bg-[#991B1B]";
}

export default function ConfidenceBar({
  value,
  width = 48,
}: ConfidenceBarProps) {
  if (value === null) {
    return <span className="text-[#6F6D66] text-xs">-</span>;
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-mono text-[#F5F4F0]">
        {formatConfidence(value)}
      </span>
      <div
        style={{ width: `${width}px` }}
        className="h-1 rounded-full bg-[#2A2A26]"
      >
        <div
          style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
          className={`h-full rounded-full ${colorClass(value)}`}
        />
      </div>
    </div>
  );
}

