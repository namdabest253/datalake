import { HTMLAttributes, ReactNode } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

export function GlassCard({ children, className = "", ...rest }: Props) {
  return (
    <div
      className={`glass-card rounded-xl shadow-glass-sm ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
