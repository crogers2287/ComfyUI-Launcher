"""SQLAlchemy models for recovery state persistence."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class RecoveryStateModel(Base):
    """Main table for storing recovery operation state.
    
    Stores the core recovery information including function details,
    current state, and retry attempts.
    """

    __tablename__ = 'recovery_state'

    # Primary key
    operation_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Function identification
    function_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Serialized function arguments
    args: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized
    kwargs: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized

    # Recovery state and progress
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error information
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata and context
    recovery_metadata: Mapped[str] = mapped_column(Text, nullable=False, default='{}')  # JSON serialized

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return (
            f"<RecoveryStateModel(operation_id='{self.operation_id}', "
            f"function_name='{self.function_name}', state='{self.state}', "
            f"attempt={self.attempt})>"
        )


class RetryAttemptModel(Base):
    """Detailed tracking of individual retry attempts.
    
    Stores detailed information about each retry attempt including
    timing, error details, and context for analysis.
    """

    __tablename__ = 'retry_attempts'

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to recovery_state
    operation_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # Attempt number
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timing information
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Result information
    success: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Strategy information
    strategy_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delay_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # Context and metadata
    context: Mapped[str] = mapped_column(Text, nullable=False, default='{}')  # JSON serialized

    def __repr__(self) -> str:
        return (
            f"<RetryAttemptModel(operation_id='{self.operation_id}', "
            f"attempt_number={self.attempt_number}, success={self.success})>"
        )


class ErrorLogModel(Base):
    """Detailed error logging for recovery operations.
    
    Provides comprehensive error tracking and classification
    for analysis and monitoring purposes.
    """

    __tablename__ = 'error_logs'

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to recovery_state
    operation_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # Error classification
    error_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    error_subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Error details
    error_type: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Context information
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Recovery context
    recovery_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    can_recover: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Additional metadata
    system_info: Mapped[str] = mapped_column(Text, nullable=False, default='{}')  # JSON serialized

    # Timestamp
    logged_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return (
            f"<ErrorLogModel(operation_id='{self.operation_id}', "
            f"error_category='{self.error_category}', severity='{self.severity}')>"
        )

