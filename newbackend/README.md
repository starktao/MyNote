MyNote Backend (FastAPI)
========================

Features
- Unified video audio extraction via yt-dlp → m4a/16k/mono
- Single and batch note generation; async concurrency with asyncio.Semaphore
- Smart screenshots around key timestamps (candidate frames + heuristic scoring)
- Task status/result files under note_results/ compatible with the Vue frontend
- SQLite + SQLAlchemy models (provider/model/batch_task/video_task) prepared

Run
1) python -m venv .venv && .venv\\Scripts\\activate (Windows)
2) pip install -r requirements.txt
3) cp .env.example .env  (optional)
4) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API
- GET /api/sys_check, /api/sys_health
- POST /api/generate_note
- POST /api/generate_notes
- GET /api/task_status/{task_id}
- GET /api/download_raw_transcript/{task_id}
- GET /api/image_proxy?url=...
- GET /api/providers, POST /api/providers, PATCH /api/providers/{id}
- GET /api/models

Next
- Plug faster-whisper / OpenAI/DeepSeek/Qwen into services/transcribe and services/llm.
- Persist tasks in DB (DAO wired in) and add /api/batch_status/{batch_id}.

