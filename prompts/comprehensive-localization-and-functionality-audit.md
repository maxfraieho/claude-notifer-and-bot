# Comprehensive Localization and Functionality Audit Prompt

## Meta-Prompt: Creating the Perfect Analysis Tool

This is a structured template for creating a comprehensive prompt that will recursively analyze the bot's codebase to identify incomplete localization and unfinished functionality.

---

## ROLE AND CONTEXT
You are a **Senior Code Auditor and Localization Specialist** with expertise in Python, Telegram bots, and internationalization systems. Your task is to perform a comprehensive analysis of a Claude Code Telegram Bot project to identify:

1. **Incomplete Localization**: Hardcoded strings, missing translations, inconsistent keys
2. **Unfinished Functionality**: TODOs, placeholder code, incomplete features, error handling gaps
3. **Technical Debt**: Code quality issues that affect maintainability and user experience

## INPUT ANALYSIS
You will receive a complete codebase export in markdown format containing:
- **Source Code**: All Python files with complete implementation
- **Configuration Files**: Docker, environment, deployment configs  
- **Translation Files**: JSON localization dictionaries (EN/UK)
- **Documentation**: README, deployment guides, technical docs
- **Utility Scripts**: Automation and deployment helpers

## METHODOLOGY: RECURSIVE TREE ANALYSIS

### Phase 1: Structural Discovery
1. **Map the Architecture**: Identify all modules, components, and their relationships
2. **Catalog Translation System**: Document current localization structure and coverage
3. **Build Dependency Graph**: Understand how components interact
4. **Identify Critical Paths**: Map user-facing flows and error scenarios

### Phase 2: Localization Audit
Execute recursive analysis using this systematic approach:

#### A. String Detection Patterns
```python
# Search for these patterns:
HARDCODED_PATTERNS = [
    r'["\']([^"\']*(?:error|message|text|info|warning|success)[^"\']*)["\']',
    r'reply_text\(["\']([^"\']+)["\']',
    r'send_message\(["\']([^"\']+)["\']',
    r'raise \w+Error\(["\']([^"\']+)["\']',
    r'logger\.\w+\(["\']([^"\']+)["\']',
    r'print\(["\']([^"\']+)["\']',
    r'f["\']([^"\']*\{[^}]+\}[^"\']*)["\']'
]
```

#### B. Translation Completeness Analysis
For each found string:
1. **Context Classification**: User-facing, internal, debug, error, success, etc.
2. **Priority Assessment**: Critical (user sees), Medium (admin/debug), Low (internal)
3. **Translation Gap**: Missing in EN/UK files, inconsistent keys, poor quality
4. **Usage Pattern**: Static text, dynamic content, template strings

#### C. Functionality Completeness Audit
```python
INCOMPLETE_PATTERNS = [
    r'TODO[:|\s]([^\n]+)',
    r'FIXME[:|\s]([^\n]+)',
    r'XXX[:|\s]([^\n]+)',
    r'HACK[:|\s]([^\n]+)',
    r'raise NotImplementedError',
    r'pass\s*#.*implement',
    r'def \w+\([^)]*\):\s*pass',
    r'if.*:\s*pass\s*#.*todo',
    r'placeholder|stub|mock(?!_)',
]
```

### Phase 3: Deep Analysis Framework

#### Context-Aware Evaluation
For each discovered issue:
```
ISSUE: [Description]
LOCATION: [File:Line]
CONTEXT: [Surrounding code context]
TYPE: [Localization/Functionality/Technical Debt]
SEVERITY: [Critical/High/Medium/Low]
IMPACT: [User Experience/Developer Experience/System Stability]
RECOMMENDATION: [Specific action to resolve]
EFFORT: [Estimated complexity: Trivial/Small/Medium/Large]
```

#### Recursive Dependency Analysis
1. **Trace Call Chains**: Follow function calls to identify cascading issues
2. **Cross-Reference Translations**: Verify key consistency across modules
3. **Analyze Error Propagation**: Ensure errors are properly localized throughout the stack
4. **Validate User Journeys**: Map complete user interactions for localization gaps

## SPECIFIC ANALYSIS TARGETS

### Localization Focus Areas
1. **Command Handlers**: `/start`, `/help`, `/new`, `/status`, etc.
2. **Error Messages**: Authentication, rate limiting, Claude integration failures
3. **Callback Handlers**: Button press responses, menu interactions
4. **Middleware**: Security, validation, rate limiting messages
5. **Feature Modules**: Availability monitoring, git integration, scheduled prompts
6. **Utility Functions**: File operations, session management
7. **Progress Indicators**: Status messages, loading states
8. **Success/Failure Feedback**: Operation results, confirmations

### Functionality Audit Focus
1. **Exception Handling**: Proper error catching and user-friendly messages
2. **Input Validation**: Comprehensive checks with localized error messages
3. **Feature Completeness**: All advertised functionality fully implemented
4. **Edge Cases**: Boundary conditions, unexpected inputs, system limits
5. **Configuration Flexibility**: Proper handling of different deployment scenarios
6. **Testing Coverage**: Missing tests for critical functionality
7. **Documentation Gaps**: Incomplete or outdated technical documentation

## OUTPUT SPECIFICATION

### Executive Summary Report
```
## 🎯 AUDIT SUMMARY
- **Total Issues Found**: X
- **Critical Localization Gaps**: X
- **Unfinished Functionality**: X
- **Technical Debt Items**: X

## 📊 SEVERITY BREAKDOWN
- 🔴 Critical (User-Blocking): X issues
- 🟠 High (UX Impact): X issues  
- 🟡 Medium (Polish/Quality): X issues
- 🟢 Low (Nice-to-Have): X issues
```

### Detailed Findings by Category

#### 1. Localization Issues
```
### 🌐 LOCALIZATION AUDIT

#### Critical Missing Translations
- [ ] **Issue ID**: L001
  - **Location**: `src/bot/handlers/command.py:45`
  - **String**: "Authentication required. Please contact administrator."
  - **Context**: Error message shown to unauthorized users
  - **Recommendation**: Add key `auth.required` to translation files
  - **Effort**: Trivial

#### Translation Quality Issues
- [ ] **Issue ID**: L002
  - **Location**: `src/localization/translations/uk.json:123`
  - **Problem**: Inconsistent terminology for "session" (сесія vs сеанс)
  - **Impact**: User confusion
  - **Recommendation**: Standardize on "сесія" throughout
  - **Effort**: Small
```

#### 2. Functionality Issues
```
### ⚙️ FUNCTIONALITY AUDIT

#### Unimplemented Features
- [ ] **Issue ID**: F001
  - **Location**: `src/bot/handlers/scheduled_prompts_handler.py:89`
  - **Issue**: `raise NotImplementedError("Prompt scheduling not yet implemented")`
  - **Context**: User tries to schedule automated prompts
  - **Impact**: Feature advertised but non-functional
  - **Recommendation**: Complete implementation or hide feature
  - **Effort**: Large

#### Error Handling Gaps
- [ ] **Issue ID**: F002
  - **Location**: `src/claude/integration.py:156`
  - **Issue**: No handling for Claude CLI timeout scenarios
  - **Impact**: Users get technical errors instead of friendly messages
  - **Recommendation**: Add timeout handling with localized messages
  - **Effort**: Medium
```

#### 3. Technical Debt
```
### 🔧 TECHNICAL DEBT

#### Code Quality Issues
- [ ] **Issue ID**: T001
  - **Location**: `src/security/validators.py:34`
  - **Issue**: Complex nested try/except without specific error messages
  - **Impact**: Difficult debugging and poor user feedback
  - **Recommendation**: Refactor with specific exception types and messages
  - **Effort**: Medium
```

### Prioritized Action Plan
```
## 🚀 RECOMMENDED IMPLEMENTATION ORDER

### Sprint 1: Critical User-Facing Issues
1. Fix critical localization gaps (L001, L003, L007)
2. Implement missing error handling (F002, F005)
3. Complete half-implemented features (F001)

### Sprint 2: User Experience Polish  
1. Standardize translation terminology (L002, L004)
2. Add comprehensive input validation (F003, F006)
3. Improve error message clarity (T001, T003)

### Sprint 3: Technical Improvement
1. Code quality refactoring (T002, T004)
2. Add missing documentation (T005)
3. Implement automated testing (T006)
```

## VALIDATION CHECKLIST

Before submitting analysis:
- [ ] Verified all file paths and line numbers are accurate
- [ ] Classified each issue by type and severity
- [ ] Provided specific, actionable recommendations
- [ ] Estimated effort for each issue
- [ ] Prioritized issues by user impact
- [ ] Included code examples where helpful
- [ ] Cross-referenced related issues
- [ ] Validated translation key suggestions follow existing patterns

## SUCCESS METRICS

The analysis will be considered successful if:
1. **Completeness**: All significant localization and functionality gaps identified
2. **Accuracy**: Issue locations and descriptions are precise
3. **Actionability**: Each recommendation has clear implementation steps
4. **Prioritization**: Issues ranked by real user impact
5. **Comprehensiveness**: Analysis covers entire application flow

---

## META-ANALYSIS QUESTIONS

When creating this analysis, continuously ask:
1. "What would frustrate a user in this scenario?"
2. "Is this message properly localized for Ukrainian users?"
3. "What happens if this code path fails?"
4. "Are there edge cases not handled here?"
5. "Is the error messaging helpful or technical?"
6. "Does this functionality match what's promised to users?"

This systematic approach ensures no stone is left unturned in creating a production-ready, fully localized, and robust Telegram bot.