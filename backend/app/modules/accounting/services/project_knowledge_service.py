"""
Project Knowledge Service using Gemini File Search.

Indexes non-secret repository files into a Gemini FileSearchStore for grounded
project code, architecture, testing, and business rules retrieval.

Enforces strict allowlist and denylist security rules:
- NEVER indexes .env, secrets, credentials, keys, or private files.
- Tracks document SHA256 hashes and Git commit revision in an incremental manifest.
"""

from __future__ import annotations

import hashlib
import fnmatch
import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

STORE_DISPLAY_NAME = "accounting-ai-system-knowledge"
DEFAULT_MANIFEST_FILENAME = ".project_index_manifest.json"

# ── Security Denylist (STRICTLY FORBIDDEN FROM INDEXING) ──────────────────────
DENYLIST_PATTERNS = frozenset({
    "**/.env*",
    "**/*.env*",
    "**/*.pem",
    "**/*.key",
    "**/*secret*",
    "**/*credential*",
    "**/*password*",
    "**/*.token",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/dist/**",
    "**/build/**",
    "**/.git/**",
    "**/.pytest_cache/**",
    "**/.system_generated/**",
    "**/*.db",
    "**/*.sqlite*",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.gif",
    "**/*.ico",
    "**/*.svg",
    "**/*.woff*",
    "**/*.ttf",
    "**/*.pyc",
    "**/*.log",
    "**/*.mp4",
    "**/*.webm",
    "**/*.webp",
    "**/*.zip",
    "**/*.tar*",
    "**/*.gz",
    "**/*.pdf",
    "**/*.lock",
})

# ── Security Allowlist (ONLY THESE PROJECT FILES ARE INDEXED) ─────────────────
ALLOWLIST_PATTERNS = frozenset({
    "backend/app/**",
    "backend/tests/**",
    "frontend/src/**",
    "alembic/**",
    "docs/**",
    "README*",
    "*walkthrough*.md",
    "*implementation_plan*.md",
    "agent_rag_audit_report*.md",
})

SUPPORTED_EXTENSIONS = frozenset({
    ".py",
    ".ts",
    ".tsx",
    ".md",
    ".sql",
    ".json",
    ".ini",
    ".css",
    ".txt",
})


@dataclass
class DocumentMetadata:
    project: str
    relative_path: str
    layer: str
    domain: str
    language: str
    sha256: str
    indexed_at: str
    remote_document_name: str | None = None

    def to_custom_metadata(self) -> list[types.CustomMetadata]:
        return [
            types.CustomMetadata(key="project", string_value=self.project),
            types.CustomMetadata(key="relative_path", string_value=self.relative_path),
            types.CustomMetadata(key="layer", string_value=self.layer),
            types.CustomMetadata(key="domain", string_value=self.domain),
            types.CustomMetadata(key="language", string_value=self.language),
        ]


def get_repo_root() -> Path:
    """Resolve repository root directory (accounting-ai-system)."""
    current = Path(__file__).resolve()
    # Go up from backend/app/modules/accounting/services/ -> root
    for parent in current.parents:
        if (parent / "backend").is_dir() and (parent / "frontend").is_dir():
            return parent
    return current.parents[5]


def get_manifest_path() -> Path:
    """Return path to local manifest file in backend."""
    return get_repo_root() / "backend" / DEFAULT_MANIFEST_FILENAME


def get_current_git_commit(repo_root: Path | None = None) -> str:
    """Get current Git commit SHA if git is available, otherwise return 'unknown'."""
    root = repo_root or get_repo_root()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def is_file_allowed(rel_path: str) -> bool:
    """Check whether a relative file path matches allowlist and does NOT match denylist."""
    norm = rel_path.replace("\\", "/").lstrip("./")

    # 1. Check Denylist first
    for pattern in DENYLIST_PATTERNS:
        if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(Path(norm).name, pattern):
            return False

    # 2. Check Supported Extension
    ext = Path(norm).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS and not Path(norm).name.startswith("README"):
        return False

    # 3. Check Allowlist
    for pattern in ALLOWLIST_PATTERNS:
        if fnmatch.fnmatch(norm, pattern):
            return True

    return False


def classify_document(rel_path: str) -> tuple[str, str, str]:
    """Classify (layer, domain, language) for a relative path."""
    norm = rel_path.replace("\\", "/").lower()

    # Layer
    if "backend/app/domain" in norm:
        layer = "domain"
    elif "backend/app/application" in norm:
        layer = "application"
    elif "backend/app/infrastructure" in norm:
        layer = "infrastructure"
    elif "backend/app/modules" in norm:
        layer = "modules"
    elif "backend/app/core" in norm:
        layer = "core"
    elif "backend/tests" in norm:
        layer = "test"
    elif "frontend" in norm:
        layer = "frontend"
    elif "alembic" in norm:
        layer = "migration"
    elif norm.endswith(".md") or "docs" in norm:
        layer = "documentation"
    else:
        layer = "general"

    # Domain
    if any(k in norm for k in ("payment", "receipt", "allocation")):
        domain = "payments"
    elif any(k in norm for k in ("invoice",)):
        domain = "invoices"
    elif "aging" in norm:
        domain = "aging"
    elif "statement" in norm:
        domain = "statements"
    elif "journal" in norm:
        domain = "journals"
    elif any(k in norm for k in ("account", "ledger", "balance", "profit_loss", "trial_balance")):
        domain = "accounting"
    elif any(k in norm for k in ("ai", "gemini", "assistant", "rag")):
        domain = "ai"
    elif any(k in norm for k in ("auth", "user", "company")):
        domain = "auth"
    elif any(k in norm for k in ("cur", "currency")):
        domain = "currency"
    else:
        domain = "core"

    # Language
    ext = Path(norm).suffix
    lang_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".md": "markdown",
        ".sql": "sql",
        ".json": "json",
        ".ini": "ini",
        ".css": "css",
        ".txt": "text",
    }
    language = lang_map.get(ext, "unknown")

    return layer, domain, language


def calculate_file_sha256(file_path: Path) -> str:
    """Compute SHA256 of file contents."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ProjectKnowledgeService:
    """Manages indexing and querying project knowledge in Gemini File Search."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or getattr(settings, "GEMINI_API_KEY", "")).strip()
        self.repo_root = get_repo_root()
        self.manifest_path = get_manifest_path()
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def load_manifest(self) -> dict[str, Any]:
        """Load manifest from disk."""
        if not self.manifest_path.exists():
            return {
                "store_name": None,
                "display_name": STORE_DISPLAY_NAME,
                "git_commit": None,
                "last_indexed_at": None,
                "documents": {},
            }
        try:
            with self.manifest_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to read manifest %s: %s", self.manifest_path, exc)
            return {
                "store_name": None,
                "display_name": STORE_DISPLAY_NAME,
                "git_commit": None,
                "last_indexed_at": None,
                "documents": {},
            }

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        """Save manifest to disk."""
        try:
            with self.manifest_path.open("w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to write manifest %s: %s", self.manifest_path, exc)

    def get_or_create_store(self) -> str:
        """Find existing store by display name or create a new one."""
        manifest = self.load_manifest()
        stored_name = manifest.get("store_name")

        # Verify existing store if recorded
        if stored_name:
            try:
                store = self.client.file_search_stores.get(name=stored_name)
                if store and store.name:
                    return store.name
            except Exception:
                logger.info("Recorded store %s not found remotely; searching or creating.", stored_name)

        # Check list of stores
        try:
            for s in self.client.file_search_stores.list():
                if s.display_name == STORE_DISPLAY_NAME:
                    manifest["store_name"] = s.name
                    self.save_manifest(manifest)
                    return s.name
        except Exception as exc:
            logger.warning("Could not list file search stores: %s", exc)

        # Create new store
        store = self.client.file_search_stores.create(
            config=types.CreateFileSearchStoreConfig(display_name=STORE_DISPLAY_NAME)
        )
        manifest["store_name"] = store.name
        self.save_manifest(manifest)
        logger.info("Created new FileSearchStore: %s (%s)", store.name, STORE_DISPLAY_NAME)
        return store.name

    def scan_repository(self) -> dict[str, Path]:
        """Scan repository for all allowed, non-denylisted files."""
        allowed_files: dict[str, Path] = {}
        for root, dirs, files in os.walk(self.repo_root):
            # Prune noisy directories from walking
            dirs[:] = [
                d for d in dirs
                if d not in {
                    "node_modules", ".venv", "venv", "__pycache__", ".git",
                    "dist", "build", ".pytest_cache", ".system_generated",
                }
            ]
            for file in files:
                abs_p = Path(root) / file
                try:
                    rel_p = abs_p.relative_to(self.repo_root).as_posix()
                except ValueError:
                    continue

                if is_file_allowed(rel_p) and abs_p.stat().st_size > 0:
                    allowed_files[rel_p] = abs_p

        return allowed_files

    def index_project(self, force_all: bool = False, max_workers: int = 8) -> dict[str, Any]:
        """
        Perform incremental project indexing into Gemini File Search Store.
        - Uploads new or changed files (with concurrent workers).
        - Deletes removed files from remote store.
        - Skips unchanged files.
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        store_name = self.get_or_create_store()
        manifest = self.load_manifest()
        existing_docs = manifest.get("documents", {})

        current_files = self.scan_repository()

        # If manifest has no documents, check if remote store already has documents uploaded
        if not existing_docs:
            try:
                remote_docs = list(self.client.file_search_stores.documents.list(parent=store_name))
                if remote_docs:
                    logger.info("Found %d existing remote documents in store; reconciling...", len(remote_docs))
                    for r_doc in remote_docs:
                        dp = getattr(r_doc, "display_name", None)
                        if dp and dp in current_files:
                            sha = calculate_file_sha256(current_files[dp])
                            layer, domain, language = classify_document(dp)
                            existing_docs[dp] = {
                                "project": "accounting-ai-system",
                                "relative_path": dp,
                                "layer": layer,
                                "domain": domain,
                                "language": language,
                                "sha256": sha,
                                "remote_document_name": getattr(r_doc, "name", None),
                                "indexed_at": datetime.now(timezone.utc).isoformat(),
                            }
                    manifest["documents"] = existing_docs
                    self.save_manifest(manifest)
            except Exception as exc:
                logger.warning("Could not list remote documents: %s", exc)

        current_rel_paths = set(current_files.keys())
        indexed_rel_paths = set(existing_docs.keys())

        added = current_rel_paths - indexed_rel_paths
        removed = indexed_rel_paths - current_rel_paths
        common = current_rel_paths & indexed_rel_paths

        modified: set[str] = set()
        for rel_p in common:
            if force_all:
                modified.add(rel_p)
                continue
            sha = calculate_file_sha256(current_files[rel_p])
            if sha != existing_docs[rel_p].get("sha256"):
                modified.add(rel_p)

        stats = {
            "total_scanned": len(current_files),
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
            "unchanged": len(common) - len(modified),
        }
        logger.info("Index plan: %s", stats)

        # 1. Delete removed files
        for rel_p in removed:
            doc_info = existing_docs.get(rel_p, {})
            remote_doc_name = doc_info.get("remote_document_name")
            if remote_doc_name:
                try:
                    self.client.file_search_stores.documents.delete(
                        name=remote_doc_name,
                        config=types.DeleteDocumentConfig(force=True),
                    )
                    logger.info("Deleted remote document %s (%s)", remote_doc_name, rel_p)
                except Exception as exc:
                    logger.warning("Failed to delete %s: %s", remote_doc_name, exc)
            existing_docs.pop(rel_p, None)

        # 2. Upload added and modified files
        files_to_upload = sorted(list(added | modified))
        manifest_lock = threading.Lock()
        completed_count = 0

        def _upload_single(rel_p: str) -> None:
            nonlocal completed_count
            abs_p = current_files[rel_p]
            sha = calculate_file_sha256(abs_p)
            layer, domain, language = classify_document(rel_p)

            # If modifying, delete old document first
            with manifest_lock:
                old_info = existing_docs.get(rel_p)
            if old_info and old_info.get("remote_document_name"):
                old_name = old_info["remote_document_name"]
                try:
                    self.client.file_search_stores.documents.delete(
                        name=old_name,
                        config=types.DeleteDocumentConfig(force=True),
                    )
                except Exception as exc:
                    logger.warning("Could not delete old doc %s: %s", old_name, exc)

            meta = DocumentMetadata(
                project="accounting-ai-system",
                relative_path=rel_p,
                layer=layer,
                domain=domain,
                language=language,
                sha256=sha,
                indexed_at=datetime.now(timezone.utc).isoformat(),
            )

            try:
                op = self.client.file_search_stores.upload_to_file_search_store(
                    file_search_store_name=store_name,
                    file=str(abs_p),
                    config=types.UploadToFileSearchStoreConfig(
                        display_name=rel_p,
                        custom_metadata=meta.to_custom_metadata(),
                    ),
                )
                doc_name = None
                if hasattr(op, "response") and op.response:
                    doc_name = op.response.document_name
                elif hasattr(op, "name"):
                    doc_name = op.name

                meta.remote_document_name = doc_name
                with manifest_lock:
                    existing_docs[rel_p] = asdict(meta)
                    completed_count += 1
                    if completed_count % 10 == 0:
                        manifest["store_name"] = store_name
                        manifest["documents"] = existing_docs
                        self.save_manifest(manifest)
                logger.info("Uploaded (%d/%d) %s -> %s", completed_count, len(files_to_upload), rel_p, doc_name)
            except Exception as exc:
                logger.error("Failed to upload %s: %s", rel_p, exc)

        if max_workers > 1 and len(files_to_upload) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_upload_single, rp) for rp in files_to_upload]
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error("Upload worker error: %s", e)
        else:
            for rel_p in files_to_upload:
                _upload_single(rel_p)

        # Final save manifest
        manifest["store_name"] = store_name
        manifest["git_commit"] = get_current_git_commit(self.repo_root)
        manifest["last_indexed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["documents"] = existing_docs
        self.save_manifest(manifest)

        return stats

    def get_status(self) -> dict[str, Any]:
        """Return current status of project knowledge indexing."""
        manifest = self.load_manifest()
        current_commit = get_current_git_commit(self.repo_root)
        indexed_commit = manifest.get("git_commit")
        is_synced = bool(indexed_commit and indexed_commit == current_commit)

        return {
            "store_name": manifest.get("store_name"),
            "display_name": manifest.get("display_name", STORE_DISPLAY_NAME),
            "indexed_commit": indexed_commit,
            "current_commit": current_commit,
            "is_commit_synced": is_synced,
            "total_documents": len(manifest.get("documents", {})),
            "last_indexed_at": manifest.get("last_indexed_at"),
        }

    def reset_store(self) -> bool:
        """Force-delete store and clear manifest."""
        manifest = self.load_manifest()
        store_name = manifest.get("store_name")
        if store_name:
            try:
                self.client.file_search_stores.delete(
                    name=store_name,
                    config=types.DeleteFileSearchStoreConfig(force=True),
                )
                logger.info("Reset store %s successfully.", store_name)
            except Exception as exc:
                logger.warning("Could not delete store %s: %s", store_name, exc)

        if self.manifest_path.exists():
            self.manifest_path.unlink()
        return True
