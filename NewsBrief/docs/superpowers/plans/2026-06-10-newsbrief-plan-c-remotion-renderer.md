# NewsBrief Plan C: Remotion Renderer Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Remotion (React/TypeScript) project that consumes the JSON spec from Plan B and renders the anchor video (16:9 + 9:16), micro-clips, captions, and thumbnail. This is the visual engine — no talking head, so every frame must signal intelligence-grade credibility.

**Architecture:** A Remotion project with typed compositions (AnchorBrief, MicroClip, Thumbnail), per-slot React components (Hook, Lead, Scan, WhyItMatters, Close), a shared design system (theme, fonts, animation presets), and a render script called by the Python orchestrator via subprocess. All visual timing is driven by word-level timestamps from the JSON spec — the voice track is the master clock.

**Tech Stack:** Node 20 LTS, TypeScript 5.3, React 18, Remotion 4, Zod (spec validation)

**Depends on:** Plan B (JSON spec format)

---

## File Structure

```
newsbrief-renderer/
  package.json
  tsconfig.json
  remotion.config.ts
  render.sh                         # CLI wrapper called by Python subprocess
  src/
    Root.tsx                        # Entry — registers compositions
    types/
      spec.ts                       # Zod schema matching Python JSON spec
    design/
      theme.ts                      # Colors, spacing
      fonts.ts                      # Font loading (Google Fonts)
      animations.ts                 # Spring presets
    compositions/
      AnchorBrief.tsx               # Full 2-min anchor (sequences all slots)
      MicroClip.tsx                 # Generic clip wrapper (slot + CLOSE)
      Thumbnail.tsx                 # Single-frame thumbnail
    slots/
      Hook.tsx
      Lead.tsx
      Scan.tsx
      WhyItMatters.tsx
      Close.tsx
    components/
      AnimatedText.tsx              # Word-by-word or sentence-by-sentence reveal
      LowerThird.tsx                # Headline + CIF tag + confidence
      CifTag.tsx                    # [CIF-XXXX] badge
      ScanCard.tsx                  # Numbered card for SCAN items
      SourceBar.tsx                 # Source attribution
      ProgressBar.tsx               # Top-of-frame elapsed time
      Wordmark.tsx                  # COGNOSCERE lockup
  public/
    fonts/                          # Self-hosted fonts (DM Serif Display, Inter, JetBrains Mono)
  test/
    benchmark-spec.json             # Test spec for R3 benchmark
```

---

### Task 1: Node Project Scaffolding

**Files:**
- Create: `newsbrief-renderer/package.json`
- Create: `newsbrief-renderer/tsconfig.json`
- Create: `newsbrief-renderer/remotion.config.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "newsbrief-renderer",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "preview": "remotion preview src/Root.tsx",
    "render": "remotion render",
    "upgrade": "remotion upgrade"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/media-utils": "^4.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "remotion": "^4.0.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "typescript": "^5.3.0",
    "prettier": "^3.1.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: Create remotion.config.ts**

```typescript
// remotion.config.ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
```

- [ ] **Step 4: Install dependencies**

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief/newsbrief-renderer
npm install
```

Run: `npx remotion --version`
Expected: `4.x.x`

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p src/{types,design,compositions,slots,components} public/fonts test
```

- [ ] **Step 6: Commit**

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief
git add newsbrief-renderer/package.json newsbrief-renderer/tsconfig.json newsbrief-renderer/remotion.config.ts
git commit -m "feat: Remotion project scaffolding"
```

---

### Task 2: Design System (Theme, Fonts, Animations)

**Files:**
- Create: `newsbrief-renderer/src/design/theme.ts`
- Create: `newsbrief-renderer/src/design/fonts.ts`
- Create: `newsbrief-renderer/src/design/animations.ts`

- [ ] **Step 1: Create theme.ts**

```typescript
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
  // 1080p sizes
  headlineDesktop: 72,
  headlineMobile: 64,
  subheadline: 48,
  body: 40,
  bodySmall: 36,
  tag: 32,
  tagSmall: 28,
  scanNumber: 96,
} as const;
```

- [ ] **Step 2: Create fonts.ts**

```typescript
// src/design/fonts.ts
import { staticFile } from "remotion";

// Fonts loaded via @font-face in a global style component
// For now, use Google Fonts CDN fallback; self-host in public/fonts/ for production
export const fontFamily = {
  headline: '"DM Serif Display", Georgia, serif',
  body: '"Inter", system-ui, sans-serif',
  mono: '"JetBrains Mono", monospace',
  wordmark: '"Franklin Gothic Medium", "Arial Narrow", Arial, sans-serif',
} as const;

export const fontUrls = [
  "https://fonts.googleapis.com/css2?family=DM+Serif+Display&display=swap",
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
  "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap",
];
```

- [ ] **Step 3: Create animations.ts**

```typescript
// src/design/animations.ts
import { spring, SpringConfig } from "remotion";

export const SPRING_ENTER: SpringConfig = {
  damping: 15,
  mass: 0.8,
  stiffness: 180,
};

export const SPRING_EXIT: SpringConfig = {
  damping: 20,
  mass: 0.6,
  stiffness: 200,
};

export const SPRING_SUBTLE: SpringConfig = {
  damping: 20,
  mass: 1.0,
  stiffness: 120,
};

export const HEADLINE_REVEAL_SPEED = 2; // frames per character
export const CARD_TRANSITION_FRAMES = 8; // ~0.27s at 30fps
export const LOWER_THIRD_DELAY = 15; // frames after slot start

export function springIn(frame: number, fps: number, config = SPRING_ENTER) {
  return spring({ frame, fps, config, durationInFrames: 30 });
}

export function springOut(
  frame: number,
  fps: number,
  startFrame: number,
  config = SPRING_EXIT
) {
  const localFrame = frame - startFrame;
  if (localFrame < 0) return 1;
  return 1 - spring({ frame: localFrame, fps, config, durationInFrames: 20 });
}
```

- [ ] **Step 4: Commit**

```bash
git add newsbrief-renderer/src/design/
git commit -m "feat: design system — colors, fonts, spring animations"
```

---

### Task 3: Spec Types (Zod Schema)

**Files:**
- Create: `newsbrief-renderer/src/types/spec.ts`

- [ ] **Step 1: Create Zod schema matching Python JSON spec**

```typescript
// src/types/spec.ts
import { z } from "zod";

export const WordTimingSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
});

export const ScanItemSchema = z.object({
  number: z.number(),
  copy: z.string(),
  cif_tag: z.string(),
  status: z.string(),
  extractable: z.boolean(),
  clip_id: z.string().nullable(),
});

export const SlotGfxSchema = z.object({
  cif_tag: z.string().optional(),
  status: z.string().optional(),
  confidence: z.string().optional(),
  sources: z.array(z.string()).optional(),
  headline: z.string().optional(),
}).passthrough();

export const SlotSchema = z.object({
  type: z.enum(["HOOK", "LEAD", "SCAN", "WHY", "CLOSE"]),
  copy: z.string().optional(),
  intro_copy: z.string().optional(),
  items: z.array(ScanItemSchema).optional(),
  audio_file: z.string(),
  words: z.array(WordTimingSchema),
  duration_seconds: z.number(),
  gfx: SlotGfxSchema.optional(),
  extractable: z.boolean().optional(),
  clip_id: z.string().nullable().optional(),
});

export const ClipSchema = z.object({
  id: z.string(),
  title: z.string(),
  slots: z.array(z.string()),
  platform_meta: z.record(z.unknown()).optional(),
});

export const SpecSchema = z.object({
  brief_id: z.number(),
  date: z.string(),
  issue_number: z.string(),
  slots: z.array(SlotSchema),
  clips: z.array(ClipSchema),
  render_targets: z.array(z.string()),
  requires_review: z.boolean().optional(),
  unknown_words: z.array(z.string()).optional(),
});

export type Spec = z.infer<typeof SpecSchema>;
export type Slot = z.infer<typeof SlotSchema>;
export type ScanItem = z.infer<typeof ScanItemSchema>;
export type WordTiming = z.infer<typeof WordTimingSchema>;
export type Clip = z.infer<typeof ClipSchema>;
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief/newsbrief-renderer && npx tsc --noEmit src/types/spec.ts`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add newsbrief-renderer/src/types/
git commit -m "feat: Zod schema for Remotion JSON spec"
```

---

### Task 4: Shared Components

**Files:**
- Create: `newsbrief-renderer/src/components/ProgressBar.tsx`
- Create: `newsbrief-renderer/src/components/CifTag.tsx`
- Create: `newsbrief-renderer/src/components/AnimatedText.tsx`
- Create: `newsbrief-renderer/src/components/Wordmark.tsx`

- [ ] **Step 1: Create ProgressBar**

```tsx
// src/components/ProgressBar.tsx
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../design/theme";

export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, width } = useVideoConfig();
  const progress = frame / durationInFrames;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: width,
        height: 4,
        backgroundColor: "rgba(255,255,255,0.05)",
      }}
    >
      <div
        style={{
          width: `${progress * 100}%`,
          height: "100%",
          backgroundColor: colors.progressBar,
        }}
      />
    </div>
  );
};
```

- [ ] **Step 2: Create CifTag**

```tsx
// src/components/CifTag.tsx
import React from "react";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";

interface CifTagProps {
  tag: string;
  status?: string;
}

export const CifTag: React.FC<CifTagProps> = ({ tag, status }) => {
  const statusColor =
    status === "DEVELOPING" ? colors.developing : colors.new;

  return (
    <div style={{ display: "flex", gap: spacing.sm, alignItems: "center" }}>
      <span
        style={{
          fontFamily: fontFamily.mono,
          fontSize: fontSize.tagSmall,
          color: colors.secondaryText,
          backgroundColor: "rgba(255,255,255,0.05)",
          padding: "4px 12px",
          borderRadius: 4,
        }}
      >
        [{tag}]
      </span>
      {status && (
        <span
          style={{
            fontFamily: fontFamily.mono,
            fontSize: fontSize.tagSmall - 4,
            color: statusColor,
            backgroundColor: `${statusColor}20`,
            padding: "4px 10px",
            borderRadius: 4,
            textTransform: "uppercase",
          }}
        >
          {status}
        </span>
      )}
    </div>
  );
};
```

- [ ] **Step 3: Create AnimatedText**

```tsx
// src/components/AnimatedText.tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";

interface AnimatedTextProps {
  text: string;
  startFrame: number;
  style?: React.CSSProperties;
  revealMode?: "fade" | "sentence";
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  startFrame,
  style,
  revealMode = "fade",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
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
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        fontFamily: fontFamily.body,
        fontSize: fontSize.body,
        color: colors.primaryText,
        lineHeight: 1.5,
        ...style,
      }}
    >
      {text}
    </div>
  );
};
```

- [ ] **Step 4: Create Wordmark**

```tsx
// src/components/Wordmark.tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { colors } from "../design/theme";
import { fontFamily } from "../design/fonts";

export const Wordmark: React.FC<{ startFrame?: number }> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - startFrame;

  const opacity = interpolate(local, [0, fps * 0.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        fontFamily: fontFamily.wordmark,
        fontSize: 56,
        color: colors.gold,
        letterSpacing: 6,
        textTransform: "uppercase",
        textAlign: "center",
      }}
    >
      COGNOSCERE
    </div>
  );
};
```

- [ ] **Step 5: Commit**

```bash
git add newsbrief-renderer/src/components/
git commit -m "feat: shared components — ProgressBar, CifTag, AnimatedText, Wordmark"
```

---

### Task 5: Slot Components (Hook, Lead, Scan, WhyItMatters, Close)

**Files:**
- Create: `newsbrief-renderer/src/slots/Hook.tsx`
- Create: `newsbrief-renderer/src/slots/Lead.tsx`
- Create: `newsbrief-renderer/src/slots/Scan.tsx`
- Create: `newsbrief-renderer/src/slots/WhyItMatters.tsx`
- Create: `newsbrief-renderer/src/slots/Close.tsx`

These are the largest files in the project. Each implements the per-slot visual treatment from Section 4 of the design.

- [ ] **Step 1: Create Hook.tsx**

```tsx
// src/slots/Hook.tsx
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
  staticFile,
} from "remotion";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { CifTag } from "../components/CifTag";
import { ProgressBar } from "../components/ProgressBar";
import type { Slot } from "../types/spec";

interface HookProps {
  slot: Slot;
}

export const Hook: React.FC<HookProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  // Character-by-character reveal timed to audio
  const words = slot.words || [];
  const revealedText = words
    .filter((w) => w.start * fps <= frame)
    .map((w) => w.word)
    .join(" ");

  const tagOpacity = interpolate(frame, [fps * 2, fps * 3], [0, 0.7], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: isVertical ? spacing.lg : spacing.xl,
        position: "relative",
      }}
    >
      <ProgressBar />

      {slot.audio_file && <Audio src={slot.audio_file} />}

      <div
        style={{
          fontFamily: fontFamily.headline,
          fontSize: isVertical ? fontSize.headlineMobile : fontSize.headlineDesktop,
          color: colors.gold,
          textAlign: "center",
          lineHeight: 1.3,
          maxWidth: isVertical ? "90%" : "80%",
        }}
      >
        {revealedText}
      </div>

      {slot.gfx?.cif_tag && (
        <div
          style={{
            position: "absolute",
            bottom: spacing.lg,
            right: spacing.lg,
            opacity: tagOpacity,
          }}
        >
          <CifTag tag={slot.gfx.cif_tag} status={slot.gfx.status} />
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 2: Create Lead.tsx**

```tsx
// src/slots/Lead.tsx
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
} from "remotion";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { CifTag } from "../components/CifTag";
import { ProgressBar } from "../components/ProgressBar";
import { springIn, LOWER_THIRD_DELAY } from "../design/animations";
import type { Slot } from "../types/spec";

interface LeadProps {
  slot: Slot;
}

export const Lead: React.FC<LeadProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const lowerThirdProgress = springIn(
    Math.max(0, frame - LOWER_THIRD_DELAY),
    fps
  );

  // Show sentences progressively based on word timing
  const words = slot.words || [];
  const currentTime = frame / fps;
  const visibleWords = words.filter((w) => w.start <= currentTime);
  const visibleText = visibleWords.map((w) => w.word).join(" ");

  const sources = slot.gfx?.sources || [];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        padding: isVertical ? spacing.md : spacing.lg,
        position: "relative",
      }}
    >
      <ProgressBar />

      {slot.audio_file && <Audio src={slot.audio_file} />}

      {/* Lower Third */}
      <div
        style={{
          opacity: lowerThirdProgress,
          transform: `translateY(${(1 - lowerThirdProgress) * 20}px)`,
          marginTop: spacing.xl,
          marginBottom: spacing.md,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.headline,
            fontSize: isVertical ? fontSize.subheadline - 8 : fontSize.subheadline,
            color: colors.gold,
            lineHeight: 1.2,
            marginBottom: spacing.sm,
          }}
        >
          {slot.gfx?.headline || ""}
        </div>
        {slot.gfx?.cif_tag && (
          <CifTag
            tag={slot.gfx.cif_tag}
            status={slot.gfx.status}
          />
        )}
      </div>

      {/* Body text panel */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: isVertical ? spacing.sm : spacing.lg,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.body,
            fontSize: isVertical ? fontSize.bodySmall : fontSize.body,
            color: colors.primaryText,
            lineHeight: 1.6,
            maxWidth: isVertical ? "95%" : "70%",
          }}
        >
          {visibleText}
        </div>
      </div>

      {/* Source bar */}
      {sources.length > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: spacing.md,
            left: spacing.md,
            fontFamily: fontFamily.body,
            fontSize: fontSize.tagSmall,
            color: colors.secondaryText,
          }}
        >
          {sources.join(" · ")}
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 3: Create Scan.tsx**

```tsx
// src/slots/Scan.tsx
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  Audio,
} from "remotion";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { CifTag } from "../components/CifTag";
import { ProgressBar } from "../components/ProgressBar";
import type { Slot, ScanItem } from "../types/spec";

interface ScanProps {
  slot: Slot;
}

export const Scan: React.FC<ScanProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const items = slot.items || [];
  const words = slot.words || [];
  const currentTime = frame / fps;

  // Find current item based on "One.", "Two." keywords in word timing
  const numberWords = ["One.", "Two.", "Three.", "Four."];
  let currentItemIndex = -1;
  for (const w of words) {
    if (w.start <= currentTime && numberWords.includes(w.word)) {
      const idx = numberWords.indexOf(w.word);
      if (idx > currentItemIndex) currentItemIndex = idx;
    }
  }

  const currentItem = currentItemIndex >= 0 && currentItemIndex < items.length
    ? items[currentItemIndex]
    : null;

  const bgColor =
    currentItemIndex % 2 === 0 ? colors.background : colors.surfaceAlt;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: bgColor,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: isVertical ? spacing.md : spacing.lg,
        position: "relative",
      }}
    >
      <ProgressBar />

      {slot.audio_file && <Audio src={slot.audio_file} />}

      {currentItem ? (
        <>
          <div
            style={{
              fontFamily: fontFamily.mono,
              fontSize: fontSize.scanNumber,
              color: colors.gold,
              marginBottom: spacing.md,
            }}
          >
            {currentItem.number}
          </div>

          <div
            style={{
              fontFamily: fontFamily.body,
              fontWeight: 500,
              fontSize: isVertical ? fontSize.bodySmall : fontSize.body,
              color: colors.primaryText,
              textAlign: "center",
              lineHeight: 1.5,
              maxWidth: isVertical ? "90%" : "70%",
              marginBottom: spacing.lg,
            }}
          >
            {currentItem.copy}
          </div>

          <CifTag tag={currentItem.cif_tag} status={currentItem.status} />
        </>
      ) : (
        // Intro card ("Four more, fast.")
        <div
          style={{
            fontFamily: fontFamily.headline,
            fontSize: fontSize.subheadline,
            color: colors.gold,
            textAlign: "center",
          }}
        >
          {slot.intro_copy}
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 4: Create WhyItMatters.tsx**

```tsx
// src/slots/WhyItMatters.tsx
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
} from "remotion";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { ProgressBar } from "../components/ProgressBar";
import type { Slot } from "../types/spec";

interface WhyProps {
  slot: Slot;
}

export const WhyItMatters: React.FC<WhyProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isVertical = height > width;

  const words = slot.words || [];
  const currentTime = frame / fps;
  const visibleText = words
    .filter((w) => w.start <= currentTime)
    .map((w) => w.word)
    .join(" ");

  const headerOpacity = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: colors.surface,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: isVertical ? spacing.lg : spacing.xl,
        position: "relative",
      }}
    >
      <ProgressBar />

      {slot.audio_file && <Audio src={slot.audio_file} />}

      <div
        style={{
          opacity: headerOpacity,
          fontFamily: fontFamily.mono,
          fontSize: fontSize.tag,
          color: colors.gold,
          letterSpacing: 3,
          textTransform: "uppercase",
          marginBottom: spacing.lg,
        }}
      >
        WHY IT MATTERS
      </div>

      <div
        style={{
          fontFamily: fontFamily.body,
          fontWeight: 500,
          fontSize: isVertical ? fontSize.body : fontSize.subheadline,
          color: colors.primaryText,
          textAlign: "center",
          lineHeight: 1.6,
          maxWidth: isVertical ? "90%" : "70%",
        }}
      >
        {visibleText}
      </div>
    </div>
  );
};
```

- [ ] **Step 5: Create Close.tsx**

```tsx
// src/slots/Close.tsx
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
} from "remotion";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { Wordmark } from "../components/Wordmark";
import { ProgressBar } from "../components/ProgressBar";
import type { Slot } from "../types/spec";

interface CloseProps {
  slot: Slot;
}

export const Close: React.FC<CloseProps> = ({ slot }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // "Decide." appears in last 1.5 seconds
  const decideFrame = durationInFrames - Math.round(fps * 1.5);
  const decideOpacity = interpolate(
    frame,
    [decideFrame, decideFrame + fps * 0.3],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const ctaOpacity = interpolate(frame, [fps * 0.5, fps * 1.0], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: spacing.xl,
        position: "relative",
      }}
    >
      {slot.audio_file && <Audio src={slot.audio_file} />}

      <Wordmark />

      <div
        style={{
          opacity: ctaOpacity,
          marginTop: spacing.lg,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.body,
            fontSize: fontSize.bodySmall,
            color: colors.secondaryText,
            marginBottom: spacing.xs,
          }}
        >
          cifaas.cognoscerellc.com
        </div>
        <div
          style={{
            fontFamily: fontFamily.body,
            fontSize: fontSize.bodySmall,
            color: colors.secondaryText,
          }}
        >
          Read the full record.
        </div>
      </div>

      <div
        style={{
          opacity: decideOpacity,
          marginTop: spacing.xl,
          fontFamily: fontFamily.headline,
          fontSize: fontSize.headlineDesktop,
          color: colors.gold,
        }}
      >
        Decide.
      </div>
    </div>
  );
};
```

- [ ] **Step 6: Commit**

```bash
git add newsbrief-renderer/src/slots/
git commit -m "feat: slot components — Hook, Lead, Scan, WhyItMatters, Close"
```

---

### Task 6: Compositions + Root

**Files:**
- Create: `newsbrief-renderer/src/compositions/AnchorBrief.tsx`
- Create: `newsbrief-renderer/src/compositions/MicroClip.tsx`
- Create: `newsbrief-renderer/src/compositions/Thumbnail.tsx`
- Create: `newsbrief-renderer/src/Root.tsx`

- [ ] **Step 1: Create AnchorBrief.tsx**

```tsx
// src/compositions/AnchorBrief.tsx
import React from "react";
import { Series, Audio } from "remotion";
import { Hook } from "../slots/Hook";
import { Lead } from "../slots/Lead";
import { Scan } from "../slots/Scan";
import { WhyItMatters } from "../slots/WhyItMatters";
import { Close } from "../slots/Close";
import type { Spec, Slot } from "../types/spec";

export const AnchorBrief: React.FC<{ spec: Spec }> = ({ spec }) => {
  const slotByType = (type: string): Slot | undefined =>
    spec.slots.find((s) => s.type === type);

  const hook = slotByType("HOOK");
  const lead = slotByType("LEAD");
  const scan = slotByType("SCAN");
  const why = slotByType("WHY");
  const close = slotByType("CLOSE");

  const fps = 30;
  const gap = 9; // 0.3s silence between slots

  return (
    <Series>
      {hook && (
        <Series.Sequence durationInFrames={Math.round(hook.duration_seconds * fps)}>
          <Hook slot={hook} />
        </Series.Sequence>
      )}
      <Series.Sequence durationInFrames={gap}><div /></Series.Sequence>
      {lead && (
        <Series.Sequence durationInFrames={Math.round(lead.duration_seconds * fps)}>
          <Lead slot={lead} />
        </Series.Sequence>
      )}
      <Series.Sequence durationInFrames={gap}><div /></Series.Sequence>
      {scan && (
        <Series.Sequence durationInFrames={Math.round(scan.duration_seconds * fps)}>
          <Scan slot={scan} />
        </Series.Sequence>
      )}
      <Series.Sequence durationInFrames={gap}><div /></Series.Sequence>
      {why && (
        <Series.Sequence durationInFrames={Math.round(why.duration_seconds * fps)}>
          <WhyItMatters slot={why} />
        </Series.Sequence>
      )}
      <Series.Sequence durationInFrames={gap}><div /></Series.Sequence>
      {close && (
        <Series.Sequence durationInFrames={Math.round(close.duration_seconds * fps)}>
          <Close slot={close} />
        </Series.Sequence>
      )}
    </Series>
  );
};
```

- [ ] **Step 2: Create MicroClip.tsx**

```tsx
// src/compositions/MicroClip.tsx
import React from "react";
import { Series } from "remotion";
import { Hook } from "../slots/Hook";
import { Lead } from "../slots/Lead";
import { Scan } from "../slots/Scan";
import { WhyItMatters } from "../slots/WhyItMatters";
import { Close } from "../slots/Close";
import type { Spec, Slot } from "../types/spec";

const SlotRenderer: React.FC<{ slot: Slot }> = ({ slot }) => {
  switch (slot.type) {
    case "HOOK": return <Hook slot={slot} />;
    case "LEAD": return <Lead slot={slot} />;
    case "SCAN": return <Scan slot={slot} />;
    case "WHY": return <WhyItMatters slot={slot} />;
    case "CLOSE": return <Close slot={slot} />;
    default: return <div />;
  }
};

interface MicroClipProps {
  spec: Spec;
  clipId: string;
}

export const MicroClip: React.FC<MicroClipProps> = ({ spec, clipId }) => {
  const clip = spec.clips.find((c) => c.id === clipId);
  if (!clip) return <div />;

  const closeSlot = spec.slots.find((s) => s.type === "CLOSE");
  const fps = 30;

  // For C1: include HOOK + LEAD + WHY
  // For scan clips: include just that scan item (simplified: full SCAN slot)
  // This is a simplified version; production would extract individual scan items
  const slotTypes = clip.slots.map((s) => s.replace("_COMPRESSED", "").replace("_TAIL", "").split("_")[0]);
  const uniqueTypes = [...new Set(slotTypes)];

  const contentSlots = uniqueTypes
    .map((type) => spec.slots.find((s) => s.type === type.toUpperCase()))
    .filter(Boolean) as Slot[];

  return (
    <Series>
      {contentSlots.map((slot, i) => (
        <Series.Sequence
          key={i}
          durationInFrames={Math.round(slot.duration_seconds * fps)}
        >
          <SlotRenderer slot={slot} />
        </Series.Sequence>
      ))}
      {closeSlot && (
        <Series.Sequence durationInFrames={Math.round(closeSlot.duration_seconds * fps)}>
          <Close slot={closeSlot} />
        </Series.Sequence>
      )}
    </Series>
  );
};
```

- [ ] **Step 3: Create Thumbnail.tsx**

```tsx
// src/compositions/Thumbnail.tsx
import React from "react";
import { colors, spacing } from "../design/theme";
import { fontFamily, fontSize } from "../design/fonts";
import { CifTag } from "../components/CifTag";
import { Wordmark } from "../components/Wordmark";
import type { Spec } from "../types/spec";

export const Thumbnail: React.FC<{ spec: Spec }> = ({ spec }) => {
  const hookSlot = spec.slots.find((s) => s.type === "HOOK");
  const hookText = hookSlot?.copy || "";
  const cifTag = hookSlot?.gfx?.cif_tag || "";
  const status = hookSlot?.gfx?.status || "";

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: colors.background,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: spacing.xl * 2,
        position: "relative",
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.headline,
          fontSize: fontSize.headlineDesktop,
          color: colors.gold,
          textAlign: "center",
          lineHeight: 1.3,
          maxWidth: "80%",
          marginBottom: spacing.lg,
        }}
      >
        {hookText}
      </div>

      {cifTag && <CifTag tag={cifTag} status={status} />}

      <div style={{ position: "absolute", bottom: spacing.xl }}>
        <Wordmark startFrame={0} />
      </div>
    </div>
  );
};
```

- [ ] **Step 4: Create Root.tsx**

```tsx
// src/Root.tsx
import { Composition, getInputProps } from "remotion";
import { AnchorBrief } from "./compositions/AnchorBrief";
import { MicroClip } from "./compositions/MicroClip";
import { Thumbnail } from "./compositions/Thumbnail";
import { SpecSchema } from "./types/spec";
import type { Spec } from "./types/spec";

const FPS = 30;

// Parse and validate spec from props
function getSpec(): Spec {
  const props = getInputProps();
  if (props && typeof props === "object" && "brief_id" in props) {
    return SpecSchema.parse(props);
  }
  // Fallback for preview mode
  return {
    brief_id: 0,
    date: "2026-01-01",
    issue_number: "N000",
    slots: [],
    clips: [],
    render_targets: [],
  };
}

export const RemotionRoot: React.FC = () => {
  const spec = getSpec();

  // Calculate total duration from slots
  const totalDurationSeconds = spec.slots.reduce(
    (sum, s) => sum + s.duration_seconds + 0.3, // 0.3s gap between slots
    0
  );
  const totalFrames = Math.max(Math.round(totalDurationSeconds * FPS), FPS * 10);

  return (
    <>
      <Composition
        id="AnchorBrief"
        component={AnchorBrief}
        durationInFrames={totalFrames}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ spec }}
      />

      <Composition
        id="AnchorBrief9x16"
        component={AnchorBrief}
        durationInFrames={totalFrames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ spec }}
      />

      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={1}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ spec }}
      />

      {spec.clips.map((clip) => (
        <Composition
          key={clip.id}
          id={`Clip-${clip.id}`}
          component={MicroClip}
          durationInFrames={FPS * 30} // 30s default; adjusted at render time
          fps={FPS}
          width={1080}
          height={1920}
          defaultProps={{ spec, clipId: clip.id }}
        />
      ))}
    </>
  );
};

import React from "react";
```

- [ ] **Step 5: Commit**

```bash
git add newsbrief-renderer/src/compositions/ newsbrief-renderer/src/Root.tsx
git commit -m "feat: compositions (AnchorBrief, MicroClip, Thumbnail) + Root entry"
```

---

### Task 7: Render Script + Benchmark Spec

**Files:**
- Create: `newsbrief-renderer/render.sh`
- Create: `newsbrief-renderer/test/benchmark-spec.json`

- [ ] **Step 1: Create render.sh**

```bash
#!/bin/bash
# render.sh — Called by Python orchestrator via subprocess
# Usage: ./render.sh <spec_path> <output_dir>
set -e

SPEC_PATH="$1"
OUTPUT_DIR="$2"

if [ -z "$SPEC_PATH" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: ./render.sh <spec_path> <output_dir>"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "[render] Starting anchor 16:9..."
npx remotion render src/Root.tsx AnchorBrief \
  --props="$SPEC_PATH" \
  --output="$OUTPUT_DIR/anchor-16x9.mp4" \
  --width=1920 --height=1080 --fps=30

echo "[render] Starting anchor 9:16..."
npx remotion render src/Root.tsx AnchorBrief9x16 \
  --props="$SPEC_PATH" \
  --output="$OUTPUT_DIR/anchor-9x16.mp4" \
  --width=1080 --height=1920 --fps=30

echo "[render] Starting thumbnail..."
npx remotion render src/Root.tsx Thumbnail \
  --props="$SPEC_PATH" \
  --output="$OUTPUT_DIR/thumbnail.png" \
  --width=1920 --height=1080 --fps=30 \
  --image-format=png

echo "[render] All renders complete."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x newsbrief-renderer/render.sh
```

- [ ] **Step 3: Create benchmark spec**

```json
{
  "brief_id": 0,
  "date": "2026-01-01",
  "issue_number": "N000",
  "slots": [
    {
      "type": "HOOK",
      "copy": "An American helicopter is down near the Strait of Hormuz.",
      "audio_file": "",
      "words": [
        {"word": "An", "start": 0.0, "end": 0.15},
        {"word": "American", "start": 0.2, "end": 0.7},
        {"word": "helicopter", "start": 0.75, "end": 1.3},
        {"word": "is", "start": 1.35, "end": 1.5},
        {"word": "down", "start": 1.55, "end": 1.9}
      ],
      "duration_seconds": 10.0,
      "gfx": {"cif_tag": "CIF-TEST", "status": "DEVELOPING"}
    },
    {
      "type": "LEAD",
      "copy": "Iran shot down a U.S. Army Apache near the Strait of Hormuz.",
      "audio_file": "",
      "words": [
        {"word": "Iran", "start": 0.0, "end": 0.35},
        {"word": "shot", "start": 0.4, "end": 0.6},
        {"word": "down", "start": 0.65, "end": 0.9}
      ],
      "duration_seconds": 40.0,
      "gfx": {"cif_tag": "CIF-TEST", "status": "DEVELOPING", "confidence": "High", "sources": ["Reuters", "AP"], "headline": "U.S. and Iran Trade Strikes"}
    },
    {
      "type": "SCAN",
      "intro_copy": "Three more, fast.",
      "items": [
        {"number": 1, "copy": "The House sent Trump a seventy billion dollar immigration bill.", "cif_tag": "CIF-T1", "status": "NEW", "extractable": false, "clip_id": null},
        {"number": 2, "copy": "Trump put a housing regulator atop the intelligence community.", "cif_tag": "CIF-T2", "status": "NEW", "extractable": true, "clip_id": "C2"},
        {"number": 3, "copy": "Gas sits at four sixteen a gallon.", "cif_tag": "CIF-T3", "status": "NEW", "extractable": true, "clip_id": "C3"}
      ],
      "audio_file": "",
      "words": [
        {"word": "Three", "start": 0.0, "end": 0.3},
        {"word": "more,", "start": 0.35, "end": 0.5},
        {"word": "fast.", "start": 0.55, "end": 0.8},
        {"word": "One.", "start": 1.0, "end": 1.3}
      ],
      "duration_seconds": 40.0
    },
    {
      "type": "WHY",
      "copy": "Here is the thread. The war near Hormuz is the same war showing up in your gas tank.",
      "audio_file": "",
      "words": [
        {"word": "Here", "start": 0.0, "end": 0.2},
        {"word": "is", "start": 0.25, "end": 0.35},
        {"word": "the", "start": 0.4, "end": 0.5},
        {"word": "thread.", "start": 0.55, "end": 0.9}
      ],
      "duration_seconds": 20.0
    },
    {
      "type": "CLOSE",
      "copy": "That is the brief for January first. Decide.",
      "audio_file": "",
      "words": [
        {"word": "That", "start": 0.0, "end": 0.2},
        {"word": "is", "start": 0.25, "end": 0.35}
      ],
      "duration_seconds": 10.0
    }
  ],
  "clips": [
    {"id": "C1", "title": "Test Lead", "slots": ["HOOK", "LEAD"], "platform_meta": {}},
    {"id": "T0", "title": "One Breath", "slots": ["HOOK"], "platform_meta": {}}
  ],
  "render_targets": ["anchor-16x9", "anchor-9x16", "C1", "T0", "thumbnail"]
}
```

- [ ] **Step 4: Verify Remotion can parse the spec**

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief/newsbrief-renderer
npx remotion render src/Root.tsx Thumbnail \
  --props="./test/benchmark-spec.json" \
  --output="/tmp/newsbrief-test-thumb.png" \
  --width=1920 --height=1080 --fps=30 \
  --image-format=png
```

Expected: A PNG thumbnail file at `/tmp/newsbrief-test-thumb.png`

- [ ] **Step 5: Commit**

```bash
git add newsbrief-renderer/render.sh newsbrief-renderer/test/benchmark-spec.json
git commit -m "feat: render script and benchmark spec for R3 testing"
```

---

### Task 8: Python Render Stage (subprocess bridge)

**Files:**
- Create: `src/stages/render.py`
- Create: `tests/test_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
from unittest.mock import patch, MagicMock
import pytest


def test_render_calls_subprocess_with_correct_args():
    from src.stages.render import render_videos

    with patch("src.stages.render.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        render_videos(
            spec_path="/tmp/spec.json",
            output_dir="/tmp/output",
            renderer_dir="/path/to/newsbrief-renderer",
        )

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "/path/to/newsbrief-renderer/render.sh" in cmd[0] or "render.sh" in " ".join(cmd)


def test_render_raises_on_nonzero_exit():
    from src.stages.render import render_videos, RenderError

    with patch("src.stages.render.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Chromium crash")

        with pytest.raises(RenderError, match="Render failed"):
            render_videos(
                spec_path="/tmp/spec.json",
                output_dir="/tmp/output",
                renderer_dir="/path/to/renderer",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_render.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/render.py
from __future__ import annotations

import os
import subprocess
import time

import structlog

log = structlog.get_logger()


class RenderError(Exception):
    pass


def render_videos(
    spec_path: str,
    output_dir: str,
    renderer_dir: str,
    timeout_seconds: int = 600,
) -> float:
    log.info("render.start", spec=spec_path, output=output_dir)

    render_script = os.path.join(renderer_dir, "render.sh")
    if not os.path.exists(render_script):
        raise RenderError(f"Render script not found: {render_script}")

    t0 = time.monotonic()
    result = subprocess.run(
        [render_script, spec_path, output_dir],
        capture_output=True,
        text=True,
        cwd=renderer_dir,
        timeout=timeout_seconds,
    )

    duration = time.monotonic() - t0

    if result.returncode != 0:
        log.error("render.failed", stderr=result.stderr[:500])
        raise RenderError(f"Render failed (exit {result.returncode}): {result.stderr[:500]}")

    log.info("render.done", duration_s=round(duration, 2))
    return duration
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_render.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/render.py tests/test_render.py
git commit -m "feat: Stage 5 RENDER — subprocess bridge to Remotion"
```

---

## Plan C Completion Checklist

After all tasks are done, verify:

- [ ] `newsbrief-renderer/` is a working Remotion project that installs and compiles
- [ ] Design system (theme, fonts, animations) matches Section 4 spec
- [ ] Zod schema validates the Python-generated JSON spec
- [ ] All 5 slot components render (Hook, Lead, Scan, WhyItMatters, Close)
- [ ] AnchorBrief sequences all slots with silence gaps
- [ ] MicroClip wraps individual slots + Close
- [ ] Thumbnail renders a single-frame PNG
- [ ] `render.sh` is callable from Python via subprocess
- [ ] `src/stages/render.py` bridges Python orchestrator to Remotion
- [ ] Benchmark spec exists for R3 testing

**Next:** Plan D (Distribution + Operations) wires up the publish gate, platform uploads, archiving, and health checks.
