#!/bin/bash
# Synchronization helper script for SpectralEdge (Linux/macOS)
# This script simplifies the process of syncing your local changes with GitHub

# Ensure the script is run from the project root
cd "$(dirname "$0")"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== SpectralEdge Sync Tool ===${NC}"
echo ""

# Function to display usage
usage() {
    echo "Usage: ./sync.sh [command]"
    echo ""
    echo "Commands:"
    echo "  pull    - Pull latest changes from GitHub"
    echo "  push    - Commit all changes and push to GitHub"
    echo "  status  - Show current git status"
    echo "  sync    - Pull, then commit and push all changes (full sync)"
    echo ""
    exit 1
}

# Function to pull changes
pull_changes() {
    echo -e "${YELLOW}Pulling latest changes from GitHub...${NC}"
    git pull origin main
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully pulled latest changes${NC}"
    else
        echo -e "${RED}✗ Failed to pull changes. Please resolve any conflicts.${NC}"
        exit 1
    fi
}

# Function to push changes
push_changes() {
    # Check if there are any changes to commit
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}No changes to commit.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Staging all changes...${NC}"
    git add .
    
    echo ""
    echo -e "${YELLOW}Enter commit message (or press Enter for default):${NC}"
    read -r commit_msg
    
    if [ -z "$commit_msg" ]; then
        commit_msg="Update: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    echo -e "${YELLOW}Committing changes...${NC}"
    git commit -m "$commit_msg"
    
    echo -e "${YELLOW}Pushing to GitHub...${NC}"
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully pushed changes to GitHub${NC}"
    else
        echo -e "${RED}✗ Failed to push changes. Please check your connection and credentials.${NC}"
        exit 1
    fi
}

# Function to show status
show_status() {
    echo -e "${YELLOW}Current git status:${NC}"
    echo ""
    git status
}

# Function to perform full sync
full_sync() {
    pull_changes
    echo ""
    push_changes
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
fi

case "$1" in
    pull)
        pull_changes
        ;;
    push)
        push_changes
        ;;
    status)
        show_status
        ;;
    sync)
        full_sync
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        usage
        ;;
esac
