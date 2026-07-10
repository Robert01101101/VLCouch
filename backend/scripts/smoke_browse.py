from unittest.mock import MagicMock

from app.db import engine, init_db
from app.routers.library import browse_home
from sqlmodel import Session

init_db()
with Session(engine) as session:
    result = browse_home(MagicMock(), session)
    print("rows:", len(result["rows"]))
    for row in result["rows"][:10]:
        total = row.get("total", len(row["items"]))
        print(f"  {row['title']}: {len(row['items'])} shown / {total} total")
