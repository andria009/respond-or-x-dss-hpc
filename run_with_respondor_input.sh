#!/bin/bash
# Script to run respond-or-x-dss-hpc with respondor-main input format
# Usage: ./run_with_respondor_input.sh <input_config.json>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_config.json>"
    echo ""
    echo "Example:"
    echo "  $0 test_input.json"
    echo ""
    echo "The JSON file should contain configuration similar to respondor-main format:"
    echo "{"
    echo "  \"name\": \"project_name\","
    echo "  \"output_dir\": \"output/directory\","
    echo "  \"poi_file\": \"path/to/locations.csv\","
    echo "  \"assess_risks\": true,"
    echo "  \"generate_routes\": true"
    echo "}"
    exit 1
fi

CONFIG_FILE="$1"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../respondor_env" ]; then
    echo "Error: Virtual environment 'respondor_env' not found in parent directory"
    echo "Please run: python3 -m venv ../respondor_env && source ../respondor_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Activating virtual environment..."
source ../respondor_env/bin/activate

echo "Running respond-or-x-dss-hpc with respondor-main input format..."
echo "Config file: $CONFIG_FILE"
echo ""

python main_respondor_input.py "$CONFIG_FILE"

echo ""
echo "Processing complete!"