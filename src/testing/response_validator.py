"""
Enhanced Response Validator for DevClaude_bot

Implements intelligent response validation as recommended by the analysis report.
Provides comprehensive validation logic that avoids false positives.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Response validation results"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Structure for validation issues"""
    severity: ValidationResult
    code: str
    message: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class ResponseValidationReport:
    """Comprehensive validation report"""
    command: str
    response_text: str
    overall_status: ValidationResult
    issues: List[ValidationIssue]
    score: int
    recommendations: List[str]
    metadata: Dict[str, Any]


class EnhancedResponseValidator:
    """
    Enhanced response validator with context-aware error detection

    Designed to minimize false positives while catching real issues.
    """

    def __init__(self):
        self.command_specific_rules = self._init_command_rules()
        self.context_patterns = self._init_context_patterns()

    def _init_command_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize command-specific validation rules"""
        return {
            "/version": {
                "expected_content": ["version", "release", "bot"],
                "allowed_terms": ["error handling", "comprehensive error", "architecture"],
                "min_length": 200,
                "required_patterns": [r"version.*\d+\.\d+", r"release.*\d{4}"]
            },
            "/help": {
                "expected_content": ["help", "commands", "usage"],
                "min_length": 100,
                "required_patterns": [r"/\w+", r"command"]
            },
            "/status": {
                "expected_content": ["status", "session", "directory"],
                "min_length": 20,
                "required_patterns": [r"(active|inactive|session|directory)"]
            },
            "/start": {
                "expected_content": ["welcome", "bot", "claude"],
                "min_length": 100,
                "required_patterns": [r"welcome|привіт", r"/\w+"]
            }
        }

    def _init_context_patterns(self) -> Dict[str, List[str]]:
        """Initialize context-aware patterns to avoid false positives"""
        return {
            "legitimate_error_contexts": [
                r"error handling",
                r"comprehensive error",
                r"enhanced error",
                r"error management",
                r"error system",
                r"fix.*error",
                r"handle.*error"
            ],
            "actual_error_indicators": [
                r"error occurred",
                r"command failed",
                r"exception.*raised",
                r"не вдалося",
                r"помилка.*виконання",
                r"failed to.*execute",
                r"something went wrong"
            ],
            "localization_issues": [
                r"\.\w+\.(title|description|error|command)",
                r"\{[^}]+\}",  # Unresolved placeholders
                r"undefined|null(?!\s+values)"  # But not "null values" in content
            ]
        }

    def validate_response(self, command: str, response_text: str,
                         additional_context: Optional[Dict[str, Any]] = None) -> ResponseValidationReport:
        """
        Perform comprehensive response validation

        Args:
            command: The bot command that was executed
            response_text: The bot's response text
            additional_context: Additional context for validation

        Returns:
            ResponseValidationReport: Comprehensive validation results
        """
        logger.debug(f"Validating response for command: {command}")

        issues = []
        score = 100
        recommendations = []
        metadata = {
            "response_length": len(response_text),
            "word_count": len(response_text.split()),
            "has_emojis": bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', response_text)),
            "command": command
        }

        # 1. Check for actual errors (with context awareness)
        error_issues = self._validate_error_indicators(command, response_text)
        issues.extend(error_issues)

        # 2. Check for localization problems
        localization_issues = self._validate_localization(response_text)
        issues.extend(localization_issues)

        # 3. Command-specific validation
        command_issues = self._validate_command_specific(command, response_text)
        issues.extend(command_issues)

        # 4. General quality checks
        quality_issues = self._validate_response_quality(response_text)
        issues.extend(quality_issues)

        # Calculate overall status and score
        overall_status = self._calculate_overall_status(issues)
        score = self._calculate_score(issues, len(response_text))

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, command)

        return ResponseValidationReport(
            command=command,
            response_text=response_text,
            overall_status=overall_status,
            issues=issues,
            score=score,
            recommendations=recommendations,
            metadata=metadata
        )

    def _validate_error_indicators(self, command: str, response_text: str) -> List[ValidationIssue]:
        """Validate for actual error indicators with context awareness"""
        issues = []
        text_lower = response_text.lower()

        # Skip /version command special case (already handled in tester fix)
        if command == "/version" and ("error handling" in text_lower or "comprehensive error" in text_lower):
            logger.debug("Skipping error detection for /version with legitimate error handling mentions")
            return issues

        # Check for legitimate error handling context first
        legitimate_context = False
        for pattern in self.context_patterns["legitimate_error_contexts"]:
            if re.search(pattern, text_lower):
                legitimate_context = True
                logger.debug(f"Found legitimate error context: {pattern}")
                break

        # Only check for actual errors if not in legitimate context
        if not legitimate_context:
            for pattern in self.context_patterns["actual_error_indicators"]:
                if re.search(pattern, text_lower):
                    issues.append(ValidationIssue(
                        severity=ValidationResult.ERROR,
                        code="ACTUAL_ERROR_DETECTED",
                        message=f"Actual error indicator found: {pattern}",
                        context={"pattern": pattern, "command": command}
                    ))
                    break

        return issues

    def _validate_localization(self, response_text: str) -> List[ValidationIssue]:
        """Validate localization and template processing"""
        issues = []

        for pattern in self.context_patterns["localization_issues"]:
            matches = re.findall(pattern, response_text)
            if matches:
                issues.append(ValidationIssue(
                    severity=ValidationResult.WARNING,
                    code="LOCALIZATION_ISSUE",
                    message=f"Potential localization issue: {matches[0]}",
                    context={"matches": matches, "pattern": pattern}
                ))

        return issues

    def _validate_command_specific(self, command: str, response_text: str) -> List[ValidationIssue]:
        """Perform command-specific validation"""
        issues = []

        if command not in self.command_specific_rules:
            return issues

        rules = self.command_specific_rules[command]
        text_lower = response_text.lower()

        # Check minimum length
        if len(response_text) < rules.get("min_length", 0):
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                code="RESPONSE_TOO_SHORT",
                message=f"Response shorter than expected ({len(response_text)} < {rules['min_length']})",
                context={"actual_length": len(response_text), "expected_min": rules['min_length']}
            ))

        # Check expected content
        expected_content = rules.get("expected_content", [])
        missing_content = [content for content in expected_content if content.lower() not in text_lower]
        if missing_content:
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                code="MISSING_EXPECTED_CONTENT",
                message=f"Missing expected content: {missing_content}",
                context={"missing": missing_content, "expected": expected_content}
            ))

        # Check required patterns
        required_patterns = rules.get("required_patterns", [])
        for pattern in required_patterns:
            if not re.search(pattern, response_text, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity=ValidationResult.WARNING,
                    code="MISSING_REQUIRED_PATTERN",
                    message=f"Missing required pattern: {pattern}",
                    context={"pattern": pattern, "command": command}
                ))

        return issues

    def _validate_response_quality(self, response_text: str) -> List[ValidationIssue]:
        """Validate general response quality"""
        issues = []

        # Check for empty response
        if not response_text.strip():
            issues.append(ValidationIssue(
                severity=ValidationResult.CRITICAL,
                code="EMPTY_RESPONSE",
                message="Response is empty",
                context={}
            ))

        # Check for extremely short responses
        elif len(response_text.strip()) < 10:
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                code="VERY_SHORT_RESPONSE",
                message="Response is very short and may not be helpful",
                context={"length": len(response_text)}
            ))

        return issues

    def _calculate_overall_status(self, issues: List[ValidationIssue]) -> ValidationResult:
        """Calculate overall validation status"""
        if not issues:
            return ValidationResult.SUCCESS

        severities = [issue.severity for issue in issues]

        if ValidationResult.CRITICAL in severities:
            return ValidationResult.CRITICAL
        elif ValidationResult.ERROR in severities:
            return ValidationResult.ERROR
        elif ValidationResult.WARNING in severities:
            return ValidationResult.WARNING
        else:
            return ValidationResult.SUCCESS

    def _calculate_score(self, issues: List[ValidationIssue], response_length: int) -> int:
        """Calculate numerical score (0-100)"""
        score = 100

        for issue in issues:
            if issue.severity == ValidationResult.CRITICAL:
                score -= 50
            elif issue.severity == ValidationResult.ERROR:
                score -= 30
            elif issue.severity == ValidationResult.WARNING:
                score -= 10

        # Bonus for good response length
        if response_length > 100:
            score += 5
        if response_length > 500:
            score += 5

        return max(0, min(100, score))

    def _generate_recommendations(self, issues: List[ValidationIssue], command: str) -> List[str]:
        """Generate recommendations based on validation issues"""
        recommendations = []

        issue_codes = [issue.code for issue in issues]

        if "ACTUAL_ERROR_DETECTED" in issue_codes:
            recommendations.append("Investigate and fix the underlying error causing command failure")

        if "LOCALIZATION_ISSUE" in issue_codes:
            recommendations.append("Review localization configuration and ensure all keys are properly translated")

        if "RESPONSE_TOO_SHORT" in issue_codes:
            recommendations.append(f"Enhance {command} response with more helpful information")

        if "MISSING_EXPECTED_CONTENT" in issue_codes:
            recommendations.append(f"Ensure {command} includes all expected information elements")

        if not issues:
            recommendations.append("Response validation passed - no issues detected")

        return recommendations


# Convenience function for easy integration
def validate_bot_response(command: str, response_text: str,
                         additional_context: Optional[Dict[str, Any]] = None) -> ResponseValidationReport:
    """
    Convenience function to validate a bot response

    Args:
        command: The bot command
        response_text: The response text to validate
        additional_context: Optional additional context

    Returns:
        ResponseValidationReport: Validation results
    """
    validator = EnhancedResponseValidator()
    return validator.validate_response(command, response_text, additional_context)