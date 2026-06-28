import React from "react";
import {Series, useVideoConfig} from "remotion";
import {Hook} from "../slots/Hook";
import {Lead} from "../slots/Lead";
import {Scan} from "../slots/Scan";
import {WhyItMatters} from "../slots/WhyItMatters";
import {Close} from "../slots/Close";
import type {Spec, Slot, SlotType} from "../types/spec";

interface MicroClipProps {
  spec: Spec;
  clipId: string;
}

function renderSlotComponent(slot: Slot) {
  switch (slot.type as SlotType) {
    case "HOOK":
      return <Hook slot={slot} />;
    case "LEAD":
      return <Lead slot={slot} />;
    case "SCAN":
      return <Scan slot={slot} />;
    case "WHY":
      return <WhyItMatters slot={slot} />;
    case "CLOSE":
      return <Close slot={slot} />;
    default:
      return (
        <div
          style={{
            width: "100%",
            height: "100%",
            backgroundColor: "#0F1419",
          }}
        />
      );
  }
}

export const MicroClip: React.FC<MicroClipProps> = ({spec, clipId}) => {
  const {fps} = useVideoConfig();

  // Find the clip definition
  const clip = spec.clips.find((c) => c.id === clipId);
  if (!clip) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundColor: "#0F1419",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#C9A227",
          fontSize: 40,
          fontFamily: "sans-serif",
        }}
      >
        Clip &ldquo;{clipId}&rdquo; not found.
      </div>
    );
  }

  // Resolve slot type strings to actual slot objects from spec
  const resolvedSlots = clip.slots.flatMap((slotType) => {
    const slot = spec.slots.find((s) => s.type === slotType);
    return slot ? [slot] : [];
  });

  // Always append the CLOSE slot at the end (if not already included)
  const closeSlot = spec.slots.find((s) => s.type === "CLOSE");
  const hasClose = resolvedSlots.some((s) => s.type === "CLOSE");
  const allSlots = hasClose || !closeSlot
    ? resolvedSlots
    : [...resolvedSlots, closeSlot];

  if (allSlots.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundColor: "#0F1419",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#C9A227",
          fontSize: 40,
          fontFamily: "sans-serif",
        }}
      >
        No slots resolved for clip &ldquo;{clipId}&rdquo;.
      </div>
    );
  }

  return (
    <Series>
      {allSlots.map((slot, i) => {
        const durationInFrames = Math.max(
          1,
          Math.round(slot.duration_seconds * fps),
        );
        return (
          <Series.Sequence key={`${slot.type}-${i}`} durationInFrames={durationInFrames}>
            {renderSlotComponent(slot)}
          </Series.Sequence>
        );
      })}
    </Series>
  );
};
