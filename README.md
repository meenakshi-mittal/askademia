# Askademia Setup Guide

This README provides step-by-step instructions to get Askademia up and running.

---

## 1. Clone the Repository

```bash
git clone <repo-url>
cd <repo-directory>
```

---

## 2. Add Environment Keys

Obtain the `keys.env` file from Meenakshi and place it in the **root directory** of the cloned repository.

---

## 3. Set Up the Slido Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" in the top-right corner.
3. Click **"Load unpacked"**
4. Select the `chrome-extension` directory inside the project.
5. The extension should now appear as **Askademia**

---

## 4. Set Up Zoom Streaming

### Enable Custom Streaming on Zoom

Follow [this Zoom guide](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0059839) to enable **Custom Live Streaming Service** in your Zoom settings.

---

## 5. Start Streaming

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

## 6. Start the System

Once streaming is live, run:

```bash
bash run.sh
```

If all is configured correctly, the system should now be fully operational.
