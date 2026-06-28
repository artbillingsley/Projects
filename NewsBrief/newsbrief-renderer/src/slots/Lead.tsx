import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors, spacing, fontSize } from "../design/theme";
import { fontFamily } from "../design/fonts";
import { springIn, LOWER_THIRD_DELAY } from "../design/animations";
import { ProgressBar } from "../components/ProgressBar";
import { BrandHeader } from "../components/BrandHeader";
import { BottomUrl } from "../components/BottomUrl";
import { CifTag } from "../components/CifTag";
import { KenBurnsPhoto } from "../components/KenBurnsPhoto";
import { FallbackGraphic } from "../components/FallbackGraphic";
import { Slot } from "../types/spec";

interface LeadProps {
  slot: Slot;
}

export const Lead: React.FC<LeadProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const currentTime = frame / fps;

  // Lower third spring entrance — delay until first word is spoken
  const firstWordStart = slot.words.length > 0 ? slot.words[0].start : 0;
  const firstWordFrame = Math.round(firstWordStart * fps);
  const lowerThirdFrame = Math.max(0, frame - firstWordFrame);
  const lowerThirdY = interpolate(
    springIn(lowerThirdFrame, fps),
    [0, 1],
    [60, 0]
  );
  const lowerThirdOpacity = interpolate(
    springIn(lowerThirdFrame, fps),
    [0, 1],
    [0, 1]
  );

  // Source bar opacity
  const sourceOpacity = interpolate(
    frame - LOWER_THIRD_DELAY - 10,
    [0, 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Body text reveal: use slot.copy (clean, no SSML) shown progressively
  // by sentences timed to word timestamps.
  const bodyText = slot.copy ?? "";
  const sentences = bodyText.match(/[^.!?]+[.!?]+/g) ?? [bodyText];
  const totalWords = slot.words.length;

  // Map sentences to approximate word indices for timing
  let wordIndex = 0;
  const sentenceTimings: { text: string; startTime: number }[] = [];
  for (const sentence of sentences) {
    const approxWordCount = sentence.trim().split(/\s+/).length;
    const startTime =
      wordIndex < totalWords ? slot.words[wordIndex].start : 0;
    sentenceTimings.push({ text: sentence.trim(), startTime });
    wordIndex += approxWordCount;
  }

  const bodyFontSize = isVertical ? fontSize.bodySmall : fontSize.body;
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

      {/* Lower third at TOP: headline + CIF tag */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? 120 : 100,
          left: 0,
          right: 0,
          paddingLeft: paddingH,
          paddingRight: paddingH,
          transform: `translateY(${lowerThirdY}px)`,
          opacity: lowerThirdOpacity,
          zIndex: 5,
        }}
      >
        {slot.gfx?.headline && (
          <div
            style={{
              fontFamily: fontFamily.headline,
              fontSize: isVertical ? fontSize.tag : fontSize.subheadline,
              color: colors.gold,
              marginBottom: spacing.xs,
              lineHeight: 1.2,
            }}
          >
            {slot.gfx.headline}
          </div>
        )}
        {slot.gfx?.cif_tag && (
          <CifTag tag={slot.gfx.cif_tag} status={slot.gfx.status} />
        )}
      </div>

      {/* Body copy — sentence-by-sentence reveal, positioned higher (~17% from top) */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? "17%" : "15%",
          left: 0,
          right: 0,
          paddingLeft: paddingH,
          paddingRight: paddingH,
          zIndex: 5,
        }}
      >
        <p
          style={{
            fontFamily: fontFamily.body,
            fontSize: bodyFontSize,
            color: colors.primaryText,
            lineHeight: 1.6,
            margin: 0,
            maxWidth: isVertical ? "82%" : "75%",
          }}
        >
          {sentenceTimings.map((s, i) => {
            const visible = currentTime >= s.startTime;
            const sentenceOpacity = visible
              ? interpolate(
                  currentTime - s.startTime,
                  [0, 0.4],
                  [0, 1],
                  {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }
                )
              : 0;
            return (
              <span key={i} style={{ opacity: sentenceOpacity }}>
                {(i === 0 ? "" : " ") + s.text}
              </span>
            );
          })}
        </p>
      </div>

      {/* Source bar — prominent attribution for credibility */}
      {slot.gfx?.sources && slot.gfx.sources.length > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: 110,
            left: 0,
            right: 0,
            backgroundColor: "rgba(0,0,0,0.85)",
            paddingTop: spacing.sm,
            paddingBottom: spacing.sm,
            paddingLeft: paddingH,
            paddingRight: paddingH,
            opacity: sourceOpacity,
            display: "flex",
            gap: spacing.sm,
            alignItems: "center",
            zIndex: 5,
          }}
        >
          <span
            style={{
              fontFamily: fontFamily.mono,
              fontSize: fontSize.tagSmall,
              color: colors.gold,
              textTransform: "uppercase" as const,
              letterSpacing: 2,
              fontWeight: "bold" as const,
            }}
          >
            SOURCES:
          </span>
          <span
            style={{
              fontFamily: fontFamily.mono,
              fontSize: fontSize.tagSmall,
              color: colors.primaryText,
            }}
          >
            {slot.gfx.sources.join("  \u00B7  ")}
          </span>
        </div>
      )}

      <BottomUrl />
    </div>
  );
};
