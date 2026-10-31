---
subject: Compiler Construction
topic: "Finite Automata: NFA and DFA"
semester: 5
week: "2"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Finite Automata: NFA and DFA

*Compiler Construction · Semester 5 · Week 2 · Difficulty 4/5*

**Key concept:** A finite automaton is a machine with states and transitions that recognizes exactly the strings of a regular language.

## How it works
- **DFA:** one transition per state and symbol. Easy to simulate.
- **NFA:** may have several transitions on one symbol and **epsilon** moves. Easier to build.
- A string is accepted if the machine can end in an accepting state after reading it.
- NFAs and DFAs recognize the same class of languages.

## Example

DFA for strings over {a, b} ending in ab, with states 0 (start), 1 and 2 (accepting). Transitions: 0-a->1, 0-b->0, 1-a->1, 1-b->2, 2-a->1, 2-b->0. The input aab goes 0, 1, 1, 2 and is accepted. The input abb goes 0, 1, 2, 0 and is rejected.

## Quick check
1. What extra feature does an NFA have compared with a DFA?
2. Trace the input bab on the example DFA. Is it accepted?
