import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors, spacing, fontSize } from "../design/theme";
import { fontFamily } from "../design/fonts";
import { springIn } from "../design/animations";
import { ProgressBar } from "../components/ProgressBar";
import { Wordmark } from "../components/Wordmark";
import { BottomUrl } from "../components/BottomUrl";
import { Slot } from "../types/spec";

interface CloseProps {
  slot: Slot;
}

// "Decide." appears at roughly 75% through the slot duration
const DECIDE_DELAY_RATIO = 0.75;

export const Close: React.FC<CloseProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const isVertical = height > width;

  const currentTime = frame / fps;

  // Wordmark fades in from frame 0 via the Wordmark component itself
  // CIFaaS URL + subtitle fades in after wordmark settles (~fps*0.6)
  const urlStartFrame = Math.round(fps * 0.6);
  const urlOpacity = interpolate(
    frame - urlStartFrame,
    [0, Math.round(fps * 0.4)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const urlTranslateY = interpolate(
    frame - urlStartFrame,
    [0, Math.round(fps * 0.4)],
    [16, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // "Decide." appears at DECIDE_DELAY_RATIO of the total slot duration
  const decideStartFrame = Math.round(durationInFrames * DECIDE_DELAY_RATIO);
  const decideSpring = springIn(Math.max(0, frame - decideStartFrame), fps);
  const decideOpacity = interpolate(decideSpring, [0, 1], [0, 1]);
  const decideScale = interpolate(decideSpring, [0, 1], [0.85, 1]);

  const urlFontSize = isVertical ? (fontSize.tagSmall - 2) * 2 : (fontSize.tag - 2) * 2;
  const subtitleFontSize = isVertical ? fontSize.tagSmall - 6 : fontSize.tagSmall - 2;
  const decideFontSize = isVertical ? fontSize.subheadline : fontSize.headlineDesktop;
  const paddingH = isVertical ? spacing.xl : spacing.xl;

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
        overflow: "hidden",
        paddingLeft: paddingH,
        paddingRight: paddingH,
        boxSizing: "border-box" as const,
      }}
    >
      <ProgressBar />

      {/* COGNOSCERE wordmark */}
      <Wordmark startFrame={0} />

      {/* CIFaaS URL + "Read the full record" */}
      <div
        style={{
          marginTop: spacing.md,
          opacity: urlOpacity,
          transform: `translateY(${urlTranslateY}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: spacing.xs,
        }}
      >
        <span
          style={{
            fontFamily: fontFamily.mono,
            fontSize: urlFontSize,
            color: colors.secondaryText,
            letterSpacing: 1,
          }}
        >
          cifaas.cognoscerellc.com
        </span>
        <span
          style={{
            fontFamily: fontFamily.body,
            fontSize: subtitleFontSize,
            color: colors.secondaryText,
            opacity: 0.7,
          }}
        >
          Read the full record
        </span>
      </div>

      {/* Divider */}
      <div
        style={{
          marginTop: spacing.lg,
          marginBottom: spacing.lg,
          width: 40,
          height: 1,
          backgroundColor: colors.gold,
          opacity: urlOpacity * 0.4,
        }}
      />

      {/* "Decide." — appears last, holds until end */}
      <div
        style={{
          opacity: decideOpacity,
          transform: `scale(${decideScale})`,
        }}
      >
        <span
          style={{
            fontFamily: fontFamily.headline,
            fontSize: decideFontSize,
            color: colors.gold,
            letterSpacing: 2,
          }}
        >
          Decide.
        </span>
      </div>

      <BottomUrl />
    </div>
  );
};
