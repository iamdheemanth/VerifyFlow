type StatusBadgeProps = {
  status: string;
  size?: "sm" | "md";
};

type Tone = {
  bg: string;
  text: string;
  dotColor: string;
  executing?: boolean;
};

function getStatusTone(status: string): Tone {
  switch (status) {
    case "completed":
      return {
        bg: "bg-[#DCFCE7]",
        text: "text-[#166534]",
        dotColor: "bg-[#166534]",
      };
    case "executing":
    case "planning":
    case "running":
      return {
        bg: "bg-[#FEF3C7]",
        text: "text-[#B45309]",
        dotColor: "bg-[#B45309]",
        executing: true,
      };
    case "failed":
    case "rejected":
      return {
        bg: "bg-[#FEE2E2]",
        text: "text-[#991B1B]",
        dotColor: "bg-[#991B1B]",
      };
    case "escalated":
    case "pending_review":
    case "sent_back":
      return {
        bg: "bg-[#DBEAFE]",
        text: "text-[#1D4ED8]",
        dotColor: "bg-[#1D4ED8]",
      };
    default:
      return {
        bg: "bg-[#EEE9E1]",
        text: "text-[#5C5248]",
        dotColor: "bg-[#9C948A]",
      };
  }
}

function formatStatusLabel(status: string) {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function StatusBadge({
  status,
  size = "sm",
}: StatusBadgeProps) {
  const tone = getStatusTone(status);
  const sizeClasses = size === "md" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${tone.bg} ${tone.text}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${tone.dotColor} ${
          tone.executing ? "animate-pulse" : ""
        }`}
      />
      {formatStatusLabel(status)}
    </span>
  );
}
