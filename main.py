from __future__ import annotations
import uvicorn

from app.core.config import get_settings
from app.factory import create_app
app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        app,
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
