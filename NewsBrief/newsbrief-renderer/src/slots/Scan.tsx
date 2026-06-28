import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors, spacing, fontSize } from "../design/theme";
import { fontFamily } from "../design/fonts";
import { ProgressBar } from "../components/ProgressBar";
import { BrandHeader } from "../components/BrandHeader";
import { BottomUrl } from "../components/BottomUrl";
import { CifTag } from "../components/CifTag";
import { KenBurnsPhoto } from "../components/KenBurnsPhoto";
import { FallbackGraphic } from "../components/FallbackGraphic";
import { Slot, ScanItem, WordTiming } from "../types/spec";

interface ScanProps {
  slot: Slot;
}

const NUMBER_WORDS: Record<string, number> = {
  // Only match with punctuation — bare "Four" in "Four more, fast" is NOT a card number
  "One.": 1,
  "Two.": 2,
  "Three.": 3,
  "Four.": 4,
  "One,": 1,
  "Two,": 2,
  "Three,": 3,
  "Four,": 4,
};

const ORDINAL_LABELS: Record<number, string> = {
  1: "01",
  2: "02",
  3: "03",
  4: "04",
};

/**
 * Determine which scan item is currently active based on word timestamps.
 * Returns -1 during the intro (before the first numbered word is reached).
 * This ensures no card flashes before card 1.
 */
function getCurrentItemIndex(words: WordTiming[], currentTime: number): number {
  // Find the first numbered word in the entire word list
  let firstNumberedWordStart = Infinity;
  for (const w of words) {
    if (NUMBER_WORDS[w.word] !== undefined) {
      firstNumberedWordStart = w.start;
      break;
    }
  }

  // If we haven't reached the first numbered word yet, show intro
  if (currentTime < firstNumberedWordStart) {
    return -1;
  }

  // Walk through words up to currentTime and track the latest numbered word
  let activeIndex = -1;
  for (const w of words) {
    if (w.start > currentTime) break;
    const n = NUMBER_WORDS[w.word];
    if (n !== undefined) {
      activeIndex = n - 1; // 0-based
    }
  }
  return activeIndex;
}

export const Scan: React.FC<ScanProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const currentTime = frame / fps;
  const items: ScanItem[] = slot.items ?? [];

  const activeIndex = getCurrentItemIndex(slot.words, currentTime);
  const isIntro = activeIndex < 0;

  // Background alternates per item
  const bgColor =
    isIntro
      ? colors.background
      : activeIndex % 2 === 0
      ? colors.background
      : colors.surfaceAlt;

  const numberFontSize = isVertical ? fontSize.scanNumber * 0.75 : fontSize.scanNumber;
  const bodyFontSize = isVertical ? fontSize.bodySmall : fontSize.body;
  const paddingH = isVertical ? spacing.xl : spacing.xl;

  const activeItem: ScanItem | undefined =
    activeIndex >= 0 ? items[activeIndex] : undefined;

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: bgColor,
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
        transition: "background-color 0s", // hard cuts — no CSS transition
      }}
    >
      <ProgressBar />
      <BrandHeader />

      {/* Ken Burns photo or fallback — per item for scan cards */}
      {(() => {
        // Use active item image if available, else slot-level, else fallback
        const itemImg = activeItem?.image_file;
        const slotImg = slot.image_file;
        const imgFile = itemImg || slotImg;
        const fbIcon = activeItem?.fallback_icon || slot.fallback_icon;
        const fbData = activeItem?.fallback_data_point || slot.fallback_data_point;
        if (imgFile) {
          return <KenBurnsPhoto imageFile={imgFile} height="45%" />;
        }
        return <FallbackGraphic icon={fbIcon} dataPoint={fbData} height="45%" />;
      })()}

      {isIntro ? (
        /* Intro state: show intro_copy — positioned in upper portion */
        <div
          style={{
            position: "absolute",
            top: isVertical ? "10%" : "8%",
            left: 0,
            right: 0,
            paddingLeft: paddingH,
            paddingRight: paddingH,
            textAlign: "center",
            zIndex: 5,
          }}
        >
          <p
            style={{
              fontFamily: fontFamily.body,
              fontSize: bodyFontSize,
              color: colors.secondaryText,
              lineHeight: 1.5,
              margin: 0,
            }}
          >
            {slot.intro_copy ?? ""}
          </p>
        </div>
      ) : (
        /* Active item state — positioned in upper portion */
        <div
          style={{
            position: "absolute",
            top: isVertical ? "10%" : "8%",
            left: 0,
            right: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            paddingLeft: paddingH,
            paddingRight: paddingH,
            gap: spacing.md,
            zIndex: 5,
          }}
        >
          {/* Large gold number */}
          {activeIndex >= 0 && (
            <span
              style={{
                fontFamily: fontFamily.headline,
                fontSize: numberFontSize,
                color: colors.gold,
                lineHeight: 1,
                fontWeight: "bold",
              }}
            >
              {ORDINAL_LABELS[activeIndex + 1] ?? String(activeIndex + 1).padStart(2, "0")}
            </span>
          )}

          {/* Story text */}
          {activeItem && (
            <p
              style={{
                fontFamily: fontFamily.body,
                fontSize: bodyFontSize,
                color: colors.primaryText,
                lineHeight: 1.5,
                textAlign: "center",
                margin: 0,
                maxWidth: isVertical ? width * 0.82 : width * 0.75,
              }}
            >
              {activeItem.copy}
            </p>
          )}

          {/* CIF tag per item */}
          {activeItem && (
            <CifTag tag={activeItem.cif_tag} status={activeItem.status} />
          )}
        </div>
      )}

      <BottomUrl />
    </div>
  );
};
