# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to the actual label strings used in this repo's GitHub issue tracker.

<!-- prettier-ignore-start -->
| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
|----------------------------|----------------------|------------------------------------------|
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `question`           | Waiting on reporter for more information |
| `ready-for-agent`          | `mode:AFK`           | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `mode:HITL`          | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |
<!-- prettier-ignore-end -->

When a skill mentions a canonical role, use the corresponding label string from
this table. Do not create duplicate labels when the mapped repo label already
exists.
