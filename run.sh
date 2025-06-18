#!/bin/bash

# Step 1: Install node-media-server globally
echo "🔧 Installing node-media-server globally..."
sudo npm install -g node-media-server

# Step 2: Start node-media-server in a new terminal window
echo "🚀 Launching node-media-server..."
osascript <<END
tell application "Terminal"
    do script "node-media-server"
end tell
END

# Step 3: Wait a bit to ensure NMS starts
sleep 2

# Step 4: Start ngrok tcp 1935 in another terminal window
echo "🌐 Starting ngrok (tcp 1935)..."
osascript <<END
tell application "Terminal"
    do script "ngrok tcp 1935"
end tell
END

# Step 5: Wait until ngrok's API becomes available
echo "⏳ Waiting for ngrok to initialize..."
until curl -s http://127.0.0.1:4040/api/tunnels > /dev/null; do
  sleep 1
done

# Step 6: Extract and reformat TCP forwarding URL as RTMP
RAW_TCP_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -Eo 'tcp://[^"]+')
HOST_PORT=${RAW_TCP_URL#tcp://}
RTMP_URL="rtmp://${HOST_PORT}/live"

# Step 7: Copy to clipboard and show it
echo "$RTMP_URL" | pbcopy
echo "✅ Copied RTMP URL to clipboard:"
echo "=============================================="
echo "$RTMP_URL"
echo "=============================================="

echo "📌 Paste this into Zoom's 'Streaming URL' field."