import React from "react";
import {Composition} from "remotion";
import {z} from "zod";
import {AnchorBrief} from "./compositions/AnchorBrief";
import {MicroClip} from "./compositions/MicroClip";
import {Thumbnail} from "./compositions/Thumbnail";
import {SpecSchema} from "./types/spec";
import type {Spec} from "./types/spec";

const FPS = 30;
const GAP_SECONDS = 0.3; // silence between slots

// Schema for compositions that only need spec
const SpecPropsSchema = z.object({
  spec: SpecSchema,
});

// Schema for MicroClip, which needs spec + clipId
const MicroClipSchema = z.object({
  spec: SpecSchema,
  clipId: z.string(),
});

type SpecProps = z.infer<typeof SpecPropsSchema>;
type MicroClipSchemaProps = z.infer<typeof MicroClipSchema>;

const AnchorBriefComp = AnchorBrief as React.ComponentType<SpecProps>;
const ThumbnailComp = Thumbnail as React.ComponentType<SpecProps>;
const MicroClipComp = MicroClip as React.ComponentType<MicroClipSchemaProps>;

const INTRO_SECONDS = 2.5; // branded thumbnail card before narration

/** Calculate total frames from intro + slot durations + gaps */
function calcDuration(spec: Spec): number {
  const totalSeconds = spec.slots.reduce(
    (sum, s) => sum + s.duration_seconds + GAP_SECONDS,
    INTRO_SECONDS + GAP_SECONDS, // intro card + gap before first slot
  );
  return Math.max(Math.round(totalSeconds * FPS), FPS * 10);
}

export const RemotionRoot: React.FC = () => {
  const defaultSpec: Spec = {
    brief_id: "",
    date: "2026-01-01",
    issue_number: "N000",
    slots: [],
    clips: [],
    render_targets: [],
  };

  return (
    <>
      <Composition
        id="AnchorBrief"
        schema={SpecPropsSchema}
        component={AnchorBriefComp}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{spec: defaultSpec}}
        calculateMetadata={({props}) => ({
          durationInFrames: calcDuration(props.spec),
        })}
      />
      <Composition
        id="AnchorBrief9x16"
        schema={SpecPropsSchema}
        component={AnchorBriefComp}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{spec: defaultSpec}}
        calculateMetadata={({props}) => ({
          durationInFrames: calcDuration(props.spec),
        })}
      />
      <Composition
        id="Thumbnail"
        schema={SpecPropsSchema}
        component={ThumbnailComp}
        durationInFrames={1}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{spec: defaultSpec}}
      />
      <Composition
        id="MicroClip"
        schema={MicroClipSchema}
        component={MicroClipComp}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{spec: defaultSpec, clipId: "C1"}}
        calculateMetadata={({props}) => ({
          durationInFrames: calcDuration(props.spec),
        })}
      />
    </>
  );
};
