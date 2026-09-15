from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RateLimitAttempt(Base):
    """One recorded attempt against one rate-limit bucket.

    The limiter used to keep these in a process-local dict, so ``--workers 2``
    meant two independent counters and the configured limit was really twice
    what the operator set.  Rows here are shared by every worker.

    Deliberately not company-scoped and carrying no foreign keys: an attempt is
    recorded before anyone is authenticated, so there is no tenant to attribute
    it to and nothing it should keep alive.
    """

    __tablename__ = "rate_limit_attempts"

    # BigInteger, matching the migration: this table takes a row per login
    # attempt across every tenant, so it is the one table in the schema with
    # a plausible route to exhausting a 32-bit key.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    # The full bucket key built by make_rate_limit_key, e.g.
    # "login:198.51.100.7:someone@example.com" or "register:198.51.100.7".
    bucket_key: Mapped[str] = mapped_column(String(255), nullable=False)

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # The counting query: one bucket, inside one window.
        Index("ix_rate_limit_attempts_bucket_time", "bucket_key", "attempted_at"),
        # The sweep: everything older than the longest window, any bucket.
        Index("ix_rate_limit_attempts_attempted_at", "attempted_at"),
    )
