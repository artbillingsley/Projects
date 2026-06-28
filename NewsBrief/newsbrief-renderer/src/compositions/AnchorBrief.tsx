import React from "react";
import {Series, useVideoConfig} from "remotion";
import {Intro} from "../slots/Intro";
import {Hook} from "../slots/Hook";
import {Lead} from "../slots/Lead";
import {Scan} from "../slots/Scan";
import {WhyItMatters} from "../slots/WhyItMatters";
import {Close} from "../slots/Close";
import type {Spec, SlotType} from "../types/spec";

interface AnchorBriefProps {
  spec: Spec;
}

const GAP_FRAMES = 9; // 0.3s at 30fps
const INTRO_FRAMES = 75; // 2.5s at 30fps

// Ordered slot sequence for the anchor brief
const SLOT_ORDER: SlotType[] = ["HOOK", "LEAD", "SCAN", "WHY", "CLOSE"];

function renderSlotComponent(type: SlotType, slot: Parameters<typeof Hook>[0]["slot"]) {
  switch (type) {
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
  }
}

export const AnchorBrief: React.FC<AnchorBriefProps> = ({spec}) => {
  const {fps} = useVideoConfig();

  // Build ordered list of slots that exist in the spec
  const orderedSlots = SLOT_ORDER.flatMap((type) => {
    const slot = spec.slots.find((s) => s.type === type);
    return slot ? [{type, slot}] : [];
  });

  if (orderedSlots.length === 0) {
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
          fontSize: 48,
          fontFamily: "sans-serif",
        }}
      >
        No slots found in spec.
      </div>
    );
  }

  // Determine thumbnail based on brief_id
  const isTech = spec.brief_id?.startsWith("tech-");
  const thumbnailFile = isTech ? "thumbnails/thumb_tech.png" : "thumbnails/thumb_news.png";

  return (
    <Series>
      {/* Branded intro card — 2.5s */}
      <Series.Sequence durationInFrames={INTRO_FRAMES}>
        <Intro thumbnailFile={thumbnailFile} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={GAP_FRAMES}>
        <div style={{width: "100%", height: "100%", backgroundColor: "#0F1419"}} />
      </Series.Sequence>
      {orderedSlots.map(({type, slot}, i) => {
        const durationInFrames = Math.max(
          1,
          Math.round(slot.duration_seconds * fps),
        );
        return (
          <React.Fragment key={type}>
            <Series.Sequence durationInFrames={durationInFrames}>
              {renderSlotComponent(type, slot)}
            </Series.Sequence>
            {/* Add gap after every slot except the last */}
            {i < orderedSlots.length - 1 && (
              <Series.Sequence durationInFrames={GAP_FRAMES}>
                <div style={{width: "100%", height: "100%", backgroundColor: "#0F1419"}} />
              </Series.Sequence>
            )}
          </React.Fragment>
        );
      })}
    </Series>
  );
};
