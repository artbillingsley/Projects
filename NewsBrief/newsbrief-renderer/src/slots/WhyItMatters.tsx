import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors, spacing, fontSize } from "../design/theme";
import { fontFamily } from "../design/fonts";
import { springIn } from "../design/animations";
import { ProgressBar } from "../components/ProgressBar";
import { BrandHeader } from "../components/BrandHeader";
import { BottomUrl } from "../components/BottomUrl";
import { KenBurnsPhoto } from "../components/KenBurnsPhoto";
import { FallbackGraphic } from "../components/FallbackGraphic";
import { Slot } from "../types/spec";

interface WhyItMattersProps {
  slot: Slot;
}

export const WhyItMatters: React.FC<WhyItMattersProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const currentTime = frame / fps;

  // Header entrance spring
  const headerEnter = springIn(frame, fps);

  // Body text: use slot.copy (clean, no SSML) shown sentence-by-sentence
  const bodyText = slot.copy ?? "";
  const sentences = bodyText.match(/[^.!?]+[.!?]+/g) ?? [bodyText];
  const totalWords = slot.words.length;

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
  const headerFontSize = isVertical ? fontSize.tagSmall : fontSize.tag;
  const paddingH = isVertical ? spacing.xl : spacing.xl;

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: colors.surface,
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

      {/* "WHY IT MATTERS" header — positioned higher */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? "8%" : "8%",
          left: 0,
          right: 0,
          paddingLeft: paddingH,
          paddingRight: paddingH,
          opacity: headerEnter,
          transform: `translateY(${(1 - headerEnter) * 20}px)`,
          zIndex: 5,
        }}
      >
        <span
          style={{
            fontFamily: fontFamily.mono,
            fontSize: headerFontSize,
            color: colors.gold,
            textTransform: "uppercase" as const,
            letterSpacing: 4,
            fontVariant: "small-caps",
            display: "block",
          }}
        >
          WHY IT MATTERS
        </span>
        <div
          style={{
            marginTop: spacing.xs,
            width: 60,
            height: 2,
            backgroundColor: colors.gold,
            opacity: 0.6,
          }}
        />
      </div>

      {/* Synthesis text — sentence-by-sentence reveal, positioned higher */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? "15%" : "15%",
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
            lineHeight: 1.7,
            margin: 0,
            maxWidth: isVertical ? "82%" : "70%",
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

      <BottomUrl />
    </div>
  );
};
