from pydantic import BaseModel, Field


class AccountInfo(BaseModel):
    id: int = Field(..., ge=1)
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    account_type: str = Field(..., pattern="^(asset|liability|equity|income|expense)$")
    is_active: bool


class JournalSuggestionRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1, max_length=2000)
    accounts: list[AccountInfo] = Field(..., min_length=1)
    language: str = Field(default="en", pattern="^(en|ar)$")


class JournalSuggestionResponse(BaseModel):
    debit_account_id: int | None = None
    credit_account_id: int | None = None
    amount: float | None = None
    confidence: str = Field(..., pattern="^(high|medium|low)$")
    explanation: str
    warnings: list[str]
    detected_intent: str
    source: str = "backend_rules"


class AiStatusResponse(BaseModel):
    journal_provider: str
    llm_enabled: bool
    fallback_enabled: bool
    source: str
    message: str
