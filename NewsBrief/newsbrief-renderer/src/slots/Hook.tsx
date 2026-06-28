import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors, spacing, fontSize } from "../design/theme";
import { fontFamily } from "../design/fonts";
import { LOWER_THIRD_DELAY } from "../design/animations";
import { ProgressBar } from "../components/ProgressBar";
import { BrandHeader } from "../components/BrandHeader";
import { BottomUrl } from "../components/BottomUrl";
import { CifTag } from "../components/CifTag";
import { KenBurnsPhoto } from "../components/KenBurnsPhoto";
import { FallbackGraphic } from "../components/FallbackGraphic";
import { Slot } from "../types/spec";

interface HookProps {
  slot: Slot;
}

export const Hook: React.FC<HookProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const currentTime = frame / fps;

  // Use slot.copy (clean, no SSML) for display text.
  // Fade in based on when the first word timing starts.
  const firstWordStart =
    slot.words.length > 0 ? slot.words[0].start : 0;
  const showText = currentTime >= firstWordStart;
  const textOpacity = showText
    ? interpolate(
        currentTime - firstWordStart,
        [0, 0.5],
        [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      )
    : 0;

  // CIF tag fades in after LOWER_THIRD_DELAY frames
  const cifOpacity = interpolate(
    frame - LOWER_THIRD_DELAY,
    [0, 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const headlineFontSize = isVertical
    ? fontSize.subheadline
    : fontSize.headlineDesktop;
  const paddingH = isVertical ? spacing.xl : spacing.xl;

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <ProgressBar />
      <BrandHeader />

      {/* Ken Burns stock photo or branded fallback — bottom 45% */}
      {slot.image_file ? (
        <KenBurnsPhoto imageFile={slot.image_file} height="45%" />
      ) : (
        <FallbackGraphic
          icon={slot.fallback_icon}
          dataPoint={slot.fallback_data_point}
          height="45%"
        />
      )}

      {/* Central statement — positioned in upper 10-15% from top */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? "12%" : "10%",
          left: 0,
          right: 0,
          paddingLeft: paddingH,
          paddingRight: paddingH,
          maxWidth: isVertical ? width * 0.82 : width * 0.8,
          marginLeft: "auto",
          marginRight: "auto",
          textAlign: "center",
          zIndex: 5,
        }}
      >
        <span
          style={{
            fontFamily: fontFamily.headline,
            fontSize: headlineFontSize,
            color: colors.gold,
            lineHeight: 1.2,
            display: "block",
            opacity: textOpacity,
          }}
        >
          {slot.copy ?? ""}
        </span>
      </div>

      {/* CIF tag + status badge at bottom-right */}
      {slot.gfx?.cif_tag && (
        <div
          style={{
            position: "absolute",
            bottom: isVertical ? spacing.lg : spacing.md,
            right: isVertical ? spacing.md : spacing.lg,
            opacity: cifOpacity,
            zIndex: 5,
          }}
        >
          <CifTag tag={slot.gfx.cif_tag} status={slot.gfx.status} />
        </div>
      )}

      <BottomUrl />
    </div>
  );
};
