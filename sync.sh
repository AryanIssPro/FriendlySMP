#!/bin/bash

# Set timestamp and branch
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BRANCH=$(git branch --show-current)

# Ensure repository is initialized
git init
git remote add origin https://github.com/AryanIssPro/FriendlySMP.git 2>/dev/null

# Pull latest changes
git pull origin "$BRANCH" --rebase

# Stage all changes
git add .

# Commit with timestamp
git commit -a -m "$TIMESTAMP"

# Force push to remote branch

git add .
git push origin "$BRANCH" --force

# Show status
git status
