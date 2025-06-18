#!/bin/bash

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate askademia

# Run app.py in background (or foreground, as needed)
python app.py &

# Open new terminal, wait a few seconds, then open the browser
osascript <<EOF
tell application "Terminal"
    do script "sleep 3; open http://127.0.0.1:5000"
end tell
EOF
