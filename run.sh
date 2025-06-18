#!/bin/bash

# Ensure conda is available
eval "$(conda shell.bash hook)"
conda activate askademia

# Open new terminal to launch browser
osascript <<EOF
tell application "Terminal"
    do script "sleep 3; open http://127.0.0.1:5000"
end tell
EOF

# Run app.py in current terminal
python app.py
