# Manus Chatbot — Installation & Execution Guide

A step-by-step walkthrough for first-time users. (This file mirrors `Manus_Chatbot_Installation_Guide.docx` so you can read or edit it in any text editor or VS Code.)

---

## 1. About This Project

Manus Chatbot is an AI-powered e-commerce chat assistant. It can search through a product catalog using **RAG (Retrieval Augmented Generation)**, read text from invoices and warranty cards using **OCR**, scan **QR codes**, and answer questions about any e-commerce site you connect or any document you upload.

The application has two parts:

- **Backend** — a FastAPI service that handles all the AI, vision, and database logic.
- **Frontend** — a Streamlit web app that gives the user a clean chat interface.

Both parts run together using **Docker**, so you do not need to install Python, Tesseract, or any AI libraries by hand. This is the easiest path for beginners and is the recommended setup.

---

## 2. What's Inside the Project

| Component | Purpose |
|---|---|
| `backend/` | FastAPI service — chat, RAG, OCR, QR scan, URL ingestion, currency, multilingual translation |
| `frontend/` | Streamlit UI — chat window, sidebar with language picker, document upload, URL ingestion, currency converter |
| `sample_documents/` | A handful of warranty / policy / log files you can upload to test document Q&A |
| `docker-compose.yml` | Wires the two services together |
| `chatbot.env` | Sample config — rename to `.env` before first run |

---

## 3. Before You Start (Prerequisites)

You will need the following installed on your computer. Pick the right link for your operating system — the installers will guide you through everything.

### 3.1 Required

- **Docker Desktop** — this is the only software you really need. It includes Docker and Docker Compose.
  - Download: <https://www.docker.com/products/docker-desktop/>
  - After installing, open Docker Desktop once and wait for the whale icon to say **"Docker Desktop is running"**.

### 3.2 Recommended

- **Visual Studio Code (VS Code)** — a free code editor that makes it easy to view and edit files.
  - Download: <https://code.visualstudio.com/>
  - Inside VS Code, install the **"Docker"** extension from the Extensions tab (square icon on the left).

### 3.3 Optional

- A free API key from <https://www.exchangerate-api.com> if you want live currency conversion. The app still works without it — it just falls back to default rates.
- **Internet access** — only needed if you want the multilingual feature to translate responses. It calls Google Translate's free endpoint at chat time. With no internet the bot still answers in English.

> **Note:** If you have never used Docker before, do not worry. You will only need to type **1 command** to start everything. Just make sure Docker Desktop is open and running before you continue.

---

## 4. Getting the Project Files

You will receive the project as a folder named **`Manus_chatbot`**, either as an attachment or a ZIP file.

### 4.1 If you received a ZIP file

1. Right-click the ZIP file and choose **"Extract All"** (Windows) or double-click it (Mac).
2. Move the extracted **`Manus_chatbot`** folder somewhere easy to find, for example your Desktop.

### 4.2 If you received the folder directly

Save the **`Manus_chatbot`** folder to your Desktop or any location you prefer.

### 4.3 Open the folder in VS Code (recommended)

1. Open VS Code.
2. Click **File → Open Folder**, and select the **`Manus_chatbot`** folder.
3. Click **Terminal → New Terminal**. A small command window will open at the bottom — this is where you will type the commands in the next steps.

---

## 5. Configure the Environment File

The project comes with a sample configuration file called **`chatbot.env`**. You need to rename this file to **`.env`** so the application can read it.

### 5.1 Rename `chatbot.env` to `.env`

Inside the `Manus_chatbot` folder, find the file named `chatbot.env` and rename it to `.env` (yes, just `.env` with a leading dot and no extension).

> On Windows, if you cannot see file extensions, open File Explorer → View → check **"File name extensions"**, then rename.

### 5.2 Edit the `.env` file

Open the `.env` file in VS Code (or any text editor). It looks like this:

```
EXCHANGE_RATE_API_KEY=your_exchange_rate_api_key_here
WHATSAPP_API_TOKEN=your_whatsapp_token_here
SECRET_KEY=your_super_secret_key_for_jwt_here
DATABASE_URL=sqlite:///./chat_history.db
```

If you have an Exchange Rate API key, replace `your_exchange_rate_api_key_here` with your real key. If you do not have one, you can leave the file as is — the app will still run.

> **Note:** Do not share your `.env` file or commit it to public repositories. It can contain secrets.

---

## 6. Running the Application (One Command)

Make sure Docker Desktop is open and running. Then, in the terminal you opened in VS Code (which should be inside the `Manus_chatbot` folder), run this single command:

```bash
docker-compose up --build
```

What this does:

- Downloads the base images (only the first time, this can take 5–10 minutes).
- Builds the backend and frontend Docker images.
- Starts both services and connects them on a private network.

You will see a lot of text scrolling. That is normal. When it is ready you will see lines similar to:

```
frontend  |  You can now view your Streamlit app in your browser.
backend   |  ✅ Database initialized
backend   |  Application startup complete.
```

### 6.1 Open the chatbot in your browser

Once you see the messages above, open a web browser and visit:

- **Frontend (chat UI):** <http://localhost:8501>
- **Backend (Swagger API docs):** <http://localhost:8000/docs>

Start with the Frontend URL — that is the chat window you will use.

### 6.2 Stopping the application

To stop the chatbot, go back to the terminal and press **Ctrl + C** (Windows/Linux) or **Cmd + C** (Mac). Wait a few seconds for both services to shut down cleanly.

To remove the containers completely (for example, before reinstalling), run:

```bash
docker-compose down
```

---

## 7. Using the Chatbot

Once the chat interface is open in your browser, you can try the following:

### 7.1 Ask a product question

Type something like: *"What headphones do you have under 100 dollars?"*. The chatbot will search the sample product catalog and reply.

### 7.2 Upload an image with a QR code

Use the **📎 Upload Document** panel in the sidebar to send an image with a QR code printed on it. The bot will scan the code and tell you whether it matches a known product.

### 7.3 Upload an invoice or warranty card

Upload a clear photo or scan of the document. The OCR engine will extract details such as invoice number, date, and amount, and the bot will then answer questions about the document.

### 7.4 Convert currency

Use the **💱 Currency Converter** sidebar tool to convert between currencies in real time.

### 7.5 Export your chat

Click **"Generate Chat File"** in the sidebar to download a copy of the conversation that can be shared on WhatsApp or email.

### 7.6 Chat in your own language

Use the **🌍 Language** dropdown in the sidebar to pick from 18 languages including Hindi, Tamil, Telugu, Bengali, French, Spanish, Arabic, Japanese and more. Choose **Auto-detect** to let the bot read whichever language you type in. Internet access is required so that translations can call Google Translate's free endpoint.

> Example: pick **Hindi** from the sidebar, type `नमस्ते` — the reply comes back in Hindi.

### 7.7 Add a website to ask questions about

Open the **🌐 Add website** panel in the sidebar, paste an e-commerce product URL (Amazon `/dp/<ASIN>` works best), set **Max pages**, then press **Ingest site**. After it finishes you can ask the chatbot product questions about that site (e.g. *"show me earbuds under 5000"*) and the answer cites the source URL.

If you paste a Flipkart, Meesho, Myntra, or Ajio homepage you may see a clear failure message saying the site blocks server-side scrapers. That is expected — these sites need a JavaScript-capable browser. Try a direct product URL instead.

---

## 8. Troubleshooting

### 8.1 `"docker-compose: command not found"`

Docker Desktop is probably not installed or not running. Open Docker Desktop and wait until the icon turns green. Then try the command again. On newer versions you can also try `docker compose` (with a space) instead of `docker-compose`.

### 8.2 The browser shows "This site can't be reached"

Wait another 30–60 seconds — the first startup is slow. Then refresh. If still failing, check the terminal for red error messages and stop with **Ctrl + C** and run `docker-compose up --build` again.

### 8.3 Port already in use (8000 or 8501)

Another application is using the port. Close any other Streamlit, FastAPI, or Jupyter server you may have running, or restart your computer and try again.

### 8.4 OCR or QR code does not detect anything

Make sure the uploaded image is clear, in focus, and well-lit. Avoid heavy compression. Re-take the photo if needed.

### 8.5 Multilingual reply comes back in English

The translation service couldn't reach Google Translate (no internet?). The app falls back to English by design. Reconnect to the internet and try again.

### 8.6 Ingestion says "blocks server-side scrapers"

Sites like Flipkart, Meesho, Myntra and Ajio render their pages with JavaScript and block automated scrapers. Use a direct product URL instead of the homepage. For Amazon use a `/dp/<ASIN>` URL — those work reliably.

### 8.7 Slow first run

The first build downloads several gigabytes of dependencies. This is normal. Subsequent runs will start in under a minute.

---

## 9. Project Folder Layout (For Reference)

Here is what each folder contains, in case you want to explore the code:

- `backend/` — FastAPI service. Contains `main.py`, the AI services, and the API routes.
- `frontend/` — Streamlit chat interface (`app.py`).
- `sample_documents/` — Sample PDFs / text / log files you can upload to test document Q&A.
- `docker-compose.yml` — Defines how the backend and frontend run together.
- `.env` — Your local configuration (renamed from `chatbot.env`).
- `README.md` — Original project overview from the developer.
- `DEPLOYMENT.md` — Short developer-style deployment notes.
- `DEMO_GUIDE.md` — Walkthrough of every feature with copy-paste examples.
- `CHANGELOG.md` — What changed in each release of the project.

---

## 10. Quick Command Reference

Save these for later — they cover 95% of what you will need.

```bash
# Start the application
docker-compose up --build

# Start in background mode
docker-compose up -d --build

# View logs while running in background
docker-compose logs -f

# Stop the application
docker-compose down

# Rebuild after a code change
docker-compose up --build --force-recreate
```

---

## 11. Need Help?

If something is not working, copy the last 20–30 lines of the terminal output and reply to the email with the message. That will give the developer enough context to help you quickly.

Welcome aboard, and enjoy exploring the Manus Chatbot!
