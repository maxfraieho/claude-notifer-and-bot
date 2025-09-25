"""DRACON Schema Storage and File Management System.

This module provides structured file system management for DRACON schemas
with automatic directory creation, versioning, and metadata tracking.

Directory Structure:
- drn/reverse/  - Schemas from reverse engineering
- drn/build/    - Base schemas for system framework development
- drn/audit/    - Testing and validation schemas
- drn/library/  - Reusable schema components
- drn/active/   - Currently active schemas
- drn/archive/  - Historical schema versions
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
import yaml

logger = structlog.get_logger()


class DraconStorageManager:
    """Manages DRACON schema file storage and organization."""

    def __init__(self, base_path: str):
        """Initialize storage manager."""
        self.base_path = Path(base_path)
        self.drn_root = self.base_path / "drn"
        self.logger = logger.bind(component="dracon_storage")

        # Define directory structure
        self.directories = {
            'reverse': self.drn_root / "reverse",    # Reverse engineering results
            'build': self.drn_root / "build",       # Base framework schemas
            'audit': self.drn_root / "audit",       # Testing schemas
            'library': self.drn_root / "library",   # Reusable components
            'active': self.drn_root / "active",     # Currently active schemas
            'archive': self.drn_root / "archive",   # Historical versions
            'temp': self.drn_root / "temp",         # Temporary work files
            'export': self.drn_root / "export",     # Export formats (png, svg, etc.)
        }

        # Initialize directories
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create directory structure if it doesn't exist."""
        try:
            for dir_name, dir_path in self.directories.items():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug("Directory ensured", directory=dir_name, path=str(dir_path))

                # Create README files for documentation
                readme_path = dir_path / "README.md"
                if not readme_path.exists():
                    self._create_directory_readme(dir_name, readme_path)

            self.logger.info("DRACON directory structure initialized", root=str(self.drn_root))
        except Exception as e:
            self.logger.error("Failed to create directory structure", error=str(e))
            raise

    def _create_directory_readme(self, dir_name: str, readme_path: Path) -> None:
        """Create README file for directory documentation."""
        readme_content = {
            'reverse': """# DRACON Reverse Engineering Schemas

This directory contains DRACON schemas generated from reverse engineering existing bot code.

## File Naming Convention:
- `{project_name}_reverse_{timestamp}.yaml` - Main reverse engineered schema
- `{project_name}_analysis_{timestamp}.json` - Analysis metadata
- `{project_name}_suggestions_{timestamp}.json` - Refactoring suggestions

## Usage:
- Review reverse engineered schemas for understanding current architecture
- Use as baseline for refactoring and modernization
- Compare with build/ schemas for migration planning
""",
            'build': """# DRACON Build Schemas

Base schemas for system framework development and architecture planning.

## File Types:
- `framework_*.yaml` - Core framework patterns
- `template_*.yaml` - Reusable templates
- `pattern_*.yaml` - Common design patterns

## Usage:
- Starting point for new bot development
- Reference architectures and best practices
- Template schemas for rapid prototyping
""",
            'audit': """# DRACON Audit Schemas

Testing and validation schemas for quality assurance.

## File Types:
- `test_*.yaml` - Test case schemas
- `validation_*.yaml` - Validation rule sets
- `benchmark_*.yaml` - Performance benchmarks

## Usage:
- Schema validation testing
- Performance analysis
- Quality assurance workflows
""",
            'library': """# DRACON Component Library

Reusable schema components and modules.

## File Types:
- `component_*.yaml` - Individual components
- `module_*.yaml` - Component groups
- `pattern_*.yaml` - Interaction patterns

## Usage:
- Import components into larger schemas
- Standardized building blocks
- Consistent design patterns
""",
            'active': """# Active DRACON Schemas

Currently active and deployed schemas.

## File Types:
- `current_*.yaml` - Active production schemas
- `staging_*.yaml` - Staging environment schemas
- `dev_*.yaml` - Development schemas

## Usage:
- Current system state representation
- Production deployment tracking
- Environment-specific configurations
""",
            'archive': """# DRACON Schema Archive

Historical versions and backup schemas.

## File Naming:
- `{schema_name}_v{version}_{timestamp}.yaml`
- `backup_{original_name}_{timestamp}.yaml`

## Usage:
- Version history tracking
- Rollback capabilities
- Change analysis
""",
            'temp': """# Temporary DRACON Files

Working directory for temporary schema operations.

## File Types:
- `work_*.yaml` - Work in progress schemas
- `merge_*.yaml` - Schema merge operations
- `convert_*.yaml` - Format conversion temporary files

## Note:
Files in this directory may be automatically cleaned up.
""",
            'export': """# DRACON Export Formats

Generated visual and export formats of schemas.

## File Types:
- `{schema_name}.png` - Visual diagrams
- `{schema_name}.svg` - Vector graphics
- `{schema_name}.json` - JSON export
- `{schema_name}.md` - Documentation export

## Usage:
- Visual representation of schemas
- Documentation generation
- Presentation materials
"""
        }

        content = readme_content.get(dir_name, f"# DRACON {dir_name.title()} Directory\n\nAutomatically generated directory for DRACON schemas.")
        readme_path.write_text(content, encoding='utf-8')

    def save_schema(self, schema_yaml: str, category: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """Save DRACON schema to appropriate directory."""
        if category not in self.directories:
            raise ValueError(f"Unknown category: {category}. Available: {list(self.directories.keys())}")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.yaml"
        file_path = self.directories[category] / filename

        try:
            # Save YAML schema
            file_path.write_text(schema_yaml, encoding='utf-8')

            # Save metadata if provided
            if metadata:
                metadata_path = file_path.with_suffix('.json')
                metadata['saved_at'] = datetime.now().isoformat()
                metadata['category'] = category
                metadata['file_path'] = str(file_path)

                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.info("Schema saved", category=category, name=name, path=str(file_path))
            return str(file_path), filename

        except Exception as e:
            self.logger.error("Failed to save schema", error=str(e), category=category, name=name)
            raise

    def load_schema(self, category: str, filename: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Load DRACON schema and its metadata."""
        if category not in self.directories:
            raise ValueError(f"Unknown category: {category}")

        file_path = self.directories[category] / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Schema not found: {file_path}")

        try:
            # Load YAML schema
            schema_yaml = file_path.read_text(encoding='utf-8')

            # Load metadata if exists
            metadata_path = file_path.with_suffix('.json')
            metadata = None
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

            self.logger.info("Schema loaded", category=category, filename=filename)
            return schema_yaml, metadata

        except Exception as e:
            self.logger.error("Failed to load schema", error=str(e), category=category, filename=filename)
            raise

    def list_schemas(self, category: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """List all schemas in category or all categories."""
        results = {}

        categories = [category] if category and category in self.directories else self.directories.keys()

        for cat in categories:
            cat_path = self.directories[cat]
            schemas = []

            for yaml_file in cat_path.glob("*.yaml"):
                schema_info = {
                    'filename': yaml_file.name,
                    'created': datetime.fromtimestamp(yaml_file.stat().st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(yaml_file.stat().st_mtime).isoformat(),
                    'size': yaml_file.stat().st_size
                }

                # Add metadata if available
                metadata_path = yaml_file.with_suffix('.json')
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            schema_info['metadata'] = metadata
                    except Exception as e:
                        logger.warning("Failed to load metadata for schema", schema=schema_file, error=str(e))
                        pass

                schemas.append(schema_info)

            # Sort by creation time (newest first)
            schemas.sort(key=lambda x: x['created'], reverse=True)
            results[cat] = schemas

        return results

    def archive_schema(self, category: str, filename: str, new_version: Optional[str] = None) -> str:
        """Archive a schema to the archive directory."""
        source_path = self.directories[category] / filename
        if not source_path.exists():
            raise FileNotFoundError(f"Schema not found: {source_path}")

        # Generate archive filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = source_path.stem
        version = new_version or "auto"
        archive_name = f"{base_name}_v{version}_{timestamp}.yaml"
        archive_path = self.directories['archive'] / archive_name

        try:
            # Copy schema to archive
            shutil.copy2(source_path, archive_path)

            # Copy metadata if exists
            metadata_source = source_path.with_suffix('.json')
            if metadata_source.exists():
                metadata_archive = archive_path.with_suffix('.json')
                shutil.copy2(metadata_source, metadata_archive)

            self.logger.info("Schema archived", original=str(source_path), archive=str(archive_path))
            return str(archive_path)

        except Exception as e:
            self.logger.error("Failed to archive schema", error=str(e))
            raise

    def delete_schema(self, category: str, filename: str, archive_first: bool = True) -> bool:
        """Delete a schema, optionally archiving it first."""
        source_path = self.directories[category] / filename
        if not source_path.exists():
            raise FileNotFoundError(f"Schema not found: {source_path}")

        try:
            # Archive before deletion if requested
            if archive_first:
                self.archive_schema(category, filename)

            # Delete schema file
            source_path.unlink()

            # Delete metadata if exists
            metadata_path = source_path.with_suffix('.json')
            if metadata_path.exists():
                metadata_path.unlink()

            self.logger.info("Schema deleted", category=category, filename=filename, archived=archive_first)
            return True

        except Exception as e:
            self.logger.error("Failed to delete schema", error=str(e))
            raise

    def copy_schema(self, source_category: str, filename: str, target_category: str, new_name: Optional[str] = None) -> str:
        """Copy schema between categories."""
        source_path = self.directories[source_category] / filename
        if not source_path.exists():
            raise FileNotFoundError(f"Schema not found: {source_path}")

        target_name = new_name or filename
        target_path = self.directories[target_category] / target_name

        try:
            # Copy schema
            shutil.copy2(source_path, target_path)

            # Copy metadata if exists
            metadata_source = source_path.with_suffix('.json')
            if metadata_source.exists():
                metadata_target = target_path.with_suffix('.json')
                shutil.copy2(metadata_source, metadata_target)

                # Update metadata with new location
                with open(metadata_target, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                metadata['copied_from'] = str(source_path)
                metadata['copied_at'] = datetime.now().isoformat()
                metadata['category'] = target_category

                with open(metadata_target, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.info("Schema copied", source=str(source_path), target=str(target_path))
            return str(target_path)

        except Exception as e:
            self.logger.error("Failed to copy schema", error=str(e))
            raise

    def export_schema_visual(self, category: str, filename: str, format: str = 'png') -> str:
        """Export schema as visual diagram (placeholder for future implementation)."""
        # This would integrate with diagram generation tools
        source_path = self.directories[category] / filename
        if not source_path.exists():
            raise FileNotFoundError(f"Schema not found: {source_path}")

        export_name = f"{source_path.stem}.{format}"
        export_path = self.directories['export'] / export_name

        # Placeholder - would implement actual diagram generation
        export_path.write_text(f"# Visual export placeholder for {filename}\n# Format: {format}\n# Generated: {datetime.now().isoformat()}")

        self.logger.info("Schema visual export created", source=str(source_path), export=str(export_path))
        return str(export_path)

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics and usage information."""
        stats = {
            'total_schemas': 0,
            'total_size': 0,
            'categories': {},
            'oldest_schema': None,
            'newest_schema': None
        }

        oldest_time = None
        newest_time = None

        for category, path in self.directories.items():
            yaml_files = list(path.glob("*.yaml"))
            category_size = sum(f.stat().st_size for f in yaml_files)

            stats['categories'][category] = {
                'count': len(yaml_files),
                'size': category_size
            }

            stats['total_schemas'] += len(yaml_files)
            stats['total_size'] += category_size

            # Track oldest and newest
            for yaml_file in yaml_files:
                file_time = yaml_file.stat().st_ctime
                if oldest_time is None or file_time < oldest_time:
                    oldest_time = file_time
                    stats['oldest_schema'] = str(yaml_file)
                if newest_time is None or file_time > newest_time:
                    newest_time = file_time
                    stats['newest_schema'] = str(yaml_file)

        return stats

    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified hours."""
        import time

        temp_path = self.directories['temp']
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0

        for temp_file in temp_path.iterdir():
            if temp_file.is_file():
                file_age = current_time - temp_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        temp_file.unlink()
                        cleaned_count += 1
                        self.logger.debug("Temp file cleaned", file=str(temp_file))
                    except Exception as e:
                        self.logger.warning("Failed to clean temp file", file=str(temp_file), error=str(e))

        self.logger.info("Temp file cleanup completed", cleaned=cleaned_count)
        return cleaned_count

    def validate_schema_integrity(self) -> Dict[str, List[str]]:
        """Validate integrity of all stored schemas."""
        issues = {
            'invalid_yaml': [],
            'missing_metadata': [],
            'corrupted_files': []
        }

        for category, path in self.directories.items():
            for yaml_file in path.glob("*.yaml"):
                try:
                    # Test YAML parsing
                    content = yaml_file.read_text(encoding='utf-8')
                    yaml.safe_load(content)

                    # Check for metadata
                    metadata_path = yaml_file.with_suffix('.json')
                    if not metadata_path.exists():
                        issues['missing_metadata'].append(str(yaml_file))

                except yaml.YAMLError:
                    issues['invalid_yaml'].append(str(yaml_file))
                except Exception:
                    issues['corrupted_files'].append(str(yaml_file))

        return issues