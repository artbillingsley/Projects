// src/design/theme.ts

export const colors = {
  background: "#0F1419",
  surface: "#1A2332",
  surfaceAlt: "#141E2B",
  primaryText: "#F5F0E8",
  secondaryText: "#9BA8B7",
  gold: "#C9A227",
  developing: "#D4855A",
  new: "#4A9B8E",
  confidence: "#6B7D5E",
  red: "#C75050",
  progressBar: "rgba(201, 162, 39, 0.4)",
} as const;

export const spacing = {
  xs: 8,
  sm: 16,
  md: 24,
  lg: 40,
  xl: 64,
} as const;

export const fontSize = {
  headlineDesktop: 94,
  headlineMobile: 83,
  subheadline: 53,
  body: 44,
  bodySmall: 40,
  tag: 36,
  tagSmall: 31,
  scanNumber: 106,
} as const;
