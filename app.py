import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from api.routes.finance import router as finance_router
from api.routes.compliance import router as compliance_router
from api.routes.operations import router as operations_router
from api.routes.auth import router as auth_router
from api.routes.notifications import router as notifications_router
from api.routes.reports import router as reports_router
from api.routes.system import router as system_router
from api.routes.command_center import router as command_center_router
from services.jobs import generate_shift_reports, run_asset_document_alerts, run_database_backup
from api.middleware import TenantContextMiddleware
from api.routes.spreadsheets import router as spreadsheets_router
from api.routes.tenants import router as tenants_router
from api.routes.shifts import router as shifts_router
from api.routes.assets import router as assets_router
from api.routes.field_operations import router as field_operations_router

scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("ENABLE_SCHEDULED_JOBS", "true").lower() == "true":
        scheduler.add_job(run_database_backup, "cron", hour=int(os.getenv("BACKUP_HOUR_UTC", "2")), minute=0, id="daily-backup", replace_existing=True)
        scheduler.add_job(generate_shift_reports, "cron", hour="0,8,16", minute=0, id="shift-reports", replace_existing=True)
        scheduler.add_job(run_asset_document_alerts, "cron", hour="6", minute=0, id="asset-document-alerts", replace_existing=True)
        scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)

app = FastAPI(
    title="ŞimşekLog API",
    version="7.0.0",
    description="Lojistik, filo, finans ve navlun operasyonları için REST API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantContextMiddleware)
app.include_router(finance_router)
app.include_router(compliance_router)
app.include_router(operations_router)
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(reports_router)
app.include_router(system_router)
app.include_router(command_center_router)
app.include_router(spreadsheets_router)
app.include_router(tenants_router)
app.include_router(shifts_router)
app.include_router(assets_router)
app.include_router(field_operations_router)


@app.get("/health", tags=["Sistem"])
def health():
    return {"status": "ok", "service": "simseklog-api"}
