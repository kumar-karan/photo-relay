import { useEffect, useRef, useState } from "react";

/**
 * Count from the previous value to the next one.
 *
 * A number that jumps straight to its final value feels like a status readout;
 * interpolating it makes progress legible at a glance.
 */
export function CountUp({
  value,
  format,
  duration = 520,
}: {
  value: number;
  format: (value: number) => string;
  duration?: number;
}) {
  const [display, setDisplay] = useState(value);
  const from = useRef(value);
  const frame = useRef<number | undefined>(undefined);

  useEffect(() => {
    const start = performance.now();
    const origin = from.current;
    const delta = value - origin;

    if (delta === 0) {
      setDisplay(value);
      return;
    }

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // Ease out cubic, so the value settles rather than stopping dead.
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(origin + delta * eased);
      if (progress < 1) {
        frame.current = requestAnimationFrame(tick);
      } else {
        from.current = value;
      }
    };

    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current !== undefined) cancelAnimationFrame(frame.current);
      from.current = value;
    };
  }, [value, duration]);

  return <>{format(display)}</>;
}