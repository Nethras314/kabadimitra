# Dataset Strategy

> How Kabadi Mitra collects the feedback data it needs to train its AI
> classifier and seed its pricing engine — without ever treating unverified
> human or AI output as ground truth.

## 1. Principle

The product is designed to **generate its own training signal** as a by-product
of normal use. Nothing collected this way is automatically ground truth:
corrections and observations are **candidates** that require review before any
training use.

## 2. Data streams

### 2.1 AI classification corrections

- **Source**: collector confirm/correct actions (`ai_decisions` →
  `ai_corrections`).
- **Captured**: `corrected_category_id`, `corrected_subcategory_id`,
  `correction_type`, `is_training_candidate` (forced `true`).
- **Purpose**: labelled examples linking an image to a human-confirmed category.
- **Status**: **IMPLEMENTED** (storage + forced flag); model training is **FUTURE**.
- **RTM**: FR-020, FR-063.

### 2.2 Price observations (provenance-backed)

- **Source**: collector entries, recycler quotes, market data, verification.
- **Captured**: material, subcategory, grade, location, timestamp, source,
  buyer, weight, transport, verification status, unit, confidence.
- **Purpose**: seed the pricing engine (contextual estimates, price history).
- **Status**: **IMPLEMENTED** (recording + provenance).
- **RTM**: FR-024, FR-025, FR-064.

### 2.3 Image quality flags

- **Source**: the classifier's `quality_flags` field on `ai_decisions`.
- **Purpose**: tune an image-quality detector.
- **Status**: **PARTIAL** — field exists in schema, but only a real AI provider
  populates it (currently `NullProvider`).
- **RTM**: FR-016, FR-065.

## 3. Guardrails

1. **Corrections are never auto-ground-truth** — `is_training_candidate` is
   forced `true`; human review is required before use (FR-020, AT-011).
2. **Collector buyer prices are `unverified` observations**, not authoritative
   market prices (FR-025).
3. **AI never claims composition/grade** — the provider contract prevents
   storing an AI assertion of exact composition, precious-metal content, or
   certified hazardousness (FR-021).
4. **No Aadhaar / minimal PII** — training data is not keyed to sensitive
   identity (FR-060, FR-061).

## 4. Derived aggregates

- `price_history` (period averages, min/max, sample count) is the intended
  consumption surface for training and analytics. **Status: PARTIAL** — table
  exists, no derivation job populates it yet (FR-066).

## 5. What is NOT collected / not yet built

- No automatic dataset export pipeline.
- No model-training pipeline.
- No `price_history` derivation worker (Redis-reserved).
- No labelled dataset bootstrap (the taxonomy seeds are reference data, not
  training images).

## 6. Status summary

| Stream | Storage | Flag/training | Status |
| ------ | ------- | ------------- | ------ |
| AI corrections | `ai_corrections` | `is_training_candidate=true` | IMPLEMENTED |
| Price observations | `price_observations` | provenance + `verification_status` | IMPLEMENTED |
| Image quality flags | `ai_decisions.quality_flags` | field only | PARTIAL |
| Price-history aggregates | `price_history` | table only | PARTIAL |
| Dataset export / training pipeline | — | — | FUTURE |
