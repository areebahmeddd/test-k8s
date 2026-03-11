---
name: deep-thinking
description: "Use when solving complex problems, debugging hard issues, designing systems, evaluating architectural tradeoffs, or when a previous approach has failed. Enforces Karpathy-style first-principles reasoning: understand deeply before coding, challenge every assumption, evaluate three or more approaches with explicit tradeoffs before implementing. Triggers on: think through this, first principles, why is this hard, how should I approach, multiple options, tradeoffs, design decision, hard problem."
argument-hint: "Describe the problem, constraint, or decision to reason through"
---

# Deep Thinking — First Principles Approach

A mandatory reasoning phase before any code is written. Inspired by Andrej Karpathy's engineering philosophy: the best code comes from deeply understanding the problem, not from typing fast.

> "Most people spend 5% of their time understanding and 95% implementing.  
> The right ratio is closer to 50/50. Understanding is where the leverage is."

## When to Use

- Complex algorithmic or system design problems
- Architecture decisions with long-term consequences
- Debugging issues that have survived the obvious fix attempts
- Any request where the first approach that comes to mind might be wrong
- Performance problems where the bottleneck is unclear

## Procedure

### Phase 1: Understand (no code yet)

1. **Restate the problem** in your own words. If you cannot explain it simply, you do not understand it yet.
2. **Name the unknowns.** Explicit unknowns are better than hidden assumptions.
3. **Clarify ALL constraints**: performance requirements, correctness guarantees, compatibility, time horizon.
4. **Define done**: what does a correct solution look like? How will you verify it?

### Phase 2: Challenge Assumptions

1. List every assumption being made about the problem.
2. Label each: **Verified** | **Probably true** | **Unverified**
3. For each unverified assumption: what's the cheapest way to verify it?
4. Ask the Feynman question: "Can I explain this to someone without jargon?" If not — dig deeper.
5. Seek the **simplest possible model** of the problem. Complexity is often a sign of a misunderstood problem.

### Phase 3: Generate Approaches (minimum 3)

For each approach, state:

- **Name**: one descriptive phrase
- **Core idea**: one sentence
- **Time / Space complexity** (for algorithms) or **Operational cost** (for systems)
- **Pros**: what it handles well
- **Cons**: what it sacrifices or risks
- **Failure mode**: the scenario where this breaks

### Phase 4: Select and Commit

1. State which approach you're taking and WHY: explicitly name the tradeoff accepted.
2. Identify the riskiest part and address it first (fail fast on hard parts).
3. Write pseudocode or a design sketch before full implementation.

### Phase 5: Implement

1. Implement the chosen approach.
2. After each logical step: "Is this still solving the right problem?"
3. At completion: test against the success criteria from Phase 1.

## Anti-Patterns to Catch Yourself

| Anti-pattern                   | What to do instead                                             |
| ------------------------------ | -------------------------------------------------------------- |
| **Premature optimization**     | Solve correctness first; optimize with measurements            |
| **Resume-driven architecture** | Use the most boring technology that works                      |
| **Gold plating**               | Build exactly what's needed; no speculative features           |
| **Copy without understanding** | Never ship code you cannot explain line by line                |
| **Tunnel vision**              | If stuck >10 min, step back and restate Phase 1                |
| **Vague goals**                | If you can't write a passing test for it, the goal isn't clear |

## Output Format

Structure every deep-thinking response as:

```
## Problem Understanding
[Restated problem — your words, not the user's]

## Constraints
- [constraint 1]
- [constraint 2]

## Assumptions
- [assumption]: [Verified / Probably true / Unverified]

## Approaches Considered

### Approach 1: [Name]
Core idea: ...
Pros: ...
Cons: ...
Failure mode: ...

### Approach 2: [Name]
...

### Approach 3: [Name]
...

## Decision: [Chosen approach]
Rationale: [Why this over the alternatives — explicit tradeoff named]

## Riskiest Part
[What could go wrong, and how you'll address it first]

## Implementation
[Code or design]
```
