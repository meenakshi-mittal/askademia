#!/bin/bash

ENV_NAME="askademia"
ENV_YML="environment.yml"
REQ_TXT="requirements.txt"

echo "🔍 Checking Conda..."

if ! command -v conda &>/dev/null; then
    echo "Conda not found. Install Miniconda or Anaconda."
    exit 1
fi

# Create env if it doesn't exist
if ! conda env list | grep -qE "^${ENV_NAME}[[:space:]]"; then
    echo "Creating conda environment '$ENV_NAME'..."
    if [[ -f "$ENV_YML" ]]; then
        conda env create -n "$ENV_NAME" -f "$ENV_YML"
    elif [[ -f "$REQ_TXT" ]]; then
        conda create -n "$ENV_NAME" python=3.11 -y
        conda run -n "$ENV_NAME" pip install -r "$REQ_TXT"
    else
        echo "❌ No environment.yml or requirements.txt found."
        exit 1
    fi
else
    echo "Conda environment '$ENV_NAME' already exists."
fi

# Install global node dependencies
if ! command -v node &>/dev/null; then
    echo "Installing Node.js..."
    brew install node
fi

if ! command -v npm &>/dev/null; then
    echo "npm not found even after Node install."
    exit 1
fi

if ! command -v ngrok &>/dev/null; then
    echo "Installing ngrok..."
    brew install --cask ngrok
fi

if ! npm list -g node-media-server &>/dev/null; then
    echo "Installing node-media-server..."
    sudo npm install -g node-media-server
fi

# Launch server + ngrok using conda run
echo "Launching node-media-server and ngrok in new terminals..."

# Kill anything using port 8000 (Node-Media-Server)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Kill any existing ngrok processes
pkill -f ngrok || true

osascript <<END
tell application "Terminal"
    do script "node-media-server"
end tell
END

sleep 2

osascript <<END
tell application "Terminal"
    do script "ngrok tcp 1935"
end tell
END

# Extract and format RTMP URL
echo "Waiting for ngrok to initialize..."
until curl -s http://127.0.0.1:4040/api/tunnels > /dev/null; do sleep 1; done

RAW_TCP_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -Eo 'tcp://[^"]+')
HOST_PORT=${RAW_TCP_URL#tcp://}
RTMP_URL="rtmp://${HOST_PORT}/live"
echo "$RTMP_URL" | pbcopy
echo "RTMP URL copied to clipboard: $RTMP_URL"
echo ""
echo "======================================="
echo "Streaming URL:"
echo "$RTMP_URL"
echo "======================================="
echo "Streaming key:"
echo "my_stream"
echo "======================================="
echo "Live streaming page URL:"
echo "http://localhost:8000/admin/streams"
echo "======================================="
echo ""
