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
        bg: "bg-emerald-500/10",
        text: "text-emerald-300",
        dotColor: "bg-emerald-300",
      };
    case "executing":
    case "planning":
    case "running":
      return {
        bg: "bg-[#C8A882]/10",
        text: "text-[#E8D5BF]",
        dotColor: "bg-[#C8A882]",
        executing: true,
      };
    case "failed":
    case "rejected":
      return {
        bg: "bg-red-500/10",
        text: "text-red-300",
        dotColor: "bg-red-300",
      };
    case "escalated":
    case "pending_review":
    case "sent_back":
      return {
        bg: "bg-sky-500/10",
        text: "text-sky-300",
        dotColor: "bg-sky-300",
      };
    default:
      return {
        bg: "bg-[#23231F]",
        text: "text-[#8A8880]",
        dotColor: "bg-[#6F6D66]",
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

