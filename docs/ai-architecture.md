# AI Architecture

> Phase 3 deliverable. Describes the pluggable, assistive AI classification
> layer. **AI is assistive, never authoritative.**

## 1. Principle

The backend decides nothing on AI's word alone. AI suggests; a human confirms or
corrects. Collector corrections are stored as **training candidates**, never
auto-applied as ground truth.

## 2. Flow

```
Photo -> AI prediction -> confidence -> collector confirmation
```

- **High confidence** (>= `AI_CONFIDENCE_THRESHOLD`): suggestion -> collector confirms.
- **Low confidence**: suggestion -> collector manually selects OR "I don't know".
- If necessary: recycler review -> admin review (Phase 5).

The classify endpoint returns a `suggested_action` of `confirm` or `manual`
derived from the confidence thresholds.

## 3. Provider interface (pluggable)

`app/ai/provider.py` defines `BaseProvider` with a single `classify(item, image_id)`
method returning a `ClassificationResult`:

```python
ClassificationResult(
    predicted_category_id, predicted_subcategory_id,
    confidence, detected_material_types, quality_flags,
    provider, model,
)
```

The provider is selected by the `AI_PROVIDER` env var. The default is `none`,
which yields an empty suggestion (confidence 0) and forces manual classification
— matching the "low confidence -> collector selects" rule.

**Real providers (OpenAI/Anthropic/self-hosted) are TODO** — they are added by
implementing `BaseProvider` and registering it. They MUST NOT claim, from an
ordinary photograph: exact gold/silver/copper content, chemical composition,
certified hazardousness, or lab-grade material grade (FR-AI-10).

## 4. Persistence

- `ai_decisions` — one row per prediction: model, image/item, predicted
  category/subcategory, `confidence`, `detected_material_types`, `quality_flags`,
  `valuation_hint`, status (`suggested|confirmed|corrected|rejected`).
- `ai_corrections` — human correction with `is_training_candidate = true`
  (feedback for future model training).
- `ai_models` — provider/model registry (unused until a real provider lands).

## 5. Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/lot-items/{item_id}/classify` | run provider, persist decision, return suggestion + action |
| POST | `/api/v1/ai-decisions/{decision_id}/confirm` | collector confirms; applies predicted category to the item |
| POST | `/api/v1/ai-decisions/{decision_id}/correct` | collector corrects; stores training candidate, applies correction |

Confirm/correct are idempotent-guarded: processing an already-processed decision
returns `409`.

## 6. Media (Cloudinary)

Images never enter PostgreSQL. Flow: **collector -> Cloudinary -> public ID /
URL -> PostgreSQL metadata**. The backend exposes `GET /api/v1/media/upload-params`
(Cloudinary signed-upload parameters) and stores only `cloudinary_public_id` /
`cloudinary_url` on `material_images`.

> **NEEDS VALIDATION**: the signed-upload endpoint requires real Cloudinary
> credentials (`CLOUDINARY_API_SECRET`) and has not been exercised against
> Cloudinary. It returns `503` when unconfigured.

## 7. Open items

- Register a real AI provider + set `AI_PROVIDER`/credentials.
- `valuation_hint` is reserved but not populated (valuation assist, Phase 4).
- Recycler/admin review escalation (Phase 5).
- Image quality-issue detection and flags from a real model.
