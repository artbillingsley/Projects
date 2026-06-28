import React from "react";
import { colors, spacing } from "../design/theme";
import { fontFamily } from "../design/fonts";

export const BottomUrl: React.FC = () => (
  <div
    style={{
      position: "absolute",
      bottom: 48,
      left: 0,
      width: "100%",
      textAlign: "center",
      zIndex: 10,
    }}
  >
    <span
      style={{
        fontFamily: fontFamily.mono,
        fontSize: 32,
        fontWeight: "bold" as const,
        color: colors.gold,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        padding: "8px 24px",
        borderRadius: 4,
      }}
    >
      www.cognoscerellc.com
    </span>
  </div>
);
