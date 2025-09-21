# DRACON Reverse Engineering Schemas

This directory contains DRACON schemas generated from reverse engineering existing bot code.

## File Naming Convention:
- `{project_name}_reverse_{timestamp}.yaml` - Main reverse engineered schema
- `{project_name}_analysis_{timestamp}.json` - Analysis metadata
- `{project_name}_suggestions_{timestamp}.json` - Refactoring suggestions

## Usage:
- Review reverse engineered schemas for understanding current architecture
- Use as baseline for refactoring and modernization
- Compare with build/ schemas for migration planning
