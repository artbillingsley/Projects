import React from "react";
import {useCurrentFrame, useVideoConfig, interpolate, staticFile, Img} from "remotion";

interface KenBurnsPhotoProps {
  imageFile: string;  // e.g. "images/hook.jpg"
  height?: string;    // e.g. "45%" — portion of frame
}

export const KenBurnsPhoto: React.FC<KenBurnsPhotoProps> = ({
  imageFile,
  height = "45%",
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Ken Burns: slow zoom from 1.0 to 1.08 + slight horizontal drift
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.08], {
    extrapolateRight: "clamp",
  });
  const translateX = interpolate(frame, [0, durationInFrames], [0, -20], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        width: "100%",
        height,
        overflow: "hidden",
      }}
    >
      {/* Dark gradient overlay at top of photo for text readability */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "40%",
          background: "linear-gradient(to bottom, #0F1419 0%, #0F141900 100%)",
          zIndex: 2,
        }}
      />

      <Img
        src={staticFile(imageFile)}
        style={{
          width: "110%",
          height: "110%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}px)`,
        }}
      />
    </div>
  );
};
