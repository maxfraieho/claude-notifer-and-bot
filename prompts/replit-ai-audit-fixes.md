# Replit AI - Comprehensive Audit Fixes Implementation

## Context
You have received a comprehensive audit report identifying 1,331 technical issues in a Claude Code Telegram Bot project. The audit found significant localization gaps, hardcoded strings, and incomplete functionality that need systematic resolution.

## Input Data
You will receive:
1. **Complete Codebase**: All source files from the project
2. **Audit Report**: `audit_report.md` with detailed findings
3. **Current Translation Files**: `src/localization/translations/en.json` and `src/localization/translations/uk.json`
4. **Localization Utility**: `src/localization/util.py` with `t()` and `t_sync()` functions

## Task Overview
Fix the identified issues systematically, prioritizing user-facing problems and maintaining code quality throughout the process.

## Critical Findings to Address

### 🔴 Priority 1: Hardcoded Strings (1,316 issues)
The audit found extensive hardcoded text that must be localized:
- Direct `reply_text()` calls with Ukrainian text
- Error messages in `raise` statements  
- Log messages visible to users
- Status messages and notifications

### 🌐 Priority 2: Translation Gaps (100 missing keys)
- 1 missing Ukrainian translation
- 99 missing English translations
- Inconsistent key coverage between languages

### ⚙️ Priority 3: Incomplete Functionality (15 issues)
- TODO markers in production code
- `NotImplementedError` placeholders
- Incomplete error handling

## Implementation Strategy

### Phase 1: Translation Infrastructure
1. **Extend Translation Files**: Add all missing keys identified in audit
2. **Key Structure**: Maintain hierarchical organization
3. **Quality Standards**: Ensure natural Ukrainian translations

### Phase 2: Code Refactoring
1. **Systematic Replacement**: Replace hardcoded strings with `t()` calls
2. **Context Preservation**: Maintain existing functionality
3. **Error Handling**: Ensure proper fallbacks for translation failures

### Phase 3: Functionality Completion
1. **TODO Resolution**: Complete or remove TODO items
2. **Error Handling**: Implement proper exception handling
3. **Feature Completion**: Finalize incomplete features

## Specific Instructions

### For Hardcoded String Replacement

**Before:**
```python
await update.message.reply_text("❌ Помилка при завантаженні списку завдань")
```

**After:**
```python
await update.message.reply_text(await t(update, "errors.task_loading_failed"))
```

### For Translation Key Addition

Add to both `en.json` and `uk.json`:
```json
{
  "errors": {
    "task_loading_failed": "❌ Failed to load task list" // EN
    "task_loading_failed": "❌ Помилка при завантаженні списку завдань" // UK
  }
}
```

### For Exception Message Localization

**Before:**
```python
raise ValueError("Invalid configuration provided")
```

**After:**
```python
raise ValueError(t_sync("en", "errors.invalid_configuration"))
```

## Translation Quality Requirements

### Ukrainian Language Standards
- Use natural, idiomatic Ukrainian
- Maintain consistent terminology:
  - "сесія" (not "сеанс") for session
  - "директорія" (not "папка") for directory
  - "помилка" for error, "повідомлення" for message
- Preserve emoji usage for visual consistency
- Use formal tone appropriate for technical interface

### English Language Standards
- Clear, concise, professional language
- Consistent with existing patterns
- Proper technical terminology
- User-friendly error messages with actionable guidance

## Key Categories to Implement

Based on audit findings, focus on these translation categories:

```json
{
  "status": {
    "title": "Bot Status",
    "directory": "Current Directory",
    "claude_session_active": "Claude Session Active",
    "claude_session_inactive": "No Active Session",
    "usage": "Usage Statistics",
    "session_id": "Session ID",
    "usage_info": "Usage Information",
    "usage_error": "Error retrieving usage data"
  },
  "errors_extended": {
    "unknown_action": "Unknown action requested",
    "error_processing": "Error processing request",
    "access_denied": "Access denied",
    "directory_not_found": "Directory not found",
    "not_a_directory": "Path is not a directory",
    "error_changing_directory": "Error changing directory",
    "error_listing_directory": "Error listing directory contents",
    "error_loading_projects": "Error loading available projects",
    "claude_integration_not_available": "Claude integration unavailable",
    "no_session_found": "No active session found"
  },
  "system_errors": {
    "unexpected_error": "An unexpected error occurred"
  }
}
```

## Implementation Checklist

### File Modifications Required
- [ ] `src/localization/translations/en.json` - Add missing keys
- [ ] `src/localization/translations/uk.json` - Add missing keys  
- [ ] `src/bot/handlers/command.py` - Replace hardcoded strings
- [ ] `src/bot/handlers/callback.py` - Replace hardcoded strings
- [ ] `src/bot/handlers/message.py` - Replace hardcoded strings
- [ ] `src/bot/handlers/scheduled_prompts_handler.py` - Replace hardcoded strings
- [ ] `src/bot/middleware/auth.py` - Replace hardcoded strings
- [ ] `src/claude/integration.py` - Replace error messages
- [ ] `src/security/validators.py` - Replace validation messages
- [ ] `src/main.py` - Complete TODO items

### Quality Assurance
- [ ] All hardcoded strings replaced with localization calls
- [ ] Both language files have complete key coverage
- [ ] Ukrainian translations are natural and consistent
- [ ] No functionality is broken during refactoring
- [ ] Error handling is preserved and improved
- [ ] TODO items are resolved or properly documented

## Validation Steps

After implementation:
1. **Syntax Check**: Ensure all JSON files are valid
2. **Key Coverage**: Verify all keys exist in both languages
3. **Functionality Test**: Confirm bot operates correctly
4. **Translation Quality**: Review Ukrainian text for naturalness
5. **Error Scenarios**: Test error handling with localized messages

## Expected Deliverables

1. **Updated Translation Files**:
   - Complete English translations (add 99 missing keys)
   - Complete Ukrainian translations (add 1 missing key)
   - Consistent key structure across both files

2. **Refactored Source Code**:
   - All hardcoded user-facing strings replaced with `t()` calls
   - Proper async/sync localization function usage
   - Maintained functionality with improved UX

3. **Completed Functionality**:
   - Resolved TODO items
   - Proper error handling implementation
   - No remaining `NotImplementedError` placeholders

4. **Quality Report**:
   - Summary of changes made
   - Translation key additions
   - Functionality improvements
   - Remaining issues (if any)

## Success Criteria

The implementation will be successful when:
- ✅ All 1,316 hardcoded strings are properly localized
- ✅ Both language files have 100% key coverage
- ✅ Ukrainian interface is natural and professional
- ✅ All TODO items are resolved or documented
- ✅ Bot functionality is preserved and enhanced
- ✅ Code quality is improved throughout

This comprehensive fix will transform the bot into a fully localized, professional application with complete Ukrainian language support and robust error handling.