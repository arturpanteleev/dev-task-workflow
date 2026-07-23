# dev-task-workflow

A portable, staged workflow for end-to-end software-development tasks.

It separates product analysis, technical planning, implementation, verification,
independent code review, and delivery. The primary skill orchestrates the stages
and retains approval gates before implementation and before Git delivery.

## Contents

- `dev-task-workflow` — orchestrator
- `dev-task-product-analysis`
- `dev-task-technical-planning`
- `dev-task-implementation`
- `dev-task-verification`
- `dev-task-code-review`
- `dev-task-delivery`

Each skill uses the portable Agent Skills layout: a directory named after the
skill containing `SKILL.md`, plus optional `assets/` and `scripts/`.

## Install

Clone the repository and run one of:

```sh
./install.sh codex
./install.sh claude
./install.sh opencode
./install.sh all
```

The installer creates symlinks and never overwrites an existing skill. Its
targets are:

| Agent | Global skill directory |
| --- | --- |
| Codex | `~/.agents/skills` |
| Claude Code | `~/.claude/skills` |
| OpenCode | `~/.config/opencode/skills` |

For a repository-local install, link the `skills/` subdirectories into the
agent's project-local directory, for example `.agents/skills/`,
`.claude/skills/`, or `.opencode/skills/`.

## Workflow

Invoke `dev-task-workflow` for a complete task. It asks for a task identifier
and an artifact directory outside the affected repositories, then delegates
each stage to a focused skill.

The workflow does not perform commit, push, or pull-request creation without
explicit user approval.

## License

[MIT](LICENSE)
