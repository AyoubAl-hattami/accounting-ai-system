"""
CLI for managing Project Knowledge Index in Gemini File Search.

Usage:
  python -m app.modules.accounting.scripts.project_index status
  python -m app.modules.accounting.scripts.project_index index [--force]
  python -m app.modules.accounting.scripts.project_index verify
  python -m app.modules.accounting.scripts.project_index reset
"""

from __future__ import annotations

import argparse
import json
import sys

from app.modules.accounting.services.project_knowledge_service import (
    ProjectKnowledgeService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Gemini File Search Project Knowledge Index"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Show current index and git status")

    # index
    index_parser = subparsers.add_parser("index", help="Incrementally index codebase")
    index_parser.add_argument(
        "--force", action="store_true", help="Force re-upload of all files"
    )
    index_parser.add_argument(
        "--workers", type=int, default=8, help="Number of concurrent upload workers (default: 8)"
    )

    # verify
    subparsers.add_parser("verify", help="Verify store connection and documents")

    # reset
    subparsers.add_parser("reset", help="Delete store and clear local manifest")

    args = parser.parse_args()

    try:
        service = ProjectKnowledgeService()
    except Exception as exc:
        print(f"Error initializing service: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.command == "status":
        status = service.get_status()
        print("=== Project Knowledge Index Status ===")
        for k, v in status.items():
            print(f"  {k}: {v}")
        if not status["is_commit_synced"]:
            print("\n  [!] Working tree commit differs from indexed commit. Run 'index' to update.")

    elif args.command == "index":
        print(f"Scanning repository and updating Gemini File Search Store (workers={args.workers})...")
        stats = service.index_project(force_all=args.force, max_workers=args.workers)
        print("\n=== Indexing Summary ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print("\nIndexing complete!")

    elif args.command == "verify":
        status = service.get_status()
        store_name = status["store_name"]
        if not store_name:
            print("No store found in manifest. Run 'index' first.")
            sys.exit(1)

        print(f"Verifying store {store_name}...")
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                store = service.client.file_search_stores.get(name=store_name)
                docs = list(service.client.file_search_stores.documents.list(parent=store_name))
                print(f"Store verified: {store.display_name} ({store.name})")
                print(f"Remote documents count: {len(docs)}")
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    print(f"Verification failed: {exc}", file=sys.stderr)
                    sys.exit(1)
                time.sleep(2)

    elif args.command == "reset":
        confirm = input("Are you sure you want to delete the remote store and manifest? (y/N): ")
        if confirm.strip().lower() == "y":
            service.reset_store()
            print("Store and manifest successfully reset.")
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
