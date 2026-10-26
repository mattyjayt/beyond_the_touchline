import { useId } from "react";
import { PITCH_H, PITCH_W } from "@/lib/pitch";

/** Striped grass and FIFA markings on the 105 x 68 SVG frame (shared by every pitch view). */
export function PitchMarkings() {
  const stripes = useId();
  return (
    <>
      <defs>
        <pattern id={stripes} width="21" height={PITCH_H} patternUnits="userSpaceOnUse">
          <rect width="10.5" height={PITCH_H} fill="var(--pitch-a)" />
          <rect x="10.5" width="10.5" height={PITCH_H} fill="var(--pitch-b)" />
        </pattern>
      </defs>
      <rect x="-3" y="-3" width={PITCH_W + 6} height={PITCH_H + 6} rx="2" fill="var(--pitch-b)" />
      <rect width={PITCH_W} height={PITCH_H} fill={`url(#${stripes})`} />
      <g fill="none" stroke="var(--pitch-line)" strokeWidth="0.3">
        <rect width={PITCH_W} height={PITCH_H} />
        <line x1={PITCH_W / 2} y1="0" x2={PITCH_W / 2} y2={PITCH_H} />
        <circle cx={PITCH_W / 2} cy={PITCH_H / 2} r="9.15" />
        <rect x="0" y={PITCH_H / 2 - 20.16} width="16.5" height="40.32" />
        <rect x={PITCH_W - 16.5} y={PITCH_H / 2 - 20.16} width="16.5" height="40.32" />
        <rect x="0" y={PITCH_H / 2 - 9.16} width="5.5" height="18.32" />
        <rect x={PITCH_W - 5.5} y={PITCH_H / 2 - 9.16} width="5.5" height="18.32" />
        <path d={`M16.5 ${PITCH_H / 2 - 7.3} A9.15 9.15 0 0 1 16.5 ${PITCH_H / 2 + 7.3}`} />
        <path d={`M${PITCH_W - 16.5} ${PITCH_H / 2 - 7.3} A9.15 9.15 0 0 0 ${PITCH_W - 16.5} ${PITCH_H / 2 + 7.3}`} />
        <rect x="-1.5" y={PITCH_H / 2 - 3.66} width="1.5" height="7.32" />
        <rect x={PITCH_W} y={PITCH_H / 2 - 3.66} width="1.5" height="7.32" />
      </g>
      <circle cx={PITCH_W / 2} cy={PITCH_H / 2} r="0.4" fill="var(--pitch-line)" />
    </>
  );
}
