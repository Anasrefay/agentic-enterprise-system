
# M2 Development Benchmark Summary

## 1. Benchmark Setup

- Total development tasks defined: 30
- Tasks executed: 10
- Models tested: 3
- Benchmark type: Preliminary development benchmark
- Evaluation status: Pending manual quality evaluation

## 2. Model Configuration

| Tier | Model ID | Provider |
|---|---|---|
| Low | openrouter/liquid/lfm-3-1.7b:free | OpenRouter |
| Medium | openrouter/nvidia/nemotron-3.5-lightning:free | OpenRouter |
| High | openrouter/nvidia/nemotron-3-ultra-550b-a55b:free | OpenRouter |

## 3. Results

| Metric | Low | Medium | High |
|---|---:|---:|---:|
| Successful calls | 8 | 10 | 10 |
| Failed calls | 2 | 0 | 0 |
| Success rate | 80% | 100% | 100% |
| Average latency (successful calls) | 6106 ms | 8370 ms | 33648 ms |
| Average total tokens (successful calls) | 1500 | 1151 | 1143 |
| Reported cost | $0 | $0 | $0 |

## 4. Observations

- Low was the fastest model in the preliminary benchmark.
- Low experienced two upstream rate-limit failures.
- Medium completed all ten tasks with a moderate average latency.
- High completed all ten tasks but had significantly higher latency.
- Model quality has not yet been formally evaluated.
- The reported zero cost applies to the tested free model calls.

## 5. Limitations

- Only 10 out of 30 defined tasks were executed.
- Each task was tested once per model.
- Two Low model failures were caused by upstream rate limits.
- No formal answer-quality scoring was performed.
- Tool-calling capability was not tested.
- Results may vary because free providers have shared usage limits.

## 6. Preliminary Decision

Keep all three models as candidates.

Medium is the preliminary balanced candidate.
Low is the preliminary speed candidate.
High is the preliminary candidate for testing complex tasks.

No final model ranking is established until quality evaluation.
