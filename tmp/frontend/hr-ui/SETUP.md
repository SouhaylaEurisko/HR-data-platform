# Frontend Setup Instructions

## Step 1: Install Dependencies

```bash
cd frontend/hr-ui
npm install
```

This will install:
- React and React DOM
- Vite (build tool)
- Axios (HTTP client)
- React Router DOM (routing)
- TypeScript and type definitions

## Step 2: Configure Backend URL

### Option A: Create `.env` file (Recommended)

1. In the `frontend/hr-ui/` directory, create a file named `.env`
2. Add the following line:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

**Important Notes:**
- The `.env` file should be in the `frontend/hr-ui/` directory (same level as `package.json`)
- Vite requires environment variables to start with `VITE_` to be exposed to the frontend
- If your backend runs on a different port, change `8000` to your port number
- The `.env` file is typically gitignored, so it won't be committed to version control

### Option B: Use Default (Development)

If you don't create a `.env` file, the app will default to `http://127.0.0.1:8000` (as defined in `src/config.ts`).

## Step 3: Start the Development Server

```bash
npm run dev
```

The frontend will start on `http://localhost:5173` (or another port if 5173 is busy).

## Step 4: Make Sure Backend is Running

Before using the UI, ensure your FastAPI backend is running:

```bash
# In the project root or backend directory
uvicorn backend.app.main:app --reload
```

The backend should be accessible at `http://127.0.0.1:8000`

## Project Structure

```
frontend/hr-ui/
├── .env                    # Backend URL configuration (create this)
├── .env.example            # Example env file
├── src/
│   ├── api/                # API client functions
│   │   ├── client.ts       # Axios instance configuration
│   │   ├── candidates.ts   # Candidate API calls
│   │   ├── import.ts       # Import API calls
│   │   └── chat.ts         # Chat API calls
│   ├── config.ts           # Configuration (API endpoints)
│   ├── types/              # TypeScript type definitions
│   │   └── api.ts          # API response types
│   └── ...
└── package.json
```

## Troubleshooting

### "Network Error: No response from server"
- Make sure your backend is running on `http://127.0.0.1:8000`
- Check that the URL in `.env` matches your backend URL
- Verify CORS is enabled on your FastAPI backend (if needed)

### Environment variable not working
- Make sure the variable name starts with `VITE_`
- Restart the dev server after creating/modifying `.env`
- Check that `.env` is in the correct location (`frontend/hr-ui/.env`)
