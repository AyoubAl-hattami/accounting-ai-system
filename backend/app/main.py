from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.health import router as health_router
from app.modules.accounting.routes.auth_routes import router as auth_router
from app.modules.accounting.routes.company_routes import router as company_router
from app.modules.accounting.routes.company_user_routes import router as company_user_router
from app.modules.accounting.routes.account_routes import router as account_router
from app.modules.accounting.routes.fiscal_routes import router as fiscal_router
from app.modules.accounting.routes.journal_routes import router as journal_router
from app.modules.accounting.routes.report_routes import router as report_router
from app.modules.accounting.routes.audit_routes import router as audit_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(company_router)
app.include_router(company_user_router)
app.include_router(account_router)
app.include_router(fiscal_router)
app.include_router(journal_router)
app.include_router(report_router)
app.include_router(audit_router)


@app.get("/")
def root():
    return {
        "message": "Accounting AI System Backend",
    }