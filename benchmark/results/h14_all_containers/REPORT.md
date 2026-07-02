# Unified benchmark A-F

Tasks/cases: 12 | seed: 42 | repeat band: 40%

## Single-agent finance (A vs B)

- **A**: latency=5481.4ms tokens_in=1368.1 llm_calls=4 success=0.583
- **B**: latency=1486.5ms tokens_in=294.3 llm_calls=0.83 success=0.833 cache_hit=0.417

## Multi-agent healthcare (C vs D)

- **C**: latency=9792ms tokens_in=606.4 success=0.5 abstain=0.333
- **D**: latency=13101.3ms tokens_in=699.8 success=0.5 abstain=0.083 embeds=3

## Multi-agent finance (E vs F)

- **E**: latency=4007.2ms tokens_in=596.7 llm_calls=2.25 success=0.5
- **F**: latency=1009.2ms tokens_in=138.2 llm_calls=0.67 success=0.583 cache_hit=0.417

## Repeat variants (finance B vs F)

- **B exact_repeat**: latency=7.7ms tokens_in=0 cache=1.0
- **B paraphrase**: latency=6.5ms tokens_in=0 cache=1.0
- **B novel**: latency=2156.8ms tokens_in=630.5 cache=0.0
- **F exact_repeat**: latency=34ms tokens_in=0 cache=1.0
- **F paraphrase**: latency=32.5ms tokens_in=0 cache=1.0
- **F novel**: latency=1769.2ms tokens_in=261.2 cache=0.0