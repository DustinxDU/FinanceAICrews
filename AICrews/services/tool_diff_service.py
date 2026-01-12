"""
Tool Diff Service - Incremental tool updates with field-level diff.

Implements intelligent discovery that preserves user metadata while updating
only changed system fields. Supports soft-delete for removed tools.

Design Principles:
1. User metadata (display_name, tags, rate_limit, etc.) is sacred - never overwrite
2. System fields (description, input_schema) are updated when changed
3. Deleted tools are marked inactive, not physically deleted (audit trail)
4. Field-level diff minimizes database writes
5. Uses PostgreSQL upsert for concurrency safety (idempotent inserts)
"""
import hashlib
import json
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from AICrews.database.models.mcp import MCPTool


def func_now():
    """
    Get current timestamp for database inserts.

    Uses Python datetime for cross-database compatibility (SQLite, PostgreSQL).
    This is evaluated in Python, not by the database server.
    """
    return datetime.now()


@dataclass
class ToolDiff:
    """Represents changes detected in a tool."""
    tool_name: str
    action: str  # "create", "update", "delete", "unchanged"
    changed_fields: Set[str]  # Only for action="update"
    old_values: Dict[str, any] = None
    new_values: Dict[str, any] = None


class ToolDiffService:
    """
    Service for incremental tool updates with field-level diff.

    Field Classification:
    - System fields (auto-updated): description, input_schema, required_params
    - User metadata (preserved): display_name*, tags, rate_limit, cache_ttl, category
    - Control fields (user-managed): is_active

    * display_name is user metadata IF user has customized it (differs from tool_name).
      If display_name == tool_name, it's treated as system default and can be updated.
    """

    # System fields that should be updated from MCP server
    SYSTEM_FIELDS = {"description", "input_schema", "required_params"}

    # User metadata fields that should NEVER be overwritten
    USER_METADATA_FIELDS = {"tags", "rate_limit", "cache_ttl", "is_active"}

    # Conditional field: display_name is user metadata if customized
    CONDITIONAL_FIELDS = {"display_name", "category"}

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def compute_field_diff(
        self,
        existing_tool: MCPTool,
        fresh_data: Dict[str, any]
    ) -> Set[str]:
        """
        Compute which system fields have changed.

        Args:
            existing_tool: Current database record
            fresh_data: Fresh data from MCP server (uses camelCase keys)

        Returns:
            Set of field names that changed
        """
        changed = set()

        # Map database field names to MCP API field names
        field_mapping = {
            "input_schema": "inputSchema",
            "description": "description",
            "required_params": "required"  # Extracted from inputSchema
        }

        for field in self.SYSTEM_FIELDS:
            old_value = getattr(existing_tool, field, None)

            # Get corresponding value from fresh data
            if field == "input_schema":
                new_value = fresh_data.get(field_mapping.get(field, field))
            elif field == "required_params":
                # Skip - extracted from inputSchema, not a direct field
                continue
            else:
                new_value = fresh_data.get(field_mapping.get(field, field))

            # Normalize for comparison
            if field == "input_schema":
                # Compare schema hashes to detect changes
                old_hash = self._hash_schema(old_value)
                new_hash = self._hash_schema(new_value)
                if old_hash != new_hash:
                    changed.add(field)
            else:
                # Direct comparison for text fields
                if old_value != new_value:
                    changed.add(field)

        return changed

    def _hash_schema(self, schema: Optional[Dict]) -> str:
        """Generate stable hash for schema comparison."""
        if not schema:
            return ""

        # Sort keys for stable hash
        normalized = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _is_display_name_customized(self, tool: MCPTool) -> bool:
        """
        Check if display_name was customized by user.

        If display_name == tool_name, it's considered system default.
        If they differ, user has customized it.
        """
        return tool.display_name != tool.tool_name

    def _is_category_customized(self, tool: MCPTool) -> bool:
        """
        Check if category was customized by user.

        If category is "custom" (default), it's considered customized.
        Otherwise, it can be updated.
        """
        return tool.category == "custom"

    def apply_incremental_update(
        self,
        server_id: int,
        fresh_tools: List[Dict[str, any]]
    ) -> Dict[str, int]:
        """
        Apply incremental update with field-level diff.

        Uses PostgreSQL upsert for concurrency safety - multiple concurrent
        discovery calls will not cause duplicate key errors.

        Args:
            server_id: MCP server ID
            fresh_tools: Fresh tool data from MCP server

        Returns:
            Stats dict: {created: int, updated: int, deleted: int, unchanged: int}
        """
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}

        # Fetch existing tools for this server
        existing_tools = self.db.execute(
            select(MCPTool).where(
                MCPTool.server_id == server_id,
                MCPTool.is_active == True  # Only active tools
            )
        ).scalars().all()

        # Build lookup: tool_name -> MCPTool
        existing_by_name = {tool.tool_name: tool for tool in existing_tools}

        # Track which tools we've seen in fresh data
        seen_tools = set()

        # Process fresh tools using bulk upsert for concurrency safety
        for tool_data in fresh_tools:
            tool_name = tool_data["name"]
            seen_tools.add(tool_name)

            existing = existing_by_name.get(tool_name)

            if not existing:
                # Try to insert - if concurrent insert happened, ignore conflict
                inserted = self._upsert_tool(server_id, tool_data)
                if inserted:
                    stats["created"] += 1
                else:
                    # Another request created it first - count as unchanged
                    stats["unchanged"] += 1
            else:
                # Existing tool - apply field-level diff
                changed_fields = self.compute_field_diff(existing, tool_data)

                if changed_fields:
                    self._update_tool_fields(existing, tool_data, changed_fields)
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1

        # Mark deleted tools as inactive (soft delete)
        for tool_name, tool in existing_by_name.items():
            if tool_name not in seen_tools:
                tool.is_active = False
                stats["deleted"] += 1

        self.db.commit()
        return stats

    def _upsert_tool(self, server_id: int, tool_data: Dict) -> bool:
        """
        Insert a new tool using PostgreSQL upsert.

        Returns True if inserted, False if already existed (concurrent insert).
        """
        tool_name = tool_data["name"]
        display_name = tool_data.get("display_name") or tool_name

        # Build insert statement
        stmt = pg_insert(MCPTool).values(
            server_id=server_id,
            tool_name=tool_name,
            display_name=display_name,
            description=tool_data.get("description"),
            input_schema=tool_data.get("inputSchema"),
            required_params=self._extract_required_params(tool_data.get("inputSchema")),
            is_active=True,
            created_at=func_now(),
            updated_at=func_now(),
        )

        # Use ON CONFLICT DO NOTHING - if tool already exists, silently skip
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["server_id", "tool_name"]
        )

        try:
            self.db.execute(stmt)
            return True
        except IntegrityError:
            # Another concurrent request inserted this tool first
            self.db.rollback()
            return False

    def _create_tool(self, server_id: int, tool_data: Dict) -> MCPTool:
        """Create new tool from fresh data."""
        tool_name = tool_data["name"]
        display_name = tool_data.get("display_name") or tool_name

        new_tool = MCPTool(
            server_id=server_id,
            tool_name=tool_name,
            display_name=display_name,
            description=tool_data.get("description"),
            input_schema=tool_data.get("inputSchema"),
            required_params=self._extract_required_params(tool_data.get("inputSchema")),
            is_active=True
        )

        self.db.add(new_tool)
        return new_tool

    def _update_tool_fields(
        self,
        existing: MCPTool,
        fresh_data: Dict,
        changed_fields: Set[str]
    ):
        """
        Update only changed system fields, preserve user metadata.

        Args:
            existing: Existing tool record
            fresh_data: Fresh data from MCP server
            changed_fields: Set of fields that changed
        """
        for field in changed_fields:
            if field == "input_schema":
                existing.input_schema = fresh_data.get("inputSchema")
                # Also update required_params if schema changed
                existing.required_params = self._extract_required_params(
                    fresh_data.get("inputSchema")
                )
            elif field == "description":
                existing.description = fresh_data.get("description")
            # Other system fields can be added here

        # Conditionally update display_name if not customized
        if not self._is_display_name_customized(existing):
            new_display = fresh_data.get("display_name") or fresh_data["name"]
            if existing.display_name != new_display:
                existing.display_name = new_display

        # Never touch user metadata: tags, rate_limit, cache_ttl, is_active

    def _extract_required_params(self, input_schema: Optional[Dict]) -> List[str]:
        """Extract required parameter names from input schema."""
        if not input_schema:
            return []

        return input_schema.get("required", [])

    def get_diff_summary(
        self,
        server_id: int,
        fresh_tools: List[Dict[str, any]]
    ) -> List[ToolDiff]:
        """
        Preview what changes would be made without committing.

        Useful for UI "preview changes" feature.

        Args:
            server_id: MCP server ID
            fresh_tools: Fresh tool data from MCP server

        Returns:
            List of ToolDiff objects describing changes
        """
        diffs = []

        # Fetch existing tools
        existing_tools = self.db.execute(
            select(MCPTool).where(
                MCPTool.server_id == server_id,
                MCPTool.is_active == True
            )
        ).scalars().all()

        existing_by_name = {tool.tool_name: tool for tool in existing_tools}
        seen_tools = set()

        # Check for creates and updates
        for tool_data in fresh_tools:
            tool_name = tool_data["name"]
            seen_tools.add(tool_name)

            existing = existing_by_name.get(tool_name)

            if not existing:
                diffs.append(ToolDiff(
                    tool_name=tool_name,
                    action="create",
                    changed_fields=set(),
                    new_values=tool_data
                ))
            else:
                changed_fields = self.compute_field_diff(existing, tool_data)

                if changed_fields:
                    old_values = {
                        field: getattr(existing, field)
                        for field in changed_fields
                    }
                    new_values = {
                        field: tool_data.get(field)
                        for field in changed_fields
                    }

                    diffs.append(ToolDiff(
                        tool_name=tool_name,
                        action="update",
                        changed_fields=changed_fields,
                        old_values=old_values,
                        new_values=new_values
                    ))
                else:
                    diffs.append(ToolDiff(
                        tool_name=tool_name,
                        action="unchanged",
                        changed_fields=set()
                    ))

        # Check for deletes
        for tool_name, tool in existing_by_name.items():
            if tool_name not in seen_tools:
                diffs.append(ToolDiff(
                    tool_name=tool_name,
                    action="delete",
                    changed_fields=set()
                ))

        return diffs


def get_tool_diff_service(db: Session) -> ToolDiffService:
    """Factory function to get ToolDiffService instance."""
    return ToolDiffService(db)
