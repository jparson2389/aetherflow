# Issue tracker: GitHub

Issues and PRDs for this repo live in GitHub Issues for
`jparson2389/aetherflow`. Use the `gh` CLI for issue operations from this
clone.

## Conventions

- Create an issue: `gh issue create --repo jparson2389/aetherflow --title "..." --body "..."`
- Read an issue: `gh issue view <number> --repo jparson2389/aetherflow --comments`
- List issues: `gh issue list --repo jparson2389/aetherflow --state open --json number,title,body,labels,comments`
- Comment on an issue: `gh issue comment <number> --repo jparson2389/aetherflow --body "..."`
- Apply or remove labels: `gh issue edit <number> --repo jparson2389/aetherflow --add-label "..."` or `--remove-label "..."`
- Close an issue: `gh issue close <number> --repo jparson2389/aetherflow --comment "..."`

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `jparson2389/aetherflow`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --repo jparson2389/aetherflow --comments`.
