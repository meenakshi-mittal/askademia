#!/bin/bash

# Ensure conda is available
eval "$(conda shell.bash hook)"
conda activate askademia

# Kill any process currently using port 5000
PID=$(lsof -ti tcp:5000)
if [ -n "$PID" ]; then
  echo "Killing process on port 5000 (PID: $PID)"
  kill -9 $PID
fi

# Open new terminal to launch browser
osascript <<EOF
tell application "Terminal"
    do script "sleep 3; open http://127.0.0.1:5000"
end tell
EOF

# Run app.py in current terminal
python app.py
