# Manual Testing Guide for Localization E2E Scenarios

This document provides detailed instructions for manually testing the Telegram bot's localization features that require live user interaction.

## Prerequisites

Before starting manual tests:

1. **Bot Setup**: Ensure the bot is running with `docker compose up -d --build`
2. **Telegram Access**: Have access to Telegram app/web with the test user account
3. **Bot Token**: The test user must be authorized (in `ALLOWED_USERS` or have valid auth token)
4. **Logs Access**: Ability to run `docker compose logs claude_bot` to verify expected log entries

## Test Scenario #9: Rate Limit Simulation

**Objective**: Test rate limiting with localized messages

### Prerequisites
- Set user language to Ukrainian (follow Test Scenario #2 first)
- Note current time for log correlation

### Test Steps

1. **Initial Message**
   - Send: `/help`
   - Expected: Normal help response in Ukrainian
   - Log: `INFO: Processing command help, user_id=<USER_ID>`

2. **Rapid Message Sending**
   - Send multiple messages rapidly (5-10 messages within 10 seconds):
     - `/help`
     - `/status`
     - `/projects`
     - `/ls`
     - `/help`
     - `/status`
     - (Continue sending commands rapidly)

3. **Expected Rate Limit Response**
   - **Expected Result**: Localized rate limit warning in Ukrainian
   - **Example Ukrainian Text**: "⏱️ Обмеження швидкості активне. Спробуйте пізніше."
   - **Expected Log**: `WARNING: Rate limit exceeded, user_id=<USER_ID>`

4. **Recovery Test**
   - Wait 30-60 seconds
   - Send: `/help`
   - Expected: Normal response resumes
   - Log: `INFO: Processing command help, user_id=<USER_ID>, success=true`

### Validation Checklist
- [ ] Rate limit message appears in Ukrainian (not English)
- [ ] Rate limit WARNING log generated with user_id
- [ ] Service recovers after waiting period
- [ ] Subsequent messages work normally

### Log Verification Commands
```bash
# Check for rate limit logs
docker compose logs claude_bot | grep -i "rate.limit"

# Check recent localization activity
docker compose logs claude_bot | grep -i "localization\|translation" | tail -10
```

---

## Test Scenario #12: Session Status and Export

**Objective**: Test session management with localization

### Prerequisites
- User language set to Ukrainian
- No active Claude session (run `/end` if needed)

### Test Steps

#### Part A: Session Status Testing

1. **Status Without Session**
   - Send: `/status`
   - **Expected Result**: Ukrainian message indicating no active session
   - **Example Text**: "❌ Немає активної сесії"
   - **Expected Log**: `INFO: Processing command status, has_session=false`

2. **Create New Session**
   - Send: `/new`
   - **Expected Result**: New session interface with Ukrainian buttons
   - **Buttons Expected**: "📝 Почати програмування", "❌ Скасувати"
   - **Expected Log**: `INFO: Processing command new`

3. **Start Session**
   - Click: "📝 Почати програмування" button
   - **Expected Result**: Session ready message in Ukrainian
   - **Expected Log**: `INFO: Processing callback query, callback_data=action:start_coding`

4. **Status With Active Session**
   - Send: `/status`
   - **Expected Result**: Session status with Ukrainian labels
   - **Status Fields**: Session ID, creation time, message count, etc.
   - **Expected Log**: `INFO: Processing command status, has_session=true`

#### Part B: Export Testing

5. **Export Menu**
   - Send: `/export`
   - **Expected Result**: Export options with Ukrainian text
   - **Buttons Expected**: 
     - "📄 Експорт у JSON"
     - "📝 Експорт у Markdown" 
     - "❌ Скасувати"
   - **Expected Log**: `INFO: Processing command export`

6. **JSON Export**
   - Click: "📄 Експорт у JSON" button
   - **Expected Result**: Session data exported in JSON format
   - **Message**: Ukrainian confirmation of export
   - **Expected Log**: `INFO: Processing callback query, callback_data=export:json`

7. **Markdown Export**
   - Click: "📝 Експорт у Markdown" button
   - **Expected Result**: Session data exported in Markdown format
   - **Message**: Ukrainian confirmation of export
   - **Expected Log**: `INFO: Processing callback query, callback_data=export:markdown`

### Validation Checklist

#### Status Command
- [ ] No-session message in Ukrainian
- [ ] New session creation interface localized
- [ ] Session status display uses Ukrainian labels
- [ ] All timestamps formatted appropriately

#### Export Command  
- [ ] Export menu buttons in Ukrainian
- [ ] JSON export works and shows Ukrainian confirmation
- [ ] Markdown export works and shows Ukrainian confirmation
- [ ] Export content is properly formatted

#### Logging
- [ ] All status commands logged with session state
- [ ] Export operations logged with format type
- [ ] No ERROR or CRITICAL logs during testing

### Log Verification Commands
```bash
# Check session-related logs
docker compose logs claude_bot | grep -i "session\|export"

# Check for callback processing
docker compose logs claude_bot | grep -i "callback.*query"

# Check for any errors during testing
docker compose logs claude_bot | grep -E "(ERROR|CRITICAL)" | tail -5
```

---

## Common Troubleshooting

### If Localization Doesn't Work
1. Verify user language setting: Send `/start` and check interface language
2. Check translation files are loaded: `docker compose logs claude_bot | grep "Loaded translations"`
3. Force language change: Click 🌐 button and reselect Ukrainian

### If Rate Limiting Doesn't Trigger
1. Send messages faster (< 1 second intervals)
2. Try different commands to increase request volume
3. Check rate limit configuration in container logs

### If Sessions Don't Work
1. Ensure Claude CLI is authenticated: `docker compose logs claude_bot | grep "Claude CLI"`
2. Check no authentication errors in logs
3. Try restarting container: `docker compose restart claude_bot`

### Log Analysis
```bash
# Real-time log monitoring during tests
docker compose logs claude_bot -f

# Check localization system health
docker compose logs claude_bot | grep -E "(localization|translation)" | head -5

# Verify no critical issues
docker compose logs claude_bot | grep -E "(ERROR|CRITICAL)" | wc -l
```

## Test Completion

After completing both manual tests:

1. **Update Test Report**: Mark scenarios #9 and #12 as "passed" or "failed" with details
2. **Log Export**: Save relevant logs for documentation
3. **Screenshot**: Take screenshots of Ukrainian interface for visual confirmation

## Success Criteria

Both tests are considered successful when:
- All UI text appears in Ukrainian (not English fallbacks)
- Expected functionality works as described
- Logs show proper processing without errors
- No crashes or unhandled exceptions occur