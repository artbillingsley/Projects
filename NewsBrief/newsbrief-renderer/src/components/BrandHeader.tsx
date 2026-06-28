import React from "react";
import { colors, spacing } from "../design/theme";
import { fontFamily } from "../design/fonts";

interface BrandHeaderProps {
  issueNumber?: string;
}

export const BrandHeader: React.FC<BrandHeaderProps> = ({ issueNumber }) => (
  <div
    style={{
      position: "absolute",
      top: 64,
      left: 64,
      display: "flex",
      alignItems: "center",
      gap: spacing.sm,
      zIndex: 10,
    }}
  >
    <span
      style={{
        fontFamily: fontFamily.wordmark,
        fontSize: 42,
        fontWeight: "bold" as const,
        color: colors.gold,
        letterSpacing: 5,
        textTransform: "uppercase" as const,
      }}
    >
      COGNOSCERE
    </span>
    {issueNumber && (
      <span
        style={{
          fontFamily: fontFamily.mono,
          fontSize: 24,
          color: colors.secondaryText,
        }}
      >
        {issueNumber}
      </span>
    )}
  </div>
);
