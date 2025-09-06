# React Hooks Error Fixes

## Summary
Fixed "Invalid hook call" errors in the ComfyUI-Launcher web application by ensuring all React components follow the Rules of Hooks.

## Issues Found and Fixed

### 1. ImportWorkflowUI.tsx
**Problem**: State variables `uploadedFile` and `isZipFile` were declared after mutation hooks that referenced them.

**Fix**: Moved these state declarations before the mutation hooks to ensure proper closure capture.

```typescript
// Before: Lines 321-322 (after mutation hooks)
// After: Lines 112-113 (before mutation hooks)
const [uploadedFile, setUploadedFile] = React.useState<File | null>(null)
const [isZipFile, setIsZipFile] = React.useState(false)
```

### 2. WorkflowsGridView.tsx
**Problem**: The `useMemo` hook was called after conditional returns, violating the rule that hooks must be called in the same order on every render.

**Fix**: Moved the `useMemo` hook before all conditional returns and added null checks inside the hook.

```typescript
// Before: useMemo was after conditional returns
// After: useMemo is before conditional returns with null check
const filteredAndSortedProjects = useMemo(() => {
    if (!getProjectsQuery.data) return []
    // ... rest of logic
}, [getProjectsQuery.data, searchQuery, sortBy, sortOrder])
```

## React Rules of Hooks Violated

1. **Don't call Hooks inside conditions**: All hooks must be called at the top level of your React function
2. **Don't call Hooks after conditional returns**: Early returns must come after all hook calls
3. **Ensure consistent hook order**: Hooks must be called in the same order on every render

## Testing
- Build completed successfully with `npm run build`
- No React hooks errors in the compilation output
- Application should now run without "Invalid hook call" runtime errors

## Recommendations
1. Always declare all hooks at the beginning of your component function
2. Place conditional returns after all hook declarations
3. Use ESLint with the `eslint-plugin-react-hooks` to catch these issues during development