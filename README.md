# Askademia Setup Guide

This README provides step-by-step instructions to get Askademia up and running.

---

## 1. Clone the Repository

```bash
git clone https://github.com/meenakshi-mittal/askademia.git
cd askademia
```

---

## 2. Set Up Python Environment

You can use `venv` or `conda` to create a virtual environment and install dependencies.

### Option A: Using `venv`

```bash
cd path/to/askademia

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # For macOS/Linux
venv\Scripts\activate    # For Windows

# Install dependencies
pip install -r requirements.txt
```

### Option B: Using `conda`

```bash
conda create -n askademia python=3.11
conda activate askademia
pip install -r requirements.txt
```

---

## 3. Install ngrok

Ngrok allows you to expose your local server to the internet.
Sign up for free:

- [Download ngrok](https://ngrok.com/download)
- [Get your auth token](https://dashboard.ngrok.com/get-started/your-authtoken)

After installing:

```bash
ngrok config add-authtoken <your_token>
```

---

## 4. Install Node.js and `node-media-server`

Askademia uses `node-media-server` to create an RTMP server.

### Install Node.js

- **macOS (with Homebrew):**
  ```bash
  brew install node
  ```

- **Windows/macOS/Linux (manual):**
  Download from [https://nodejs.org](https://nodejs.org)

### Install node-media-server

```bash
npm install -g node-media-server
```

---

## 5. Add Environment Keys

Obtain the `keys.env` file from Meenakshi and place it in the **root directory** of the cloned repository.

---

## 6. Set Up the Slido Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" in the top-right corner.
3. Click **"Load unpacked"**
4. Select the `chrome-extension` directory inside the project.
5. The extension should now appear as **Askademia**

---

## 7. Set Up Zoom Streaming

### Enable Custom Streaming on Zoom

Follow [this Zoom guide](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0059839) to enable **Custom Live Streaming Service** in your Zoom settings.

---

## 8. Start Streaming

### Before the lecture, run:

```bash
bash streaming.sh
```

This will open several terminal windows. One will display something like:

```
=======================================
Streaming URL:
rtmp://0.tcp.us-cal-1.ngrok.io:12858/live
=======================================
Streaming key:
my_stream
=======================================
Live streaming page URL:
http://localhost:8000/admin/streams
=======================================
```

**Keep this window open and accessible.**

---

### In the Zoom meeting:

1. Click **"More" > "Livestream" > "Live on Custom Live Streaming Service"**
2. A browser window will appear asking for:
   - Streaming URL
   - Streaming key
   - Live streaming page URL
3. Fill these in using the terminal output above.
4. Start the stream.

> Note: If you see a "cannot locate admin" or similar error, you can ignore it and close the page. Zoom should still show that it's connected to a live stream at the top of the meeting window.

---

## 9. Start the System

Once streaming is live, activate your environment and run:

```bash
bash run.sh
```

If all is configured correctly, the system should now be fully operational.
