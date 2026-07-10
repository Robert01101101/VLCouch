"""Quick scan smoke test — respects SCAN_LIMIT from .env."""
from pathlib import Path

from app.config import MEDIA_ROOTS, SCAN_LIMIT
from app.db import engine, init_db
from app.library_scan import scan_library
from sqlmodel import Session, select
from app.models import Movie, Show, Episode

print("MEDIA_ROOTS:", MEDIA_ROOTS)
print("SCAN_LIMIT:", SCAN_LIMIT or "none")
for r in MEDIA_ROOTS:
    p = Path(r["path"])
    print(f"  {r['type']}: {p} exists={p.exists()}")

init_db()
with Session(engine) as session:
    stats = scan_library(session, MEDIA_ROOTS)
    print("Scan stats:", stats)
    print("Movies:", len(session.exec(select(Movie)).all()))
    print("Shows:", len(session.exec(select(Show)).all()))
    print("Episodes:", len(session.exec(select(Episode)).all()))
