# WingWizard Refactoring Guide

This document provides instructions for migrating to the refactored WingWizard application structure.

## Overview

The WingWizard application has been refactored to improve maintainability, readability, and extensibility. The key changes include:

1. **Reorganized directory structure** with clearer separation of concerns
2. **Centralized configuration system** for app settings
3. **Improved error handling** throughout the codebase
4. **Better separation of UI and business logic**
5. **Enhanced documentation** with type hints and docstrings

Please refer to [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed overview of the new architecture.

## Migration Steps

### 1. Review the Changes

Before migrating, please take a moment to review the changes and understand the new structure:

- The core business logic is now in the `core` directory
- The UI code is now in the `ui` directory
- Configuration settings are centralized in `config/settings.py`
- Utility functions are now in the `utils` directory

### 2. Backup Your Current Code

Although we've created backups as part of the refactoring process, it's always good to have your own backup:

```bash
# Create a backup of your current code
git stash
# or
cp -r /path/to/strava-tracks-analyzer /path/to/strava-tracks-analyzer-backup
```

### 3. Run the Migration Script

We've provided a migration script to help with the transition:

```bash
# Make sure you're in the project directory
cd /path/to/strava-tracks-analyzer

# Run the migration script
./migrate.sh
```

This script will:
- Create a backup of the current `app.py`
- Move the new `app.py` into place
- Run a basic syntax check on the refactored code
- If the check fails, it will restore the original `app.py`

### 4. Test the Refactored Application

After running the migration script, test the application to ensure it works as expected:

```bash
# Activate the virtual environment if you're using one
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows

# Run the application
streamlit run app.py
```

### 5. Known Issues

Some pages are still under refactoring and may not work yet:
- Gear Comparison page
- Guide page

These will be completed in future phases of the refactoring.

## Next Steps

After migration, there are a few additional steps you can take to enhance the application:

1. **Complete the refactoring** of the Gear Comparison and Guide pages
2. **Add unit tests** to ensure the application works as expected
3. **Implement additional features** using the new architecture

## Troubleshooting

If you encounter any issues during migration:

1. **Check the logs** for error messages
2. **Restore the backup** if needed
3. **Review the changes** to understand what went wrong

If you're still having issues, please open an issue on the project's GitHub repository.

## Questions?

If you have any questions about the refactoring, please refer to the [ARCHITECTURE.md](ARCHITECTURE.md) document or open an issue on the project's GitHub repository.