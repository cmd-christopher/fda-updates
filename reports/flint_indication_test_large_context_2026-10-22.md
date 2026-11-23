# Flint FDA indication test with larger generation limits

**Run date:** 2026-10-22  
**Model:** `flint:40b-a2b-qat-int4` on the Mac Studio (`192.168.1.6`)  
**Sample:** Same balanced 60-record sample as the earlier test: 30 original approvals and 30 supplements.  
**Request shape:** One approval per local Ollama `/api/chat` call; production indication prompt; `think: false`; `num_ctx: 65,536`; `num_predict: 16,384`.  
**Total elapsed:** 877 seconds (14.6 minutes); median 5.9 seconds per record; slowest 111 seconds.

## Results

| Set | Records | Returned an answer | Exact normalized match to cache |
|---|---:|---:|---:|
| Original approvals | 30 | 30 | 16 |
| Supplements | 30 | 30 | 17 |
| **Total** | **60** | **60** | **33** |

All 60 responses ended normally; none hit the 16,384-token cap. Flint used an average of 1,409 completion tokens per entry. The most verbose entry used 10,460 tokens and took 111 seconds.

Under the earlier one-entry trial's 1,000-token cap, 42/60 entries produced an answer and 27/60 exactly matched the cache. With the larger cap, that became 60/60 answers and 33/60 exact cache matches. The output limit fixed the empty-response problem and raised strict cache agreement from 45% to 55%, at about 2.4 times the total runtime. The existing cache is previous model-generated data, not independent ground truth; strict string differences include acceptable variants and more specific labels.

## Quality notes

Many non-exact outputs were reasonable condition-name variants, such as “paroxysmal supraventricular tachycardia” for “PSVT” and “non-small cell lung cancer” for “NSCLC.” Some were too vague or focused on a qualifier rather than the primary condition. Examples include “pediatrics” for a pediatric-labeling supplement, and “NRG1 gene fusion” where the source lists several diseases. Flint returned “tablet crushing” for a VENCLEXTA administration update; that captures the label change but is not a condition name.

This test supports the user's hypothesis that Flint needs a much larger output budget to finish consistently. It also shows a substantial latency cost and continued variation in choosing the primary condition. The 65,536-token context setting was generous; these one-entry prompts did not need that much context, so the improvement is most clearly attributable to the higher output budget and single-entry requests.

## Assessment

Flint is viable for an experimental single-entry path with a large output budget: it completed all entries in this sample. It is not yet a drop-in replacement for the current batched workflow. Its outputs need an independent quality review on ambiguous supplements, and the observed latency may be too high for processing the full dataset frequently. No production configuration or cached summaries were changed.

Full per-entry outputs and timings: [flint_indication_test_large_context_2026-10-22.json](flint_indication_test_large_context_2026-10-22.json).
