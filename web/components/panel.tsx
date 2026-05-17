import { ReactNode } from "react";

type PanelProps = {
  children: ReactNode;
  className?: string;
  intensity?: "raised" | "quiet" | "flat";
  tone?:
    | "default"
    | "quiet"
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
  quiet: "surface-quiet",
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

const intensities = {
  raised: "shadow-brutal",
  quiet: "shadow-brutalSoft",
  flat: "shadow-none",
};

export function Panel({ children, className = "", intensity = "raised", tone = "default" }: PanelProps) {
  return (
    <div
      className={`border-4 border-ink ${tones[tone]} ${intensities[intensity]} ${className}`}
    >
      {children}
    </div>
  );
}
