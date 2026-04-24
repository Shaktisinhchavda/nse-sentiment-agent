---
name: sentiment-learning-loop
description: Closed learning loop skill that improves sentiment responses based on user feedback. Automatically created and updated by the agent.
version: 1.0.0
metadata:
  hermes:
    tags: [learning, feedback, improvement]
    category: meta
---

# Sentiment Learning Loop

## When to Use
- When the agent receives negative feedback on a sentiment response
- When the agent needs to update its understanding of stock sentiment patterns
- When accumulated feedback indicates a systematic improvement opportunity

## Procedure

### Feedback Collection
1. After every chat response, prompt user for feedback: good/bad/neutral
2. If feedback is "bad", require a correction comment
3. Store feedback in `data/feedback/feedback_log.jsonl`

### Learning Mechanism
1. On negative feedback with corrections:
   - Extract the correction pattern
   - Append to `data/feedback/learned_context.txt`
   - This file is loaded on every chat session start
   - Injected as system-level context: "LEARNED FROM PREVIOUS FEEDBACK"

2. On accumulated positive feedback patterns:
   - Validate that learned corrections are producing good results
   - Remove stale corrections that are no longer relevant

### Verification
- Check `data/feedback/learned_context.txt` for accumulated learnings
- Check `data/feedback/feedback_log.jsonl` for all feedback entries
- Positive feedback % should increase over time

## Pitfalls
- Don't let learned context grow too large (token limits)
- Periodically prune outdated learnings
- Contradictory feedback should be flagged, not blindly learned
