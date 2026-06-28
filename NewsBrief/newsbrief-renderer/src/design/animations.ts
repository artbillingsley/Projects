// src/design/animations.ts
import {spring, SpringConfig} from "remotion";

export const SPRING_ENTER: SpringConfig = {
  damping: 15,
  mass: 0.8,
  stiffness: 180,
  overshootClamping: false,
};

export const SPRING_EXIT: SpringConfig = {
  damping: 20,
  mass: 0.6,
  stiffness: 200,
  overshootClamping: false,
};

export const SPRING_SUBTLE: SpringConfig = {
  damping: 20,
  mass: 1.0,
  stiffness: 120,
  overshootClamping: false,
};

export const HEADLINE_REVEAL_SPEED = 2;
export const CARD_TRANSITION_FRAMES = 8;
export const LOWER_THIRD_DELAY = 15;

export function springIn(frame: number, fps: number, config = SPRING_ENTER) {
  return spring({frame, fps, config, durationInFrames: 30});
}

export function springOut(
  frame: number,
  fps: number,
  startFrame: number,
  config = SPRING_EXIT,
) {
  const localFrame = frame - startFrame;
  if (localFrame < 0) return 1;
  return 1 - spring({frame: localFrame, fps, config, durationInFrames: 20});
}
