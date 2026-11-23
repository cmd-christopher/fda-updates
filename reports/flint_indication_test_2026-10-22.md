# Flint FDA indication summarization test

**Run date:** 2026-10-22  
**Model:** `flint:40b-a2b-qat-int4` on the Mac Studio (`192.168.1.6`)  
**Dataset:** 60 records sampled from `data/approvals.json`: 30 original approvals and 30 supplements. The sample used seed `20261022`; five handpicked examples were retained.  
**Prompt:** Production indication extraction prompt, one record per request, local Ollama `/api/chat`, `think: false`, `num_predict: 1000`.  
**Duration:** 365.5 seconds total; 6.1 seconds per record on average.

## Results

| Set | Sampled | Returned an answer | Blank at token limit | Normalized exact cache match |
|---|---:|---:|---:|---:|
| Original approvals | 30 | 23 | 7 | 15 |
| Supplements | 30 | 19 | 11 | 12 |
| **Total** | **60** | **42** | **18** | **27** |

The cache exact-match rate was 27/60 (45%). Among requests that returned an answer, 27/42 (64%) exactly matched the existing cache after lowercasing and punctuation normalization. This is a strict text comparison, not an independent quality score: the cache is prior model-generated data. Many non-exact results were reasonable wording variants or captured a more specific population than the cached label.

## Observations

- Flint produced concise, usable labels on many records, including condition names such as idiopathic pulmonary fibrosis, cystic fibrosis, IgA nephropathy, and muscle-invasive bladder cancer.
- **18/60 requests returned no answer** and used all 1,000 allowed completion tokens. This happened more often for supplements (11/30) than original approvals (7/30).
- A 410-record full-set run through the current batch-of-10 workflow returned no parsed labels. A follow-up native Ollama request with 10 records and a 2,500-token cap also exhausted its budget without an answer. A high-cap retry on the first blank single-record case used all 3,000 tokens and still returned no answer; it was stopped there.
- Some returned summaries missed the requested condition focus. For example, VENCLEXTA returned “tablet crushing” for a label update about administration options; PROLIA returned only “pediatric” for a pediatric-labeling supplement.
- The original batch-of-10 test is especially unsuitable for this model under the current output budget. Flint's reasoning consumes a large number of tokens before it emits the requested line, and the OpenAI-compatible request did not reliably expose an answer even with `think: false`.

## Assessment

Flint shows it can identify indication names, but **it is not reliable with the current production batching and token settings**. In this sample, nearly one-third of one-record calls returned no output, and output quality varied on supplement-specific changes. It should not replace the current model without addressing reasoning/output control and retesting the full-set parser. No production model, configuration, or indication cache was changed.

Full per-record outcomes are in [flint_indication_test_2026-10-22.json](flint_indication_test_2026-10-22.json).
