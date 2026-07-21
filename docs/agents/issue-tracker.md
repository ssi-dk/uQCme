# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues in `ssi-dk/uQCme`. Use the
`gh` CLI for issue operations.

This app repo should be treated as public. Do not include private deployment
details such as hostnames, user accounts, private paths, tokens, private deploy
manifests, payload contents, or operational incidents. Put those details in the
relevant private deploy repo issue and link to it from a sanitized public issue
when needed.

## Conventions

- Create an issue: `gh issue create --title "..." --body "..."`
- Read an issue: `gh issue view <number> --comments`
- List issues: `gh issue list --state open`
- Comment on an issue: `gh issue comment <number> --body "..."`
- Apply or remove labels with `gh issue edit`.
- Close an issue with `gh issue close`.

Infer the repo from `git remote -v`; `gh` does this automatically when run
inside the clone.

## Pull requests as a triage surface

**PRs as a request surface: no.**

When set to `yes`, external pull requests use the same triage labels and
states as issues. Read them with `gh pr view <number> --comments` and inspect
changes with `gh pr diff <number>`. Only contributor-authored PRs belong in
the request queue; exclude PRs from owners, members, and collaborators.

GitHub shares one number space across issues and pull requests. Resolve an
ambiguous `#<number>` with `gh pr view <number>`, falling back to
`gh issue view <number>`.

## Cross-repo work

For work spanning app, automation, and deploy repos, create or update a
repo-local issue for the public uQCme change, link related issues, and associate
them with the GitHub Project named `researchit todo`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue in this repo unless the requested content contains
private deployment detail. If it does, create the detailed issue in the relevant
private deploy repo and keep this repo's issue public-safe.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments` inside this repo.

## Wayfinding operations

- **Map**: A single issue labelled `wayfinder:map`, containing Notes,
  Decisions-so-far, and Fog.
- **Child ticket**: A GitHub sub-issue linked to the map and labelled
  `wayfinder:<type>` (`research`, `prototype`, `grilling`, or `task`).
  If sub-issues are unavailable, use a task-list entry and put
  `Part of #<map>` at the top of the child.
- **Blocking**: Use GitHub native issue dependencies. Add blockers through
  `repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by`, passing the
  blocker's numeric database ID. If dependencies are unavailable, use
  `Blocked by: #<n>, #<n>` at the top of the child.
- **Frontier query**: Inspect the map's open children in map order and select
  the first ticket with no open blocker and no assignee.
- **Claim**: `gh issue edit <n> --add-assignee @me`.
- **Resolve**: Comment with the result, close the child, and append a context
  pointer to the map's Decisions-so-far.
