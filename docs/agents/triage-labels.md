# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

<!-- prettier-ignore-start -->
| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `mode:AFK`           | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `mode:HITL`          | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |
<!-- prettier-ignore-end -->

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

`mode:AFK`, `mode:HITL`, and `wontfix` already exist in the repo. `needs-triage` and `needs-info` have no existing equivalent — create them on first use (`gh label create`).

Edit the right-hand column to match whatever vocabulary you actually use.
