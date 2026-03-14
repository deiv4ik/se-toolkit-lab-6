# Git Workflow

## Resolving Merge Conflicts
To resolve a merge conflict, follow these steps:

1. Open the conflicting file in your editor
2. Look for the conflict markers: <<<<<<<, =======, >>>>>>>
3. The changes from your branch are between <<<<<<< and =======
4. The changes from the other branch are between ======= and >>>>>>>
5. Choose which changes to keep, or edit to combine them
6. Remove the conflict markers
7. Save the file
8. Stage the resolved file: `git add <filename>`
9. Commit the changes: `git commit -m "Resolve merge conflict"`

## Protecting a Branch on GitHub
To protect a branch on GitHub:

1. Go to your repository on GitHub
2. Click on "Settings"
3. In the left sidebar, click "Branches"
4. Under "Branch protection rules", click "Add rule"
5. Enter the branch name you want to protect (e.g., main, master)
6. Configure protection settings
7. Click "Create" or "Save changes"
