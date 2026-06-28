import React from "react";
import {useVideoConfig} from "remotion";
import {CifTag} from "../components/CifTag";
import {Wordmark} from "../components/Wordmark";
import {colors, spacing, fontSize} from "../design/theme";
import {fontFamily} from "../design/fonts";
import type {Spec} from "../types/spec";

interface ThumbnailProps {
  spec: Spec;
}

export const Thumbnail: React.FC<ThumbnailProps> = ({spec}) => {
  const {width, height} = useVideoConfig();
  const isVertical = height > width;

  // Get the HOOK slot for headline text and GFX data
  const hookSlot = spec.slots.find((s) => s.type === "HOOK");
  const hookText = hookSlot?.copy ?? hookSlot?.gfx?.headline ?? "NewsBrief";
  const cifTag = hookSlot?.gfx?.cif_tag;
  const cifStatus = hookSlot?.gfx?.status;

  const headlineFontSize = isVertical ? fontSize.subheadline : fontSize.headlineDesktop;
  const paddingH = isVertical ? spacing.md : spacing.xl;

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
        boxSizing: "border-box" as const,
        paddingLeft: paddingH,
        paddingRight: paddingH,
      }}
    >
      {/* Top accent bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 6,
          backgroundColor: colors.gold,
        }}
      />

      {/* Issue number badge */}
      {spec.issue_number && (
        <div
          style={{
            position: "absolute",
            top: spacing.md,
            left: paddingH,
            fontFamily: fontFamily.mono,
            fontSize: fontSize.tagSmall - 4,
            color: colors.secondaryText,
            letterSpacing: 2,
            textTransform: "uppercase" as const,
          }}
        >
          {spec.issue_number} · {spec.date}
        </div>
      )}

      {/* Central headline — hook text in gold */}
      <div
        style={{
          maxWidth: isVertical ? width * 0.9 : width * 0.75,
          textAlign: "center",
        }}
      >
        <span
          style={{
            fontFamily: fontFamily.headline,
            fontSize: headlineFontSize,
            color: colors.gold,
            lineHeight: 1.2,
            display: "block",
          }}
        >
          {hookText}
        </span>
      </div>

      {/* Bottom row: CIF tag (left) + Wordmark (right) */}
      <div
        style={{
          position: "absolute",
          bottom: isVertical ? spacing.lg : spacing.md,
          left: paddingH,
          right: paddingH,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {cifTag ? (
          <CifTag tag={cifTag} status={cifStatus} />
        ) : (
          <div />
        )}

        {/* Inline wordmark — static (Thumbnail is single-frame, no animation needed) */}
        <div
          style={{
            fontFamily: fontFamily.wordmark,
            fontSize: isVertical ? 36 : 44,
            color: colors.gold,
            letterSpacing: 5,
            textTransform: "uppercase" as const,
          }}
        >
          COGNOSCERE
        </div>
      </div>
    </div>
  );
};
