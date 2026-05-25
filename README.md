# AI-Powered E-commerce Chatbot

This project aims to develop a comprehensive AI-powered e-commerce chatbot with advanced capabilities including RAG (Retrieval Augmented Generation), computer vision, OCR, QR code detection, multi-lingual support, real-time currency conversion, human escalation, chat history, WhatsApp integration, and website embeddability. The entire solution will be containerized using Docker for easy deployment.

## Table of Contents

1.  [Architecture Overview](#architecture-overview)
2.  [Technology Stack](#technology-stack)
3.  [Project Structure](#project-structure)
4.  [Feature Breakdown](#feature-breakdown)
5.  [Deployment](#deployment)

## 1. Architecture Overview

The chatbot will consist of a backend service (FastAPI) handling AI logic, data retrieval, and external integrations, and a frontend interface (Streamlit) for user interaction. Docker will be used to containerize both components, ensuring a consistent and isolated environment.

```mermaid
graph TD
    User[Customer] -->|Interacts with| Frontend[Streamlit Chatbot UI]
    Frontend -->|API Calls| Backend[FastAPI Service]

    subgraph Backend Services
        Backend -->|Embeddings & Search| ChromaDB[Vector Database]
        Backend -->|OCR Processing| OCR[Tesseract/PaddleOCR]
        Backend -->|QR Code Detection| OpenCV_Pyzbar[OpenCV/Pyzbar]
        Backend -->|AI/NLP| TensorFlow[TensorFlow/Transformers]
        Backend -->|Currency Conversion| ExchangeRateAPI[External API]
        Backend -->|Human Escalation| HumanAgent[Human Agent Interface]
        Backend -->|Chat History| PostgreSQL[Database]
        Backend -->|WhatsApp Integration| WhatsAppAPI[WhatsApp Business API]
    end

    ChromaDB -->|Stores| ProductData[Product Data (Text & Embeddings)]
    OCR -->|Processes| Documents[Invoices, Warranty Cards]
    OpenCV_Pyzbar -->|Scans| QRCodes[Product QR Codes]
    TensorFlow -->|Powers| RAG[RAG Model] & NLP[NLP Tasks]
    PostgreSQL -->|Stores| ChatLogs[Chat Logs & History]
    HumanAgent -->|Receives| EscalatedQueries[Escalated Queries]
    WhatsAppAPI -->|Sends/Receives| ChatFiles[Chat Transfer Files]
```

## 2. Technology Stack

| Category             | Technology/Tool                                  | Purpose                             |
| :------------------- | :----------------------------------------------- | :---------------------------------- |
| **Frontend**         | Streamlit                                        | Interactive Chatbot UI              |
| **Backend**          | FastAPI, Pydantic                                | RESTful API, Data Validation        |
| **AI/ML**            | TensorFlow, Hugging Face Transformers (for RAG)  | NLP, Embeddings, RAG Model          |
| **Computer Vision**  | OpenCV, Pyzbar                                   | QR Code Detection, Image Processing |
| **OCR**              | Tesseract OCR (or PaddleOCR)                     | Document Text Extraction            |
| **Vector DB**        | ChromaDB                                         | Product Data Retrieval (RAG)        |
| **Database**         | PostgreSQL (for chat history, user data)         | Persistent Storage for Chat Logs    |
| **Containerization** | Docker, Docker Compose                           | Environment Isolation, Deployment   |
| **Multi-language**   | Google Translate API / Hugging Face Transformers | Language Detection, Translation     |
| **Currency**         | Exchange Rate API (e.g., Open Exchange Rates)    | Real-time Currency Conversion       |
| **Chat Transfer**    | WhatsApp Business API (or similar)               | Seamless Chat Transfer via Files    |

## 3. Project Structure

```
.
├── README.md
├── docker-compose.yml
├── requirements.txt
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints.py
│   │   │   └── models.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── chatbot_service.py
│   │   │   ├── cv_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── rag_service.py
│   │   │   └── currency_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── whatsapp_utils.py
│   └── data/
│       ├── products.json  # Sample product data
│       └── documents/     # Sample documents for OCR
├── frontend/
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── static/
│       └── style.css      # Custom CSS for gold/black theme
└── .env                   # Environment variables
```

## 4. Feature Breakdown

1.  **RAG and Computer Vision for Customer Support**: Integrated into `rag_service.py` and `cv_service.py`.
2.  **Product Data Retrieval from Vector DB**: ChromaDB integration via `rag_service.py`.
3.  **OCR for Document Processing**: Handled by `ocr_service.py`.
4.  **Fake Product Detection (QR Codes)**: Implemented in `cv_service.py` using OpenCV and Pyzbar.
5.  **Multi-lingual Chat**: Language detection and translation within `chatbot_service.py`.
6.  **Real-time Currency Conversion**: External API integration in `currency_service.py`.
7.  **Human Escalation**: Logic in `chatbot_service.py` and a placeholder for human agent interface.
8.  **Chat Logs, History, File Uploads**: PostgreSQL integration via `db.py` and `chatbot_service.py`.
9.  **Chat Transfer via WhatsApp**: `whatsapp_utils.py` for file generation and transfer.
10. **Integratable and Embeddable**: FastAPI backend provides a clear API, Streamlit can be embedded or served standalone.
11. **Docker Environment**: `docker-compose.yml` and individual `Dockerfile`s.
12. **Gold and Black UI**: Custom CSS in `frontend/static/style.css`.

## 5. Deployment

Instructions for building and running the Docker containers will be provided in the `docker-compose.yml` and a separate `DEPLOYMENT.md` file.
