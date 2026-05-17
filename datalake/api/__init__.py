"""HTTP API that exposes the SQLite-backed data to the React frontend.

Single read-only aiohttp app. The frontend at `frontend/` consumes these endpoints
to replace its `src/data/mock.ts` static data with live values. See `server.py`.
"""
