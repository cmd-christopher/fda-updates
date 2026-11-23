# GPT-6 Luna FDA indication summarization test

**Run date:** 2026-10-22  
**Model:** `gpt-6-luna`  
**Reasoning:** high  
**Route:** Codex CLI authenticated through the ChatGPT subscription; no API key or Ollama Cloud  
**Sample:** Same 60 records and production indication prompt as the Flint comparison: 30 original approvals and 30 supplements; one record per request.  
**Duration:** 846.0 seconds (14.1 minutes), 14.1 seconds per record on average.  
**CLI-reported token use:** 204,388 total; average 3,406 per entry.

## Results

| Measure | GPT-6 Luna, high | Flint, high-cap trial |
|---|---:|---:|
| Entries with an answer | 60/60 | 60/60 |
| Normalized exact matches to existing cache | 34/60 (56.7%) | 33/60 (55.0%) |
| Elapsed time | 14.1 min | 14.6 min |
| Normalized exact agreement between models | 42/60 | — |

The cache is prior model-generated data, not independent ground truth. Exact text differences include synonyms, abbreviations, and more specific condition names, so the one-record advantage in cache matching is too small to show that Luna is more accurate. Both models completed all entries in the one-record format. They produced identical normalized wording on 42 of 60 records.

## Output review

Several differences illustrate that cache agreement does not equal correctness. For VENCLEXTA, Luna returned “No new indication” while Flint returned “tablet crushing”; the source text describes an administration update rather than a disease indication. Luna selected warm autoimmune hemolytic anemia for IMAAVY, while the source lists generalized myasthenia gravis first and then warm autoimmune hemolytic anemia. For OPTISON, Luna returned “Pediatric patients,” which is not a condition name. On the other hand, many non-exact outputs were sensible expansions or contractions, such as “non-small cell lung cancer” for “NSCLC.”

## Assessment

Luna at high reasoning is viable for the same one-entry test path: all 60 requests returned parseable answers with no errors. On this sample it was effectively tied with Flint on strict cache matching and response time. High reasoning used about 204K CLI-reported tokens across the test and did not produce a clear quality advantage. Review of high-impact mismatches against an independently adjudicated gold set would be needed before choosing between them.

GPT-6 Luna supports high reasoning effort; OpenAI's guidance recommends low effort for extraction and classification tasks, with higher effort reserved for tasks that need more multi-step reasoning ([official reasoning-effort guidance](https://developers.openai.com/api/docs/guides/deployment-checklist#set-up-reasoningeffort)). High was kept here because it was the requested setting.

No production model, configuration, or indication cache was changed. Per-entry outputs and timing are in [gpt6luna_indication_test_2026-10-22.json](gpt6luna_indication_test_2026-10-22.json).
