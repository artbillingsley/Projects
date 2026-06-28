import React from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {colors} from "../design/theme";

export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames, width} = useVideoConfig();
  const progress = frame / durationInFrames;

  return (
    <div style={{position: "absolute", top: 0, left: 0, width, height: 4, backgroundColor: "rgba(255,255,255,0.05)"}}>
      <div style={{width: `${progress * 100}%`, height: "100%", backgroundColor: colors.progressBar}} />
    </div>
  );
};
