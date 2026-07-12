# NOTES.md

## What I built

I built NeoBank as a small segmented banking cyber range, but the important part is that I did not just draw the architecture. I actually wired the pieces together so the workflow behaves like a real system.

The first design choice was to follwo the prosoal by having different zones, controlled paths and clear data ownership. Using Docker networking I split the system into DMZ, Corporate, Core, PCI, and separate database subnet which created explicit enforced trust boundaries.

Then I built the services around that split:
- `dmz-gw` handles the public edge.
- `corp-agent` handles support workflows.
- `core-svc` owns Core business logic and account state.
- `pci-svc` owns card-side authorization and PCI data.

I connected them so the traffic flow follows the intended path instead of shortcutting around it. That means Core talks to PCI over service-to-service HTTP, and the databases sit behind the services that own them.

I also built the support workflow that reviews tickets, classifies risk, checks for suspicious instruction-like content, and then decides whether a ticket should be escalated or handled through a privileged path. This is also where the distinguishing feature lives, because the workflow makes the approval decision part of the system instead of treating it like an afterthought, so the service boundaries stay clear, the sensitive state changes stay explicit, and the exploit path has to pass through a real decision point.

Finally, I added seed data, test scripts, and exploit/reset paths so the environment can be demonstrated repeatedly without turning into a one-shot demo.

What was real:
- the Docker network topology
- the FastAPI services
- the PostgreSQL databases
- the Core and PCI schema separation
- the service-to-service calls
- the write paths for tickets, credits, freezes, unfreezes, transactions, and audit logs

What was mocked or simplified:
- the default support-agent mode
- the live LLM behavior unless an API key is provided
- the dataset size
- the exploit baseline/reset fixture handling

## What I faked

I kept a few things intentionally fake or simplified because the point of the project was to show the architecture and the security behavior, not to build a production bank.

### Support-agent model behavior
The support-agent layer defaults to `mock` mode.

Why:
- the project must run locally without requiring an API key
- the exploit and policy workflow should be reproducible during review
- the local path needs to stay deterministic for testing

What this means:
- the workflow is real
- the model output is deterministic by default
- optional OpenAI-compatible `llm` mode exists if someone wants to connect a real model with an API key

### Seed volume / demo state behavior
I kept the canonical bootstrap seed small and then expanded the demo data separately.

Why:
- reviewers can understand the base system quickly
- the exploit path stays easy to trace
- richer demo data can be layered in without making the project noisy or confusing

### Exploit baseline handling
The exploit reset flow is still backed by code-level constants and scripted reset helpers rather than a fully separate data fixture system.

Why:
- it keeps the reset flow simple
- it makes the exploit harness repeatable
- it avoids overcomplicating the take-home with extra infrastructure

## My differentiator

My differentiator was to add an approval layer inside the customer-support workflow like an embedded policy. The agent can know before performing actions whether the requested action is categorized as privileged.

The main support workflow is the principal implementation, and the embedded approval / policy layer inside that workflow is the depth differentiator.

So before the agent can perform sensitive actions like unfreezing an account or issuing credit, the system classifies the requested action, decides whether it is privileged, and determines whether human approval is required. That makes the workflow more realistic, more explainable, and more security-focused, because the exploit now passes through a real decision point that is supposed to stop unsafe automation.

This is better than just having a “support bot” because it turns the support workflow into a control point:
- it identifies risky requests
- it separates review from action
- it makes privileged actions visible
- it keeps the exploit tied to a real authorization decision instead of a dummy response

## Why this way

I built it this way because the project needed to demonstrate security boundaries, not just functionality.

The architecture choices matter because:
- Core/PCI separation shows data ownership clearly
- service-to-service calls show the intended trust chain
- the support workflow shows how unsafe requests can be evaluated before action
- the embedded policy layer shows how a system can be made more secure without hiding everything behind vague automation

The fake parts matter too, because they keep the take-home focused:
- the local mock agent means the project works without external dependencies
- the compact seed data keeps the review approachable
- the repeatable exploit state makes it easier to verify behavior consistently

## What I would do in two days

1. Move the exploit baseline and reset behavior into a cleaner fixture/migration layer so it is fully data-driven.
2. Add a proper human-approval queue artifact instead of only returning approval decisions inline.
3. Tighten the support workflow so internal service calls are the only path to database updates everywhere.
4. Expand automated checks around the approval layer so the safe path and exploit path are both verified more explicitly.
5. Package the exploit evidence into a clearer before/after report so the reviewer can see the security behavior faster.

<!-- Optional small addition I would consider: add one explicit sentence here stating that the main support workflow is part of the principal implementation, while the embedded approval / policy layer inside that workflow is the chosen depth differentiator. -->
