import { ReactNode } from "react";

type PanelProps = {
  children: ReactNode;
  className?: string;
  tone?:
    | "default"
    | "info"
    | "story"
    | "signal"
    | "time"
    | "success"
    | "danger"
    | "paper"
    | "neon"
    | "aqua"
    | "peach"
    | "gold"
    | "mint"
    | "ember";
};

const tones = {
  default: "surface-default",
  info: "surface-info",
  story: "surface-story",
  signal: "surface-signal",
  time: "surface-time",
  success: "surface-success",
  danger: "surface-danger",
  paper: "surface-default",
  neon: "surface-signal",
  aqua: "surface-info",
  peach: "surface-story",
  gold: "surface-time",
  mint: "surface-success",
  ember: "surface-danger",
};

export function Panel({ children, className = "", tone = "default" }: PanelProps) {
  return (
    <div
      className={`border-4 border-ink ${tones[tone]} shadow-brutal ${className}`}
    >
      {children}
    </div>
  );
}
