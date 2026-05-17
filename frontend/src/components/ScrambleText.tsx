import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

const DEFAULT_GLYPHS =
  "!<>-_\\/[]{}—=+*^?#abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

type Props = {
  text: string;
  /** Per-character lock-in delay in ms. Lower = faster reveal. */
  charDelayMs?: number;
  /** Glyph swap interval in ms while a character is still scrambling. */
  tickMs?: number;
  /** Delay before the scramble starts, in ms. */
  startDelayMs?: number;
  /** Character set used while scrambling. */
  glyphs?: string;
  /** Only run the scramble when the element enters the viewport. */
  triggerOnView?: boolean;
  className?: string;
  as?: "span" | "div" | "h1" | "h2" | "h3" | "p";
};

export function ScrambleText({
  text,
  charDelayMs = 55,
  tickMs = 35,
  startDelayMs = 0,
  glyphs = DEFAULT_GLYPHS,
  triggerOnView = true,
  className,
  as = "span",
}: Props) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const shouldRun = triggerOnView ? inView : true;

  const [display, setDisplay] = useState(() =>
    text.replace(/[^\s]/g, () => randomGlyph(glyphs)),
  );

  useEffect(() => {
    if (!shouldRun) return;

    let revealed = 0;
    let cancelled = false;
    let tickHandle: ReturnType<typeof setInterval> | null = null;
    let revealHandle: ReturnType<typeof setInterval> | null = null;

    const startTimer = setTimeout(() => {
      if (cancelled) return;
      // Swap random glyphs for un-revealed characters.
      tickHandle = setInterval(() => {
        setDisplay((prev) => {
          let next = "";
          for (let i = 0; i < text.length; i++) {
            if (i < revealed) {
              next += text[i];
            } else if (text[i] === " " || text[i] === "\n") {
              next += text[i];
            } else {
              next += randomGlyph(glyphs);
            }
          }
          return next;
        });
      }, tickMs);

      // Lock characters in one-by-one.
      revealHandle = setInterval(() => {
        revealed += 1;
        if (revealed >= text.length) {
          setDisplay(text);
          if (tickHandle) clearInterval(tickHandle);
          if (revealHandle) clearInterval(revealHandle);
        }
      }, charDelayMs);
    }, startDelayMs);

    return () => {
      cancelled = true;
      clearTimeout(startTimer);
      if (tickHandle) clearInterval(tickHandle);
      if (revealHandle) clearInterval(revealHandle);
    };
  }, [text, charDelayMs, tickMs, startDelayMs, glyphs, shouldRun]);

  const MotionTag =
    as === "h1"
      ? motion.h1
      : as === "h2"
        ? motion.h2
        : as === "h3"
          ? motion.h3
          : as === "p"
            ? motion.p
            : as === "div"
              ? motion.div
              : motion.span;

  return (
    <MotionTag
      ref={ref as never}
      className={className}
      initial={{ opacity: 0, filter: "blur(6px)" }}
      animate={
        shouldRun
          ? { opacity: 1, filter: "blur(0px)" }
          : { opacity: 0, filter: "blur(6px)" }
      }
      transition={{ duration: 0.4, ease: "easeOut" }}
      aria-label={text}
    >
      <span aria-hidden>{display}</span>
    </MotionTag>
  );
}

function randomGlyph(glyphs: string): string {
  return glyphs[Math.floor(Math.random() * glyphs.length)];
}
