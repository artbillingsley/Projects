import React from "react";
import {useCurrentFrame, useVideoConfig, interpolate} from "remotion";
import {colors} from "../design/theme";
import {fontFamily} from "../design/fonts";

export const Wordmark: React.FC<{startFrame?: number}> = ({startFrame = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startFrame;

  const opacity = interpolate(local, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{
      opacity,
      fontFamily: fontFamily.wordmark,
      fontSize: 56,
      color: colors.gold,
      letterSpacing: 6,
      textTransform: "uppercase" as const,
      textAlign: "center" as const,
    }}>
      COGNOSCERE
    </div>
  );
};
