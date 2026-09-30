# DAHAM Codex Execution Plans

Use this file when a task is large enough that implementation needs several coordinated steps.

## When an ExecPlan is required

Create an ExecPlan for:
- Major feature additions
- Significant refactors
- Data migrations
- Public-data/API integrations
- Changes spanning multiple apps or modules
- PWA/service-worker/notification architecture changes
- Settlement/calculation-rule migrations
- SEO page generation systems
- Automated deployment/CI changes
- Any task where a partial implementation could leave production unstable

## Plan file location

Store active plans under:

docs/exec-plans/active/

After completion, move them to:

docs/exec-plans/completed/

Suggested filename:

YYYY-MM-DD-short-task-name.md

## Required structure

Each ExecPlan must contain:

# Title

## Goal
Describe the user-visible result.

## Current state
Document the relevant current implementation, paths, known behavior, and constraints.

## Requirements
List the exact functional and business rules that must be satisfied.

## Non-goals
State what must not be changed.

## Implementation steps
Use ordered, concrete steps. Include file paths/components when known.

## Verification plan
Include:
- build
- lint/type-check
- automated tests
- desktop verification
- mobile verification
- image/asset verification
- browser-console verification
- data/calculation checks where relevant

## Risks
List regression, data, security, API, caching, responsive, and deployment risks.

## Progress
Maintain checkboxes:
- [ ] Investigation
- [ ] Implementation
- [ ] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [ ] Regression check
- [ ] Final review

## Discoveries
Record important findings made while working.

## Decisions
Record implementation decisions and why they were chosen.

## Final verification
Document the commands/tests actually run and their results.

## Remaining limitations
Only list real unresolved limitations or external dependencies.

## Execution rule

The plan is not the deliverable.

After creating the plan:
1. Implement it.
2. Test it.
3. Fix failures.
4. Update the plan with discoveries.
5. Repeat until the requested behavior is verified.
6. Only then report completion.

Do not stop after writing the plan unless the user explicitly asked only for planning.
