#!/bin/bash
# Script to rewrite git history to a single commit
# WARNING: This is destructive and will rewrite all history!

set -e

echo "=========================================="
echo "Git History Rewrite Script"
echo "=========================================="
echo ""
echo "WARNING: This will DELETE all git history and create a single commit!"
echo "Make sure you have a backup if needed."
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 1
fi

# Get current branch name
CURRENT_BRANCH=$(git branch --show-current)
echo ""
echo "Current branch: $CURRENT_BRANCH"
echo ""

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Create a backup branch (just in case)
BACKUP_BRANCH="backup-before-rewrite-$(date +%Y%m%d-%H%M%S)"
echo "Creating backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"

# Create new orphan branch (no history)
echo ""
echo "Creating new orphan branch..."
git checkout --orphan new-main

# Add all files
echo "Adding all files..."
git add -A

# Create single commit
echo "Creating single commit..."
git commit -m "Initial commit"

# Delete old main branch
echo ""
echo "Deleting old $CURRENT_BRANCH branch..."
git branch -D "$CURRENT_BRANCH"

# Rename new branch to main
echo "Renaming new branch to $CURRENT_BRANCH..."
git branch -m "$CURRENT_BRANCH"

echo ""
echo "=========================================="
echo "Local history rewritten successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review the new history: git log"
echo "  2. Force push to remote: git push -f origin $CURRENT_BRANCH"
echo "  3. If something went wrong, restore from: git checkout $BACKUP_BRANCH"
echo ""
echo "WARNING: Force pushing will overwrite the remote repository history!"
echo "Make sure all collaborators are aware of this change."
echo ""

