"""Repository pattern implementation for recovery state persistence."""
import json
import logging
import traceback
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..types import RecoveryData, RecoveryState
from .models import ErrorLogModel, RecoveryStateModel, RetryAttemptModel

logger = logging.getLogger(__name__)


class RecoveryRepository:
    """Repository for managing recovery state persistence operations.
    
    Implements the repository pattern to abstract database operations
    and provide a clean interface for recovery state management.
    """

    def __init__(self, session: AsyncSession):
        """Initialize with async database session."""
        self.session = session

    async def save_recovery_state(self, recovery_data: RecoveryData) -> None:
        """Save or update recovery state.
        
        Args:
            recovery_data: Recovery data to persist

        """
        try:
            # Check if record exists
            stmt = select(RecoveryStateModel).where(
                RecoveryStateModel.operation_id == recovery_data.operation_id
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                update_stmt = (
                    update(RecoveryStateModel)
                    .where(RecoveryStateModel.operation_id == recovery_data.operation_id)
                    .values(
                        function_name=recovery_data.function_name,
                        args=json.dumps(recovery_data.args),
                        kwargs=json.dumps(recovery_data.kwargs),
                        state=recovery_data.state.value,
                        attempt=recovery_data.attempt,
                        error=str(recovery_data.error) if recovery_data.error else None,
                        recovery_metadata=json.dumps(recovery_data.metadata),
                        updated_at=datetime.utcnow()
                    )
                )
                await self.session.execute(update_stmt)
            else:
                # Create new record
                model = RecoveryStateModel(
                    operation_id=recovery_data.operation_id,
                    function_name=recovery_data.function_name,
                    args=json.dumps(recovery_data.args),
                    kwargs=json.dumps(recovery_data.kwargs),
                    state=recovery_data.state.value,
                    attempt=recovery_data.attempt,
                    error=str(recovery_data.error) if recovery_data.error else None,
                    recovery_metadata=json.dumps(recovery_data.metadata),
                    created_at=recovery_data.created_at,
                    updated_at=recovery_data.updated_at
                )
                self.session.add(model)

            await self.session.commit()
            logger.debug(f"Saved recovery state for operation {recovery_data.operation_id}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save recovery state {recovery_data.operation_id}: {e}")
            raise

    async def load_recovery_state(self, operation_id: str) -> RecoveryData | None:
        """Load recovery state by operation ID.
        
        Args:
            operation_id: Unique operation identifier
            
        Returns:
            Recovery data if found, None otherwise

        """
        try:
            stmt = select(RecoveryStateModel).where(
                RecoveryStateModel.operation_id == operation_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                return self._model_to_recovery_data(model)
            return None

        except Exception as e:
            logger.error(f"Failed to load recovery state {operation_id}: {e}")
            raise

    async def delete_recovery_state(self, operation_id: str) -> None:
        """Delete recovery state and all related data.
        
        Args:
            operation_id: Unique operation identifier

        """
        try:
            # Delete related records first (cascading)
            await self.session.execute(
                delete(RetryAttemptModel).where(
                    RetryAttemptModel.operation_id == operation_id
                )
            )
            await self.session.execute(
                delete(ErrorLogModel).where(
                    ErrorLogModel.operation_id == operation_id
                )
            )

            # Delete main recovery state
            await self.session.execute(
                delete(RecoveryStateModel).where(
                    RecoveryStateModel.operation_id == operation_id
                )
            )

            await self.session.commit()
            logger.debug(f"Deleted recovery state for operation {operation_id}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete recovery state {operation_id}: {e}")
            raise

    async def list_by_state(self, state: RecoveryState) -> list[RecoveryData]:
        """List all recovery data with given state.
        
        Args:
            state: Recovery state to filter by
            
        Returns:
            List of recovery data matching the state

        """
        try:
            stmt = (
                select(RecoveryStateModel)
                .where(RecoveryStateModel.state == state.value)
                .order_by(desc(RecoveryStateModel.updated_at))
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_recovery_data(model) for model in models]

        except Exception as e:
            logger.error(f"Failed to list recovery states by {state.value}: {e}")
            raise

    async def cleanup_old_states(self, days: int = 30) -> int:
        """Clean up old recovery states.
        
        Args:
            days: Number of days to keep. States older than this are deleted
            
        Returns:
            Number of records deleted

        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            # Get count of records to be deleted
            count_stmt = select(RecoveryStateModel).where(
                RecoveryStateModel.updated_at < cutoff_date
            )
            result = await self.session.execute(count_stmt)
            old_states = result.scalars().all()
            count = len(old_states)

            if count == 0:
                return 0

            # Extract operation IDs for cascading deletes
            operation_ids = [state.operation_id for state in old_states]

            # Delete related records
            await self.session.execute(
                delete(RetryAttemptModel).where(
                    RetryAttemptModel.operation_id.in_(operation_ids)
                )
            )
            await self.session.execute(
                delete(ErrorLogModel).where(
                    ErrorLogModel.operation_id.in_(operation_ids)
                )
            )

            # Delete main records
            await self.session.execute(
                delete(RecoveryStateModel).where(
                    RecoveryStateModel.updated_at < cutoff_date
                )
            )

            await self.session.commit()
            logger.info(f"Cleaned up {count} old recovery states")
            return count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup old states: {e}")
            raise

    async def save_retry_attempt(
        self,
        operation_id: str,
        attempt_number: int,
        started_at: datetime,
        completed_at: datetime | None = None,
        success: bool = False,
        error: Exception | None = None,
        strategy_name: str | None = None,
        delay_seconds: float | None = None,
        context: dict[str, Any] | None = None
    ) -> None:
        """Save detailed retry attempt information.
        
        Args:
            operation_id: Unique operation identifier
            attempt_number: Retry attempt number
            started_at: When the attempt started
            completed_at: When the attempt completed (optional)
            success: Whether the attempt succeeded
            error: Error that occurred (optional)
            strategy_name: Name of retry strategy used
            delay_seconds: Delay before this attempt
            context: Additional context information

        """
        try:
            duration_ms = None
            if completed_at and started_at:
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            model = RetryAttemptModel(
                operation_id=operation_id,
                attempt_number=attempt_number,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                success=success,
                error_type=type(error).__name__ if error else None,
                error_message=str(error) if error else None,
                error_traceback=traceback.format_exc() if error else None,
                strategy_name=strategy_name,
                delay_seconds=delay_seconds,
                context=json.dumps(context or {})
            )

            self.session.add(model)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save retry attempt for {operation_id}: {e}")
            raise

    async def save_error_log(
        self,
        operation_id: str,
        error: Exception,
        error_category: str,
        severity: str,
        function_name: str,
        attempt_number: int,
        error_subcategory: str | None = None,
        recovery_strategy: str | None = None,
        can_recover: bool = True,
        system_info: dict[str, Any] | None = None
    ) -> None:
        """Save detailed error log information.
        
        Args:
            operation_id: Unique operation identifier
            error: The exception that occurred
            error_category: Category of error (network, filesystem, etc.)
            severity: Error severity (low, medium, high, critical)
            function_name: Name of function that failed
            attempt_number: Retry attempt number when error occurred
            error_subcategory: More specific error subcategory
            recovery_strategy: Recovery strategy being used
            can_recover: Whether this error is recoverable
            system_info: Additional system information

        """
        try:
            model = ErrorLogModel(
                operation_id=operation_id,
                error_category=error_category,
                error_subcategory=error_subcategory,
                severity=severity,
                error_type=type(error).__name__,
                error_message=str(error),
                error_traceback=traceback.format_exc() if error else None,
                function_name=function_name,
                attempt_number=attempt_number,
                recovery_strategy=recovery_strategy,
                can_recover=can_recover,
                system_info=json.dumps(system_info or {})
            )

            self.session.add(model)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save error log for {operation_id}: {e}")
            raise

    async def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about recovery data.
        
        Returns:
            Dictionary containing various statistics

        """
        try:
            stats = {
                'total_operations': 0,
                'by_state': {},
                'by_function': {},
                'error_categories': {},
                'average_attempts': 0.0,
                'oldest_operation': None,
                'newest_operation': None,
                'success_rate': 0.0
            }

            # Count operations by state
            for state in RecoveryState:
                stmt = select(RecoveryStateModel).where(
                    RecoveryStateModel.state == state.value
                )
                result = await self.session.execute(stmt)
                count = len(result.scalars().all())
                stats['by_state'][state.value] = count
                stats['total_operations'] += count

            # Get additional statistics if we have data
            if stats['total_operations'] > 0:
                # Function distribution
                stmt = select(
                    RecoveryStateModel.function_name,
                    RecoveryStateModel.created_at,
                    RecoveryStateModel.updated_at,
                    RecoveryStateModel.attempt
                )
                result = await self.session.execute(stmt)
                records = result.all()

                # Function counts
                function_counts = {}
                total_attempts = 0
                dates = []

                for record in records:
                    func_name = record.function_name
                    function_counts[func_name] = function_counts.get(func_name, 0) + 1
                    total_attempts += record.attempt
                    dates.extend([record.created_at, record.updated_at])

                stats['by_function'] = function_counts
                stats['average_attempts'] = total_attempts / len(records)

                # Date range
                if dates:
                    dates = [d for d in dates if d is not None]
                    if dates:
                        stats['oldest_operation'] = min(dates).isoformat()
                        stats['newest_operation'] = max(dates).isoformat()

                # Success rate (completed operations / total operations)
                success_count = stats['by_state'].get('completed', 0)
                if stats['total_operations'] > 0:
                    stats['success_rate'] = success_count / stats['total_operations']

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise

    async def list_recovery_keys(self) -> list[str]:
        """List all recovery operation IDs."""
        try:
            stmt = select(RecoveryStateModel.operation_id)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list recovery keys: {e}")
            raise
    
    async def clear_all(self) -> None:
        """Clear all recovery data from database."""
        try:
            # Delete all records from all tables
            await self.session.execute(delete(ErrorLogModel))
            await self.session.execute(delete(RetryAttemptModel))
            await self.session.execute(delete(RecoveryStateModel))
            await self.session.commit()
            logger.info("Cleared all recovery data")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to clear all data: {e}")
            raise
    
    async def count_recovery_states(self) -> int:
        """Count total recovery states."""
        try:
            from sqlalchemy import func
            stmt = select(func.count(RecoveryStateModel.operation_id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count recovery states: {e}")
            raise
    
    async def count_retry_attempts(self) -> int:
        """Count total retry attempts."""
        try:
            from sqlalchemy import func
            stmt = select(func.count(RetryAttemptModel.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count retry attempts: {e}")
            raise
    
    async def count_error_logs(self) -> int:
        """Count total error logs."""
        try:
            from sqlalchemy import func
            stmt = select(func.count(ErrorLogModel.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count error logs: {e}")
            raise
    
    async def get_recent_recovery_states(self, limit: int = 10) -> list[RecoveryStateModel]:
        """Get recent recovery states."""
        try:
            stmt = (
                select(RecoveryStateModel)
                .order_by(desc(RecoveryStateModel.updated_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get recent recovery states: {e}")
            raise
    
    async def get_recovery_state(self, operation_id: str) -> RecoveryData | None:
        """Alias for load_recovery_state."""
        return await self.load_recovery_state(operation_id)
    
    async def get_retry_attempts(self, operation_id: str) -> list[RetryAttemptModel]:
        """Get all retry attempts for an operation."""
        try:
            stmt = (
                select(RetryAttemptModel)
                .where(RetryAttemptModel.operation_id == operation_id)
                .order_by(RetryAttemptModel.attempt_number)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get retry attempts for {operation_id}: {e}")
            raise
    
    async def get_error_logs(self, operation_id: str) -> list[ErrorLogModel]:
        """Get all error logs for an operation."""
        try:
            stmt = (
                select(ErrorLogModel)
                .where(ErrorLogModel.operation_id == operation_id)
                .order_by(desc(ErrorLogModel.logged_at))
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get error logs for {operation_id}: {e}")
            raise
    
    def _model_to_recovery_data(self, model: RecoveryStateModel) -> RecoveryData:
        """Convert database model to RecoveryData object."""
        return RecoveryData(
            operation_id=model.operation_id,
            function_name=model.function_name,
            args=tuple(json.loads(model.args)),
            kwargs=json.loads(model.kwargs),
            state=RecoveryState(model.state),
            attempt=model.attempt,
            error=Exception(model.error) if model.error else None,
            metadata=json.loads(model.recovery_metadata),
            created_at=model.created_at,
            updated_at=model.updated_at
        )

