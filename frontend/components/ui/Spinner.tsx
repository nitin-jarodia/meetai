interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  color?: string;
}

const sizeMap: Record<NonNullable<SpinnerProps["size"]>, number> = {
  sm: 14,
  md: 20,
  lg: 32,
};

export function Spinner({ size = "md", color = "currentColor" }: SpinnerProps) {
  const px = sizeMap[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      className="animate-[spin_600ms_linear_infinite]"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.18" strokeWidth="3" />
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="18 30"
      />
    </svg>
  );
}
