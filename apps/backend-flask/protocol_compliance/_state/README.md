# ProtocolGuard Backend State

This directory stores runtime artefacts for the ProtocolGuard Flask backend.

At runtime the server creates an SQLite database (`analysis_state.sqlite3`) that tracks analysis job state and the host-side paths for the `/workspace` mount used by Container Main. The database file is created automatically when the backend starts handling static analysis jobs.
