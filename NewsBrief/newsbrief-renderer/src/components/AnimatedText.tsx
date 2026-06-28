import React from "react";
import {useCurrentFrame, useVideoConfig, interpolate} from "remotion";
import {colors, fontSize} from "../design/theme";
import {fontFamily} from "../design/fonts";

interface AnimatedTextProps {
  text: string;
  startFrame: number;
  style?: React.CSSProperties;
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({text, startFrame, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const localFrame = frame - startFrame;

  const opacity = interpolate(localFrame, [0, fps * 0.3], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(localFrame, [0, fps * 0.3], [12, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{
      opacity,
      transform: `translateY(${translateY}px)`,
      fontFamily: fontFamily.body,
      fontSize: fontSize.body,
      color: colors.primaryText,
      lineHeight: 1.5,
      ...style,
    }}>
      {text}
    </div>
  );
};
