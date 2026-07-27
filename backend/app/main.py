from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analytics, auth, posts, social_accounts

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Multi-tenant SaaS platform for connecting social accounts, "
        "scheduling posts, auto-publishing via background workers, and viewing analytics."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(social_accounts.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
