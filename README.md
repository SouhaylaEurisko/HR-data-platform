## HR Data Platform (MVP)

This project is a minimal FastAPI-based backend to:

- **Upload** XLSX files containing candidate / application data.
- **Parse and inject** that data into a database.
- **Expose** REST endpoints to list and filter records for HR.

### 1. Environment setup

- Create and activate a virtual environment (PowerShell example):

```powershell
cd C:\Users\user\Desktop\Project1
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run the API

From the project root:

```powershell
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` in your browser to see the interactive API docs.

### 3. Next steps

The next implementation steps will be:

- Add database configuration and models for candidate records.
- Create an XLSX upload endpoint that reads files from the `data` folder or via HTTP upload.
- Implement parsing and injection logic to store rows as records.
- Implement listing and filtering endpoints for the injected data.

