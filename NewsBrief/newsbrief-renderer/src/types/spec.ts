import { z } from "zod";

// ---------------------------------------------------------------------------
// WordTiming
// ---------------------------------------------------------------------------
export const WordTimingSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
});
export type WordTiming = z.infer<typeof WordTimingSchema>;

// ---------------------------------------------------------------------------
// ScanItem
// ---------------------------------------------------------------------------
export const ScanItemSchema = z.object({
  number: z.number(),
  copy: z.string(),
  cif_tag: z.string(),
  status: z.string(),
  extractable: z.boolean(),
  clip_id: z.string().nullable(),
  image_file: z.string().optional(),
  fallback_icon: z.string().optional(),
  fallback_data_point: z.string().optional(),
});
export type ScanItem = z.infer<typeof ScanItemSchema>;

// ---------------------------------------------------------------------------
// SlotGfx
// ---------------------------------------------------------------------------
export const SlotGfxSchema = z
  .object({
    cif_tag: z.string().optional(),
    status: z.string().optional(),
    confidence: z.string().optional(),
    sources: z.array(z.string()).optional(),
    headline: z.string().optional(),
  })
  .passthrough();
export type SlotGfx = z.infer<typeof SlotGfxSchema>;

// ---------------------------------------------------------------------------
// Slot
// ---------------------------------------------------------------------------
export const SlotTypeSchema = z.enum([
  "HOOK",
  "LEAD",
  "SCAN",
  "WHY",
  "CLOSE",
]);
export type SlotType = z.infer<typeof SlotTypeSchema>;

export const SlotSchema = z
  .object({
    type: SlotTypeSchema,
    copy: z.string().optional(),
    intro_copy: z.string().optional(),
    items: z.array(ScanItemSchema).optional(),
    audio_file: z.string(),
    words: z.array(WordTimingSchema),
    duration_seconds: z.number(),
    gfx: SlotGfxSchema.optional(),
    extractable: z.boolean().optional(),
    clip_id: z.string().nullable().optional(),
    image_file: z.string().optional(),
    fallback_icon: z.string().optional(),
    fallback_data_point: z.string().optional(),
  })
  .passthrough();
export type Slot = z.infer<typeof SlotSchema>;

// ---------------------------------------------------------------------------
// Clip
// ---------------------------------------------------------------------------
export const ClipSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    slots: z.array(z.string()),
    platform_meta: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough();
export type Clip = z.infer<typeof ClipSchema>;

// ---------------------------------------------------------------------------
// Spec  (top-level render spec)
// ---------------------------------------------------------------------------
export const SpecSchema = z
  .object({
    brief_id: z.union([z.string(), z.number()]),
    date: z.string(),
    issue_number: z.string(),
    slots: z.array(SlotSchema),
    clips: z.array(ClipSchema),
    render_targets: z.array(z.string()),
    requires_review: z.boolean().optional(),
    unknown_words: z.array(z.string()).optional(),
  })
  .passthrough();
export type Spec = z.infer<typeof SpecSchema>;
