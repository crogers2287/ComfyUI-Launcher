---
name: app-recovery
status: backlog
created: 2025-09-06T20:12:28Z
progress: 0%
prd: .claude/prds/app-recovery.md
github: [Will be updated when synced to GitHub]
---

# Epic: app-recovery

## Overview

Implement a lightweight recovery system that enhances the existing error handling and progress tracking infrastructure to automatically recover from common workflow import/validation failures. The solution leverages existing components (progress_tracker.py, WebSocket events, Celery tasks) and adds minimal new code focused on retry logic and state persistence.

## Architecture Decisions

### Key Technical Decisions
1. **Enhance Existing Progress Tracker**: Extend `progress_tracker.py` to persist state to disk instead of memory-only
2. **Leverage Celery Retry**: Use Celery's built-in retry mechanisms with custom backoff strategy
3. **Reuse WebSocket Infrastructure**: Emit recovery status through existing socket events
4. **Minimal New Components**: Add recovery logic as decorators/middleware rather than new services
5. **SQLite for State**: Use lightweight SQLite DB for recovery state (already a dependency)

### Design Patterns
- **Decorator Pattern**: Wrap existing download/validation functions with recovery logic
- **Strategy Pattern**: Pluggable recovery strategies for different error types
- **Observer Pattern**: Use existing WebSocket for recovery notifications

## Technical Approach

### Frontend Components
- **RecoveryBanner**: Minimal banner component showing active recovery status
- **Enhanced ProjectCard**: Add recovery indicator to existing project cards
- **Progress Enhancement**: Extend existing progress bars to show retry attempts

### Backend Services
- **Recovery Decorator**: Python decorator for automatic retry with state persistence
- **State Persistence**: SQLite table for tracking operation state
- **Error Classifier**: Simple error categorization logic
- **Enhanced Progress Tracker**: Add checkpoint/resume capabilities

### Infrastructure
- **No new infrastructure required** - leverages existing:
  - Celery for async operations
  - WebSocket for real-time updates
  - Existing file storage for partial downloads
  - Current error handling patterns

## Implementation Strategy

### Phase 1: Core Recovery (Week 1)
- Implement recovery decorator with exponential backoff
- Add SQLite state persistence
- Enhance existing download functions with resume capability

### Phase 2: Integration (Week 2)
- Apply recovery to model downloads and validation
- Add WebSocket events for recovery status
- Implement basic error classification

### Phase 3: UI & Polish (Week 3)
- Add recovery banner and indicators
- Implement user-facing recovery actions
- Add recovery metrics and logging

## Task Breakdown Preview

High-level task categories that will be created:
- [ ] **Core Recovery System**: Implement recovery decorator and state persistence (~2-3 days)
- [ ] **Download Resume**: Add resume capability to model downloads (~2 days)
- [ ] **Error Classification**: Create error categorizer and recovery strategies (~1 day)
- [ ] **Progress State Enhancement**: Extend progress tracker for checkpoints (~1 day)
- [ ] **Frontend Recovery UI**: Add recovery banner and status indicators (~2 days)
- [ ] **Integration & Testing**: Apply recovery to existing operations (~2 days)
- [ ] **Documentation**: Recovery usage guide and API docs (~1 day)

## Dependencies

### External Dependencies
- SQLite (already included)
- Python requests library (existing)
- Celery retry functionality (existing)

### Internal Dependencies
- Existing progress_tracker.py module
- Current WebSocket infrastructure
- Celery task system
- Model download functions

### Prerequisite Work
- None - builds entirely on existing infrastructure

## Success Criteria (Technical)

### Performance Benchmarks
- Recovery overhead: <50ms per operation
- State persistence: <100ms writes
- UI updates: Real-time via WebSocket
- Memory usage: <5MB per project

### Quality Gates
- 95%+ test coverage for recovery logic
- Zero data corruption in state persistence
- Graceful degradation on recovery failure
- No impact on successful operations

### Acceptance Criteria
- Downloads resume from exact byte position
- Network errors retry automatically (3x max)
- Recovery state survives process restart
- Users see clear recovery status

## Estimated Effort

### Overall Timeline
- **Total Duration**: 3 weeks
- **Developer Resources**: 1 full-stack developer
- **Complexity**: Medium (leveraging existing infrastructure)

### Critical Path Items
1. Recovery decorator implementation (blocks everything)
2. SQLite state schema (blocks persistence)
3. WebSocket event integration (blocks UI)

### Risk Factors
- Minimal risk due to reuse of existing patterns
- Main complexity in handling edge cases
- Testing various failure scenarios

## Tasks Created
- [ ] 001.md - Recovery Decorator Implementation (parallel: false)
- [ ] 002.md - SQLite State Persistence (parallel: true)
- [ ] 003.md - Error Classification System (parallel: false)
- [ ] 004.md - Download Resume Enhancement (parallel: true)
- [ ] 005.md - Progress State Enhancement (parallel: true)
- [ ] 006.md - Frontend Recovery UI (parallel: true)
- [ ] 007.md - Integration & Testing (parallel: false)

Total tasks: 7
Parallel tasks: 4
Sequential tasks: 3
Estimated total effort: 84 hours