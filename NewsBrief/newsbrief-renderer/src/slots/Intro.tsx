import React from "react";
import { Img, staticFile, useVideoConfig, interpolate, useCurrentFrame } from "remotion";
import { colors } from "../design/theme";

interface IntroProps {
  thumbnailFile: string;
}

export const Intro: React.FC<IntroProps> = ({ thumbnailFile }) => {
  const { width, height, fps } = useVideoConfig();
  const frame = useCurrentFrame();

  // Fade in over 0.3s, hold, fade out over 0.3s at end
  const fadeIn = interpolate(frame, [0, Math.round(fps * 0.3)], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: colors.background,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeIn,
      }}
    >
      <Img
        src={staticFile(thumbnailFile)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </div>
  );
};
