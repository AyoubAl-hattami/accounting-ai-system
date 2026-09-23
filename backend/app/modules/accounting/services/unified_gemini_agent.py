"""
Unified Gemini Agent Service.

Gemini is the autonomous brain of the agent:
- Understands user requests in Arabic, English, or any language without Regex intent routing.
- Autonomously decides whether to query Project Knowledge (via Gemini File Search),
  invoke Live Accounting Database Tools (via Function Calling), or both (Hybrid).
- Enforces strict tenant isolation (company_id forced from auth) and RBAC permissions.
- Action/mutation proposals require explicit user confirmation before execution.
- Returns grounded responses with verifiable source citations and grounding cards.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConversationTurn,
    GeminiAssistantReply,
    PageContext,
    SourceCitation,
    SuggestedAction,
)
from app.modules.accounting.services.accounting_tool_registry import (
    AccountingToolRegistry,
)
from app.modules.accounting.services.gemini_agent_contract import (
    CORE_SYSTEM_INSTRUCTIONS,
)
from app.modules.accounting.services.gemini_assistant_service import (
    detect_message_language,
)
from app.modules.accounting.services.project_knowledge_service import (
    ProjectKnowledgeService,
)

logger = logging.getLogger(__name__)

MAX_AGENT_TURNS = 5


def _generate_content_with_retry(
    client: genai.Client,
    model: str,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
    max_retries: int = 4,
) -> types.GenerateContentResponse:
    import time
    from google.genai.errors import ServerError, ClientError

    last_exc = None
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except (ServerError, ClientError) as exc:
            last_exc = exc
            # Retry on 503 (unavailable), 500 (internal), 429 (rate limit)
            status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            err_str = str(exc).lower()
            is_transient = (
                status_code in (503, 500, 429)
                or "503" in err_str
                or "high demand" in err_str
                or "resource_exhausted" in err_str
                or "rate" in err_str
            )
            if not is_transient or attempt == max_retries - 1:
                raise
            import re
            retry_match = re.search(r"retry in ([\d\.]+)s", err_str)
            if retry_match:
                delay = float(retry_match.group(1)) + 2.0
            else:
                delay = float(2 ** attempt + 2)

            logger.warning(
                "Gemini transient error on attempt %d/%d: %s. Retrying in %.1fs...",
                attempt + 1,
                max_retries,
                exc,
                delay,
            )
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]


def dispatch_unified_agent(
    db: Session,
    company_id: int,
    user_role: str,
    message: str,
    page_context: PageContext,
    language: str = "en",
    history: list[ConversationTurn] | None = None,
) -> GeminiAssistantReply:
    """
    Primary dispatcher for the Unified Gemini Agent.
    - Uses GEMINI_MODEL dynamically from settings (default gemini-3.6-flash).
    - If Gemini API is not configured, delegates to deterministic fallback.
    - LLM autonomously decides whether to use Project Knowledge File Search, Accounting Tools, or answer directly.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")

    lang = detect_message_language(message, language)

    # If Gemini is not configured, delegate cleanly to deterministic legacy assistant
    if not api_key:
        logger.info("Gemini API key not configured; delegating to deterministic fallback.")
        from app.modules.accounting.services.gemini_assistant_service import (
            dispatch_gemini_assistant,
        )
        return dispatch_gemini_assistant(
            db=db,
            company_id=company_id,
            user_role=user_role,
            message=message,
            page_context=page_context,
            language=lang,
            history=history,
        )

    try:
        client = genai.Client(api_key=api_key)

        # 1. Project Knowledge Tool (File Search Store)
        pk_service = ProjectKnowledgeService(api_key=api_key)
        store_name = pk_service.get_or_create_store()

        tools: list[types.Tool] = [
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_name],
                )
            ),
        ]

        # 2. Accounting Tools (Function Calling)
        function_declarations = AccountingToolRegistry.get_tool_declarations_for_role(user_role)
        if function_declarations:
            tools.append(types.Tool(function_declarations=function_declarations))

        # 3. System Instructions & Grounding Contract
        full_system_instruction = (
            f"{CORE_SYSTEM_INSTRUCTIONS}\n\n"
            f"--- RUNTIME CONTEXT ---\n"
            f"- User Role: {user_role}\n"
            f"- Company ID: {company_id}\n"
            f"- Current Page: {page_context.page} (Route: {page_context.route})\n"
            f"- Preferred Language: {lang}\n"
            f"- Response Requirement: Always respond in {lang.upper()}.\n"
        )

        config = types.GenerateContentConfig(
            system_instruction=full_system_instruction,
            temperature=0.1,
            tools=tools,
            tool_config=types.ToolConfig(
                include_server_side_tool_invocations=True,
            ),
        )

        # 4. Assemble contents
        contents: list[types.Content] = []
        if history:
            for turn in history[-6:]:
                role = "user" if turn.role == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn.content)]))

        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        data_sources: list[str] = []
        citations: list[SourceCitation] = []
        captured_suggested_action: SuggestedAction | None = None
        final_reply_text = ""

        # 5. Multi-turn Tool Calling Execution Loop
        for turn_idx in range(MAX_AGENT_TURNS):
            response = _generate_content_with_retry(
                client=client,
                model=model_name,
                contents=contents,
                config=config,
            )

            # Check for citations / grounding metadata
            if response.candidates and response.candidates[0].grounding_metadata:
                gm = response.candidates[0].grounding_metadata
                if gm.grounding_chunks:
                    for chunk in gm.grounding_chunks:
                        if chunk.retrieved_context and chunk.retrieved_context.title:
                            title = chunk.retrieved_context.title
                            snippet = chunk.retrieved_context.text if hasattr(chunk.retrieved_context, "text") else None
                            if not any(c.file_path == title for c in citations):
                                citations.append(SourceCitation(file_path=title, title=title, snippet=snippet))
                                if "project_knowledge" not in data_sources:
                                    data_sources.append("project_knowledge")

            # Check for Function Calls
            if response.function_calls:
                # Append model turn to conversation history
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                tool_response_parts: list[types.Part] = []
                for fc in response.function_calls:
                    logger.info("Gemini requested tool: %s with args: %s", fc.name, fc.args)
                    exec_result = AccountingToolRegistry.execute_tool(
                        tool_name=fc.name,
                        args=fc.args or {},
                        db=db,
                        company_id=company_id,
                        user_role=user_role,
                    )
                    if exec_result.is_mutation_proposal and exec_result.suggested_action:
                        captured_suggested_action = exec_result.suggested_action

                    if exec_result.data_source and exec_result.data_source not in data_sources:
                        data_sources.append(exec_result.data_source)

                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": exec_result.data},
                        )
                    )

                contents.append(types.Content(role="user", parts=tool_response_parts))
                # Next turn in loop to let Gemini process tool response
                continue

            # No function calls -> Model provided final response
            if response.text:
                final_reply_text = response.text
            elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, "text") and p.text]
                final_reply_text = "\n".join(text_parts)

            break

        if not final_reply_text:
            final_reply_text = (
                "تمت معالجة طلبك بنجاح." if lang == "ar" else "Your request was processed successfully."
            )

        return GeminiAssistantReply(
            reply=final_reply_text,
            intent="unified_agent_response",
            confidence="high",
            data_sources=data_sources,
            citations=citations,
            suggested_action=captured_suggested_action,
        )

    except Exception as exc:
        logger.error("Unified Gemini Agent error: %s", exc, exc_info=True)
        # Clean degradation to deterministic fallback
        from app.modules.accounting.services.gemini_assistant_service import (
            dispatch_gemini_assistant,
        )
        return dispatch_gemini_assistant(
            db=db,
            company_id=company_id,
            user_role=user_role,
            message=message,
            page_context=page_context,
            language=lang,
            history=history,
        )
