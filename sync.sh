TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BRANCH=$(git branch --show-current)

git init
git remote add origin https://github.com/AryanIssPro/FriendlySMP.git

git pull origin "$BRANCH"

git push origin "$BRANCH"
git commit -m "$TIMESTAMP"

git pull origin "$BRANCH"

# Add all changes
git add .

# Commit with timestamp
git commit -m "$TIMESTAMP"
git push origin "$BRANCH"

git status
