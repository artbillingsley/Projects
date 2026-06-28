import React from "react";
import {colors, spacing, fontSize} from "../design/theme";
import {fontFamily} from "../design/fonts";

interface CifTagProps {
  tag: string;
  status?: string;
}

export const CifTag: React.FC<CifTagProps> = ({tag, status}) => {
  const statusColor = status === "DEVELOPING" ? colors.developing : colors.new;

  return (
    <div style={{display: "flex", gap: spacing.sm, alignItems: "center"}}>
      <span style={{
        fontFamily: fontFamily.mono,
        fontSize: fontSize.tagSmall,
        color: colors.secondaryText,
        backgroundColor: "rgba(255,255,255,0.05)",
        padding: "4px 12px",
        borderRadius: 4,
      }}>
        [{tag}]
      </span>
      {status && (
        <span style={{
          fontFamily: fontFamily.mono,
          fontSize: fontSize.tagSmall - 4,
          color: statusColor,
          backgroundColor: `${statusColor}20`,
          padding: "4px 10px",
          borderRadius: 4,
          textTransform: "uppercase" as const,
        }}>
          {status}
        </span>
      )}
    </div>
  );
};
