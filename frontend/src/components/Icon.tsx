import { CSSProperties } from "react";

type Props = {
  name: string;
  className?: string;
  filled?: boolean;
  style?: CSSProperties;
};

export function Icon({ name, className = "", filled, style }: Props) {
  const fillStyle = filled
    ? { fontVariationSettings: "'FILL' 1" as const, ...style }
    : style;
  return (
    <span className={`material-symbols-outlined ${className}`} style={fillStyle}>
      {name}
    </span>
  );
}
