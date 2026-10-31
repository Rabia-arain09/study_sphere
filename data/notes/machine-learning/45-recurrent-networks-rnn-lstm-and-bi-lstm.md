---
subject: Machine Learning
topic: "Recurrent Networks: RNN, LSTM and Bi-LSTM"
semester: 5
week: "16"
difficulty: 5
content_source: ai_generated
content_reviewed: false
---

# Recurrent Networks: RNN, LSTM and Bi-LSTM

*Machine Learning · Semester 5 · Week 16 · Difficulty 5/5*

**Key concept:** Recurrent networks process a sequence step by step while carrying a memory of what came before.

## How it works
- An **RNN** passes a hidden state from one time step to the next, so it suits text, speech and time series.
- Plain RNNs suffer from the **vanishing gradient** problem and forget long-range information.
- An **LSTM** adds a cell state and three gates (forget, input, output) that decide what to keep, add and expose.
- A **Bi-LSTM** reads the sequence forwards and backwards, so each word sees both left and right context.

## Example

In "The movies I watched last week were great", an LSTM can still link "were" to "movies" despite the long gap.

## Quick check
1. What problem do LSTM gates solve?
2. How does a Bi-LSTM differ from an LSTM?
