# Database Integration for File & Chat History TODO

## Approved Plan Steps:

### 1. Create new files

- [x] `backend/app/models/history.py` (SQLAlchemy models: FileUpload, ChatMessage)
- [x] `backend/app/core/database.py` (Async SQLAlchemy session/engine)
- [x] `backend/app/dependencies.py` (get_session_id dependency)

### 2. Update existing files

- [x] `backend/main.py` (Engine creation, table init, include new deps)
- [x] `backend/app/api/endpoints.py` (Add session_id to requests, pass to services)
- [x] `backend/app/services/chatbot_service.py` (Store/retrieve history via DB)
- [x] `backend/app/services/rag_service.py` (query_history method)
- [x] `backend/requirements.txt` (Add aiosqlite, alembic)

### 3. Followup (manual/user)

- [ ] Install deps: cd backend && pip install -r requirements.txt
- [ ] Init alembic: cd backend && alembic init alembic
- [ ] Config alembic.ini & env.py with DATABASE_URL from settings
- [ ] Generate migration: alembic revision --autogenerate -m "add history tables"
- [ ] Run: alembic upgrade head
- [ ] Test endpoints with curl (upload/chat with session_id)
- [ ] Verify DB (sqlite3 chat_history.db "SELECT \* FROM ...")
- [ ] Update frontend/app.py to send session_id if needed

- [x] `backend/app/models/history.py` (SQLAlchemy models: FileUpload, ChatMessage)
- [x] `backend/app/core/database.py` (Async SQLAlchemy session/engine)
- [x] `backend/app/dependencies.py` (get_session_id dependency)

### 1. Create new files (3/3 done)

### 2. Update existing files

All code updates complete. See followup steps below.
