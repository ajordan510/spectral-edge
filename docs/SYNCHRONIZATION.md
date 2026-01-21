# SpectralEdge Synchronization Documentation

This document describes the two-way synchronization setup between your local development environment and the Manus AI sandbox environment.

## Overview

The SpectralEdge project uses **GitHub as the central source of truth** for all code. Both you and Manus AI can independently pull changes from and push changes to the repository at `https://github.com/ajordan510/spectral-edge`.

This approach provides several benefits including version control, change history, conflict resolution, and the ability to work asynchronously without direct file sharing.

## Authentication Setup

To enable Manus AI to push changes to your repository, a **GitHub Personal Access Token (PAT)** has been configured. This token grants write access to the repository while maintaining security through GitHub's authentication system.

The token is stored securely in the Manus sandbox environment and is used automatically whenever Manus needs to push changes. The token has an expiration date and can be revoked at any time from your GitHub account settings.

## Synchronization Workflow

The typical workflow for collaborative development on SpectralEdge follows this pattern:

### When You Start Working

Before you begin making changes on your local machine, you should always pull the latest updates from GitHub to ensure you have the most recent version of the code. Open a terminal in your `spectral-edge` directory and run:

```bash
./sync.sh pull
```

This command fetches all changes that Manus or other collaborators may have pushed since your last session.

### During Your Work Session

Make your changes, test them locally, and commit them as you normally would. You can use standard Git commands or the helper script:

```bash
./sync.sh status    # Check what files have changed
./sync.sh push      # Commit and push your changes
```

### When You Ask Manus to Work

When you request that Manus work on the project, the following automated process occurs:

1. Manus pulls the latest changes from your GitHub repository
2. Manus makes the requested modifications and tests them
3. Manus commits the changes with a descriptive message
4. Manus pushes the changes back to GitHub
5. Manus notifies you that the work is complete

### Retrieving Manus's Changes

After Manus has completed work and pushed changes, you can retrieve them by pulling from GitHub:

```bash
./sync.sh pull
```

Your local repository will be updated with all of Manus's changes, and you can immediately continue working.

## Conflict Resolution

If both you and Manus modify the same file simultaneously, Git will detect a merge conflict when you attempt to pull or push. Git will mark the conflicting sections in the affected files, and you will need to manually resolve them by editing the files and choosing which changes to keep.

After resolving conflicts, stage the resolved files and commit:

```bash
git add <resolved-files>
git commit -m "Resolved merge conflict"
git push origin main
```

To minimize conflicts, communicate with Manus about which files or features you are actively working on, and try to work on different parts of the codebase when possible.

## Helper Scripts

The `sync.sh` (Linux/macOS) and `sync.bat` (Windows) scripts provide convenient shortcuts for common Git operations:

| Command | Description |
|---------|-------------|
| `./sync.sh pull` | Pull latest changes from GitHub |
| `./sync.sh push` | Stage all changes, commit with a message, and push to GitHub |
| `./sync.sh status` | Display current Git status |
| `./sync.sh sync` | Perform a full synchronization (pull, then push) |

These scripts handle error checking and provide user-friendly output to simplify the synchronization process.

## Security Considerations

The Personal Access Token used by Manus is stored only in the Manus sandbox environment and is not exposed in any logs or outputs. The token has limited permissions (repository access only) and can be revoked at any time from your GitHub settings.

If you need to revoke the token, go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens) and delete the token. You can generate a new token at any time and provide it to Manus to restore push access.

## Best Practices

To ensure smooth collaboration, follow these best practices:

- **Pull before you start working** to get the latest changes
- **Commit frequently** with clear, descriptive messages
- **Push regularly** to share your progress
- **Communicate** about which files you are editing to avoid conflicts
- **Test your changes** before pushing to ensure the code works correctly
- **Use branches** for experimental features (optional but recommended for larger changes)

## Troubleshooting

### Issue: "Your branch is behind 'origin/main'"

**Solution**: You need to pull the latest changes before pushing:
```bash
./sync.sh pull
```

### Issue: "Failed to push changes"

**Solution**: Check your internet connection and ensure you have pulled the latest changes. If the problem persists, there may be a merge conflict that needs to be resolved.

### Issue: "Permission denied"

**Solution**: On Linux/macOS, ensure the sync script is executable:
```bash
chmod +x sync.sh
```

## Summary

With this synchronization setup, you and Manus AI can work seamlessly on the SpectralEdge project. GitHub serves as the central repository, and both environments can independently pull and push changes. This provides a robust, version-controlled workflow that supports collaborative development while maintaining a complete history of all changes.
