interface AvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-xs",
  lg: "h-11 w-11 text-sm",
} as const;
const palette = [
  "bg-indigo-500/20 text-indigo-200",
  "bg-teal-500/20 text-teal-200",
  "bg-violet-500/20 text-violet-200",
  "bg-emerald-500/20 text-emerald-200",
  "bg-amber-500/20 text-amber-200",
  "bg-rose-500/20 text-rose-200",
];

export function Avatar({ name, size = "md" }: AvatarProps) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const initials = `${parts[0]?.[0] ?? "?"}${parts.length > 1 ? parts[parts.length - 1]?.[0] ?? "" : ""}`;
  const hash = [...name].reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-medium uppercase ${sizeMap[size]} ${palette[hash % palette.length]}`}
      title={name}
    >
      {initials}
    </span>
  );
}
