# Field Pilot

> Phase 9 deliverable. Plan for validating the product in the field. **Many
> parameters are placeholders and need validation before a real pilot.**

## Goal

Validate the collector-first workflow end-to-end with a small set of real
collectors and at least one authorized recycler, and collect the feedback data
the system is designed to learn from.

## Scope (proposed)

- **Participants**: ~10–20 pickers/kabadiwalas, 1–2 aggregators, 1 verified
  recycler, 1 platform admin.
- **Locales**: pilot in 1–2 languages first (Hindi + English), expand after.
- **Geography**: one city/region to keep recycler service areas simple.

## Success metrics (to be defined)

- % of captures classified correctly with a single collector confirmation.
- Time from capture to a matched recycler quote.
- % of lots reaching `COMPLETED` (payment recorded).
- % of price observations sourced from `verification` (vs. collector entry).

## Data to collect

- **AI corrections** as training candidates (never auto-ground-truth).
- **Price observations** with full provenance to seed the pricing engine.
- **Image quality flags** to tune the AI quality detector.

## Open questions / needs validation

- Pilot sample size and duration.
- Whether digital payment (UPI) is acceptable, or cash-first.
- Recycler service-area definition (radius vs. polygon) per region.
- Regulatory/authorization documentation required for recycler onboarding.
