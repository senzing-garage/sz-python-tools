# unattended-issue-loop overlay for sz-python-tools

Extra rules for `/unattended-issue-loop` in this repo. They add to the skill; they replace none
of its steps.

## Merge method

This repo disallows merge commits and allows squash merges.

- Stage 4 merges with `gh pr merge <pr> --squash --delete-branch` instead of `--merge`.
- The Stage 1 merge probe confirms that an allow rule matches
  `gh pr merge <pr> --squash --delete-branch`, and that
  `gh repo view --json squashMergeAllowed --jq .squashMergeAllowed` prints `true`, in place of
  the `mergeCommitAllowed` check.
