# AI Agent Prompt: Create Advanced Bot Logic Auditor

## Mission
Create a comprehensive Python script that performs **REAL USER EXPERIENCE TESTING** on a Telegram bot by simulating actual user interactions and identifying genuine usability problems that users encounter in practice.

## Context
You are building an advanced auditor for a Claude Code Telegram Bot that needs to find **actual problems users experience**, not just code patterns. The bot has complex localization, command handlers, callback buttons, and Claude integration.

**Real Problems We Need to Catch:**
1. **Commands that are advertised but don't work** (like `/new` showing error)
2. **Non-localized responses** (Ukrainian users getting English errors)
3. **Buttons that do nothing** when pressed
4. **Missing quick actions** (advertised but not implemented)
5. **Failed Claude integration** causing generic error messages
6. **Translation keys showing instead of text** (runtime failures)

## Technical Requirements

### Core Analysis Modules

#### 1. **Command Flow Simulator**
```python
def simulate_user_commands(self):
    """Simulate actual user command interactions"""
    # Test each advertised command
    # Check if handler exists and responds appropriately
    # Verify localization works for responses
    # Detect when commands fail silently or with poor errors
```

#### 2. **Callback Button Tracer**
```python
def trace_button_callbacks(self):
    """Follow button callback chains from UI to implementation"""
    # Find all inline keyboard buttons in the code
    # Trace callback_data to handler functions
    # Identify callbacks that lead nowhere
    # Check if button text matches functionality
```

#### 3. **Localization Runtime Validator**
```python
def validate_runtime_localization(self):
    """Test localization system under real conditions"""
    # Find translation key usage in code
    # Check if keys exist in both language files
    # Test fallback behavior when keys are missing
    # Identify hardcoded strings that show to users
```

#### 4. **User Journey Mapper**  
```python
def map_user_journeys(self):
    """Map complete user interaction flows"""
    # Start -> Command -> Response -> Follow-up Actions
    # Identify broken chains in user workflows
    # Find dead ends where users get stuck
    # Test error recovery paths
```

#### 5. **Integration Point Tester**
```python
def test_integration_points(self):
    """Test external integration failure handling"""
    # Claude CLI integration points
    # File system operations
    # Docker/container interactions
    # Database connections
    # Check what happens when each fails
```

## Advanced Detection Patterns

### Real Problem Indicators

**Critical Issues:**
```python
CRITICAL_PATTERNS = {
    'dead_commands': [
        r'@register_command\(["\'](\w+)["\'].*?async def.*?raise NotImplementedError',
        r'CommandHandler\(["\'](\w+)["\'].*?pass',
    ],
    'silent_failures': [
        r'except.*:\s*pass(?!\s*#)',
        r'except.*:\s*continue(?!\s*#)',
        r'try:.*?except.*?return None',
    ],
    'user_facing_errors': [
        r'reply_text\([rf]?["\'][^"\']*(?:Exception|Error|Failed)[^"\']*["\']',
        r'await.*?reply.*?code\s*1',
    ],
    'broken_buttons': [
        r'InlineKeyboardButton\(["\']([^"\']+)["\'].*?callback_data=["\'](\w+)["\']',
        # Then check if callback exists
    ]
}
```

**UX Issues:**
```python
UX_ISSUES = {
    'mixed_languages': [
        r'[а-яё]+.*?[a-z].*?reply_text',  # Mixed Ukrainian/English
        r'❌.*?[A-Z][a-z]+.*?Error',     # English errors with Ukrainian emoji
    ],
    'poor_error_messages': [
        r'reply_text\(["\']❌[^"\']*["\'].*?\)',  # Generic error symbols
        r'Exception.*?str\(e\)',                   # Raw exception messages
    ],
    'inconsistent_ui': [
        r'KeyboardButton.*?["\']([^"\']*)["\']',   # Find all button texts
        # Check for inconsistent naming/styling
    ]
}
```

### Smart Analysis Methods

#### Context-Aware Code Analysis
```python
def analyze_with_context(self, file_path, function_name):
    """Analyze code with understanding of bot workflow"""
    # Parse AST to understand code structure
    # Trace function calls and data flow
    # Identify user interaction points
    # Check response consistency
```

#### Behavioral Pattern Detection
```python
def detect_behavioral_issues(self):
    """Find patterns that indicate poor user experience"""
    # Commands that should work together but don't
    # Inconsistent response patterns
    # Missing confirmation messages
    # Poor loading state handling
```

## Output Specification

### Smart Report Structure
```markdown
## 🎯 REAL USER IMPACT ANALYSIS

### Critical UX Failures (Fix Today)
- **C01: Dead Command** - `/actions` button exists but leads to error
  - **What User Sees:** Clicks button → "Quick actions unavailable"
  - **Root Cause:** Handler not implemented
  - **Fix:** Implement QuickActionsHandler or hide button

### Localization Failures (Fix This Week)  
- **L01: Mixed Language Error** - Error messages in English for Ukrainian users
  - **What User Sees:** Ukrainian interface → English error message
  - **Root Cause:** Error handling bypasses localization
  - **Fix:** Wrap all error responses with t() function

### UX Inconsistencies (Polish Phase)
- **U01: Inconsistent Button Text** - Some buttons use emoji, others don't
  - **What User Sees:** Inconsistent visual interface
  - **Root Cause:** No UI style guidelines
  - **Fix:** Standardize button text formatting
```

### Actionable Recommendations
Each issue should include:
- **Specific file locations** with line numbers
- **Code snippets** showing the problem
- **Expected vs actual behavior** from user perspective
- **Concrete fix suggestions** with code examples
- **Priority ranking** based on user impact severity

## Advanced Features to Implement

### 1. **Simulation Engine**
- Create mock user interactions
- Test command sequences
- Validate response appropriateness
- Check translation coverage dynamically

### 2. **Flow Analysis**
- Map all possible user paths through the bot
- Identify dead ends and error states
- Check for missing error recovery
- Validate help text accuracy

### 3. **Integration Testing**
- Test Claude CLI integration points
- Validate file operations
- Check authentication flows
- Test external API connections

### 4. **Quality Metrics**
```python
QUALITY_METRICS = {
    'localization_coverage': lambda: self.check_translation_completeness(),
    'error_handling_quality': lambda: self.assess_error_user_friendliness(),
    'ui_consistency': lambda: self.measure_interface_consistency(),
    'feature_completeness': lambda: self.verify_advertised_features(),
}
```

## Success Criteria

The auditor should successfully identify:
1. ✅ **All commands that users can access but don't work**
2. ✅ **Every place where Ukrainian users get English text**
3. ✅ **All buttons that do nothing when clicked**
4. ✅ **Missing error messages or poor error UX**
5. ✅ **Integration failures that show technical errors to users**
6. ✅ **Inconsistent UI patterns that confuse users**

## Implementation Guidelines

### Code Quality Standards
- Use AST parsing for accurate code analysis
- Implement proper error handling
- Create comprehensive test coverage
- Write clear, maintainable code
- Include detailed docstrings

### Performance Considerations  
- Process files efficiently
- Use caching for repeated operations
- Provide progress indicators
- Handle large codebases gracefully

### Extensibility
- Modular design for easy feature addition
- Configuration file support
- Plugin architecture for custom checks
- Export results in multiple formats

## Validation Requirements

Before submitting, verify the auditor:
- [ ] Finds the specific issues mentioned in user testing
- [ ] Provides actionable, specific fixes
- [ ] Prioritizes issues by real user impact
- [ ] Generates clear, readable reports
- [ ] Runs efficiently on the target codebase
- [ ] Handles edge cases gracefully

This advanced auditor should be significantly more effective than basic pattern matching, focusing on **actual user experience problems** rather than just code style issues.