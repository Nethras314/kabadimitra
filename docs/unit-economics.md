# Unit Economics Assessment

> Spec deliverable: "a short unit-economics assessment comparing the collector's
> existing earnings with the potential earnings through the proposed platform
> and explaining how the platform can sustain its operations."

> **EVIDENCE STATUS: MODEL, NOT MEASUREMENT.** No field research has been
> conducted. Every collector-side figure below is a **planning assumption** taken
> from public scrap-market rates, not observed data. Nothing here should be
> quoted as a finding. The parameters are marked and must be replaced with
> field data (see §6) before any funding or policy decision.

## 1. The economic problem

A collector today sells to the nearest available buyer, usually an aggregator or
kabadiwala who knows roughly what the material is worth but not what the
downstream recycler pays. The gap between those two numbers is the collector's
unrealised margin.

The platform does three things economically:

1. **Price transparency** — the collector sees a defensible market range before
   selling, so the price is negotiated from a position other than ignorance.
2. **Formal route access** — selling to a verified recycler directly removes one
   or more intermediary margins.
3. **Reduced information cost** — less time spent finding buyers, less exposure
   to unsafe processing in between.

## 2. Collector-side model (per lot)

Assumptions, illustrative:

| Parameter | Value | Note |
|---|---|---|
| Lots collected per working day | 2–4 | **Assumption** |
| Mixed weight per lot | 15–30 kg | **Assumption** |
| Material mix (by weight) | ~50% mixed metal, ~25% cable, ~15% equipment, ~10% plastics | **Assumption** |
| Blended market rate | ~₹95/kg (Pune reference seed) | From seeded observations, not a live quote |
| Transport cost to recycler | ₹40–80 per lot | **Assumption** |
| Time cost of an extra aggregation hop | ₹100–200 per lot | **Assumption** |

Resulting ranges per lot (indicative):

| Path | Revenue/collector | Margin/collector |
|---|---|---|
| Current: sell to aggregator | ₹1,200–2,400 | Baseline |
| Platform: sell to verified recycler | ₹1,400–2,700 | +₹150–300 per lot |

**Effect size: roughly +12–15% on a lot, or ₹300–1,000 per working day.** This
is the honest magnitude: meaningful, but not transformative per unit. The larger
argument is cumulative (formalisation, traceability, safety) rather than a
step-change in daily income.

## 3. Platform unit economics

Revenue model options:

- **Take rate on transaction** (1–3% of material value). At 1.5% of ~₹2,000 per
  lot → **₹30/lot**. At 2 lots/collector/day × 26 days × 10,000 collectors →
  ~₹1.56 Cr/year. Requires ~10k active collectors.
- **Recycler subscription** (₹500–2,000/month per facility for verified
  listings, price data, and matched leads). At ₹1,000/month × 200 recyclers →
  ₹24 L/year — insufficient alone; needs volume.
- **EPR / producer-funded channel** (likely the strongest route in India).
  Producers with EPR obligations can fund the aggregation of informal supply.
  Not modelled here — requires institutional engagement.

Fixed cost baseline (indicative, monthly): cloud ~₹8–15k, engineering ~₹4–6 L,
field ops/verification ~₹1–2 L. **A pure transaction take-rate does not cover
this at pilot scale**; the realistic path is blended funder revenue or
EPR-linked funding.

## 4. What the platform must do to sustain itself

- **Verify recyclers properly.** If a listed recycler is not actually
  authorized, the platform's central claim fails and collectors lose trust.
  Verification is a cost centre, not a checkbox.
- **Keep the price data fresh.** Stale prices are worse than no prices — they
  cause a collector to accept a bad deal believing it was fair.
- **Not add a burden.** Any fee that raises the friction above the informal
  route guarantees collectors route around the platform. The economic case for
  the formal channel must stay positive for the collector.

## 5. Honest risks

- **Adoption risk (highest).** Informal collectors optimise for immediacy. A
  formal route that requires travel, waiting, or paperwork loses regardless of
  price. Cash remains first-class by design for this reason.
- **Data risk.** With little transaction volume, price estimates are thin and
  noisy. Confidence must be shown honestly, which is why the estimate endpoint
  returns a range and sample count, not a single number.
- **Verification cost vs. revenue.** Verifying and maintaining recycler records
  may exceed early revenue.
- **Safety outcomes are not measured by these numbers.** Reduced exposure to
  open burning and acid leaching is a genuine benefit that this model does not
  monetise.

## 6. What must be measured to replace these assumptions

| Needed input | Method | Replaces |
|---|---|---|
| Lots/collector/day, weight/lot | Diary study with 5–10 collectors over 2 weeks | §2 rows 1–2 |
| Current realised price/kg by material | Transaction diary + receipt photos | §2 blended rate |
| Current buyer chain (hops to recycler) | Chain mapping per collector | §2 row 4 |
| Travel/time cost per lot | Diary study | §2 transport |
| Willingness to switch | Conjoint / stated-preference in follow-up | §3 take rate |
| Recycler willingness to pay | Interviews with 5+ recyclers | §3 subscription |

**Required before this document is used for any decision: field research with
at least two working collectors or aggregators** (also a spec deliverable, and
currently not started).
