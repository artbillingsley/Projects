import React from "react";
import {colors, spacing} from "../design/theme";
import {fontFamily} from "../design/fonts";

interface FallbackGraphicProps {
  /** Large icon/emoji representing the topic */
  icon?: string;
  /** Key data point or short phrase */
  dataPoint?: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Height of the graphic area */
  height?: string;
}

export const FallbackGraphic: React.FC<FallbackGraphicProps> = ({
  icon = "",
  dataPoint = "",
  subtitle = "",
  height = "45%",
}) => (
  <div
    style={{
      position: "absolute",
      bottom: 0,
      left: 0,
      width: "100%",
      height,
      backgroundColor: "#0A0F14",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      borderTop: `3px solid ${colors.gold}`,
      overflow: "hidden",
    }}
  >
    {/* Subtle diagonal lines pattern for visual texture */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity: 0.04,
        background: `repeating-linear-gradient(
          -45deg,
          transparent,
          transparent 20px,
          ${colors.gold} 20px,
          ${colors.gold} 21px
        )`,
      }}
    />

    {icon && (
      <div style={{fontSize: 80, marginBottom: spacing.md, zIndex: 1}}>
        {icon}
      </div>
    )}
    {dataPoint && (
      <div
        style={{
          fontFamily: fontFamily.headline,
          fontSize: 64,
          color: colors.gold,
          textAlign: "center" as const,
          zIndex: 1,
          padding: `0 ${spacing.lg}px`,
        }}
      >
        {dataPoint}
      </div>
    )}
    {subtitle && (
      <div
        style={{
          fontFamily: fontFamily.mono,
          fontSize: 24,
          color: colors.secondaryText,
          marginTop: spacing.sm,
          textAlign: "center" as const,
          zIndex: 1,
        }}
      >
        {subtitle}
      </div>
    )}
  </div>
);
