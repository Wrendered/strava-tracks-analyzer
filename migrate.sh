#!/bin/bash
# Migration script for WingWizard refactoring

# Create backup before migration
echo "Creating backup of current app.py..."
cp app.py app.py.bak

# Move the new app.py in place
echo "Moving new app.py into place..."
mv app.py.new app.py

# Run a basic test to verify syntax
echo "Testing the syntax of the refactored code..."
python -m py_compile app.py core/gpx.py core/metrics.py core/segments.py core/wind/direction.py core/wind/models.py utils/geo.py utils/validation.py ui/components/visualization.py ui/components/filters.py ui/pages/analysis.py

# Check the exit status
if [ $? -eq 0 ]; then
    echo "Syntax check passed."
else
    echo "Syntax check failed. Restoring original app.py..."
    mv app.py.bak app.py
    exit 1
fi

echo "Migration complete! Please run the application to verify functionality."
echo "To run the application: streamlit run app.py"