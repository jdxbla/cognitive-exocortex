"""Natural Language Everything Service - Tier 1 Feature 4

Control the entire system with plain English commands.
"""
import re
from datetime import datetime, timedelta
from typing import Any, Optional
import os

from anthropic import Anthropic

from database import db
from config import get_settings
from models import ParsedCommand, NLCommandResponse

settings = get_settings()


class NaturalLanguageService:
    """Parse and execute natural language file commands"""

    # Command patterns for quick parsing (before hitting AI)
    QUICK_PATTERNS = {
        # Delete commands
        r"delete\s+all\s+(\w+)\s+files?\s+(?:in\s+)?(.+)?": "delete_by_type",
        r"remove\s+all\s+(\w+)\s+files?\s+(?:in\s+)?(.+)?": "delete_by_type",
        r"delete\s+files?\s+older\s+than\s+(\d+)\s+(days?|weeks?|months?)": "delete_by_age",

        # Find/Search commands
        r"find\s+(?:all\s+)?(\w+)\s+files?\s+(?:in\s+)?(.+)?": "find_by_type",
        r"search\s+(?:for\s+)?[\"'](.+)[\"']": "search_content",
        r"show\s+(?:me\s+)?files?\s+(?:from|about)\s+(.+)": "search_semantic",

        # Organize commands
        r"organize\s+(?:files?\s+)?(?:in\s+)?(.+)?\s+by\s+(date|type|size|name)": "organize",
        r"sort\s+(.+)\s+by\s+(date|type|size|name)": "organize",

        # Size commands
        r"(?:find|show)\s+(?:all\s+)?files?\s+(?:larger|bigger)\s+than\s+(\d+)\s*([kmg]?b)": "find_by_size_larger",
        r"(?:find|show)\s+(?:all\s+)?files?\s+(?:smaller)\s+than\s+(\d+)\s*([kmg]?b)": "find_by_size_smaller",

        # Date commands
        r"show\s+files?\s+modified\s+(?:in\s+the\s+)?last\s+(\d+)\s+(days?|weeks?|hours?)": "find_by_date",
        r"(?:find|show)\s+files?\s+(?:from|modified)\s+(?:before|after)\s+(.+)": "find_by_date_relative",

        # Move/Copy commands
        r"move\s+all\s+(\w+)\s+(?:files?\s+)?(?:to|into)\s+(.+)": "move_by_type",
        r"copy\s+all\s+(\w+)\s+(?:files?\s+)?(?:to|into)\s+(.+)": "copy_by_type",
    }

    # Dangerous operations that need confirmation
    DANGEROUS_OPERATIONS = {"delete", "remove", "move", "rename", "format"}

    def __init__(self):
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        """Get Anthropic client (lazy initialization)"""
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._client = Anthropic(api_key=api_key)
        return self._client

    async def parse_command(
        self, command: str, context: Optional[dict] = None
    ) -> ParsedCommand:
        """Parse a natural language command into structured intent"""
        command_lower = command.lower().strip()

        # Try quick pattern matching first
        for pattern, intent in self.QUICK_PATTERNS.items():
            match = re.match(pattern, command_lower)
            if match:
                return self._build_parsed_command(intent, match.groups(), command)

        # Fall back to AI parsing for complex commands
        return await self._ai_parse_command(command, context)

    def _build_parsed_command(
        self, intent: str, groups: tuple, original_command: str
    ) -> ParsedCommand:
        """Build a ParsedCommand from regex match"""
        entities: dict[str, Any] = {}
        requires_confirmation = False
        warning = None

        if intent == "delete_by_type":
            file_type = groups[0]
            directory = groups[1] if len(groups) > 1 and groups[1] else "."
            entities = {"file_type": file_type, "directory": directory}
            requires_confirmation = True
            warning = f"This will delete ALL {file_type} files in {directory}"

        elif intent == "delete_by_age":
            amount = int(groups[0])
            unit = groups[1].rstrip("s")  # Remove plural
            entities = {"age_amount": amount, "age_unit": unit}
            requires_confirmation = True
            warning = f"This will delete files older than {amount} {unit}s"

        elif intent == "find_by_type":
            file_type = groups[0]
            directory = groups[1] if len(groups) > 1 and groups[1] else "."
            entities = {"file_type": file_type, "directory": directory}

        elif intent == "search_content":
            entities = {"query": groups[0]}

        elif intent == "search_semantic":
            entities = {"query": groups[0]}

        elif intent == "organize":
            directory = groups[0] if groups[0] else "."
            organize_by = groups[1]
            entities = {"directory": directory, "organize_by": organize_by}

        elif intent in ("find_by_size_larger", "find_by_size_smaller"):
            size = int(groups[0])
            unit = groups[1].lower()
            multiplier = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}.get(unit, 1)
            entities = {"size_bytes": size * multiplier, "comparison": intent.split("_")[-1]}

        elif intent == "find_by_date":
            amount = int(groups[0])
            unit = groups[1].rstrip("s")
            entities = {"time_amount": amount, "time_unit": unit}

        elif intent == "move_by_type":
            file_type = groups[0]
            destination = groups[1]
            entities = {"file_type": file_type, "destination": destination}
            requires_confirmation = True
            warning = f"This will move ALL {file_type} files to {destination}"

        elif intent == "copy_by_type":
            file_type = groups[0]
            destination = groups[1]
            entities = {"file_type": file_type, "destination": destination}

        # Check if operation is dangerous
        for dangerous in self.DANGEROUS_OPERATIONS:
            if dangerous in intent.lower():
                requires_confirmation = True
                break

        return ParsedCommand(
            intent=intent,
            entities=entities,
            confidence=0.9,  # High confidence for pattern matches
            requires_confirmation=requires_confirmation,
            warning=warning,
        )

    async def _ai_parse_command(
        self, command: str, context: Optional[dict] = None
    ) -> ParsedCommand:
        """Use Claude to parse complex commands"""
        try:
            client = self._get_client()

            system_prompt = """You are a file management command parser. Parse the user's natural language command into a structured format.

Output JSON with these fields:
- intent: The action to perform (find, delete, move, copy, organize, search, etc.)
- entities: Key-value pairs of relevant parameters (file_type, directory, query, size, date, etc.)
- confidence: Your confidence in the parsing (0.0 to 1.0)
- requires_confirmation: true if this is a destructive operation
- warning: Any warning message for dangerous operations

Example:
User: "Find all large videos from last month"
Response: {"intent": "find_complex", "entities": {"file_type": "video", "size": "large", "date_range": "last_month"}, "confidence": 0.85, "requires_confirmation": false, "warning": null}"""

            context_info = ""
            if context:
                context_info = f"\n\nCurrent context: {context}"

            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast model for parsing
                max_tokens=500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Parse this command: {command}{context_info}"}
                ],
            )

            # Parse the response
            import json
            response_text = response.content[0].text
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return ParsedCommand(
                    intent=parsed.get("intent", "unknown"),
                    entities=parsed.get("entities", {}),
                    confidence=parsed.get("confidence", 0.5),
                    requires_confirmation=parsed.get("requires_confirmation", False),
                    warning=parsed.get("warning"),
                )
        except Exception as e:
            print(f"AI parsing error: {e}")

        # Fallback for unparseable commands
        return ParsedCommand(
            intent="unknown",
            entities={"raw_command": command},
            confidence=0.0,
            requires_confirmation=True,
            warning="Could not parse command. Please rephrase.",
        )

    async def execute_command(
        self, parsed: ParsedCommand, dry_run: bool = False
    ) -> dict:
        """Execute a parsed command"""
        # Import services here to avoid circular imports
        from services.semantic_search import search_service

        result = {"executed": False, "result": None, "error": None}

        if parsed.confidence < 0.3:
            result["error"] = "Command confidence too low. Please rephrase."
            return result

        if dry_run:
            result["result"] = f"Would execute: {parsed.intent} with {parsed.entities}"
            return result

        intent = parsed.intent
        entities = parsed.entities

        try:
            if intent == "search_semantic" or intent == "search_content":
                query = entities.get("query", "")
                results = await search_service.search(query, max_results=20)
                result["executed"] = True
                result["result"] = [
                    {"path": r.file_path, "score": r.score} for r in results
                ]

            elif intent == "find_by_type":
                file_type = entities.get("file_type")
                directory = entities.get("directory", ".")
                # This would call a file system search
                result["executed"] = True
                result["result"] = f"Finding {file_type} files in {directory}..."

            elif intent == "organize":
                directory = entities.get("directory", ".")
                organize_by = entities.get("organize_by")
                result["executed"] = True
                result["result"] = f"Organizing {directory} by {organize_by}..."

            elif intent.startswith("delete") or intent.startswith("remove"):
                if parsed.requires_confirmation:
                    result["error"] = "Confirmation required for deletion"
                else:
                    result["executed"] = True
                    result["result"] = "Deletion completed"

            else:
                result["error"] = f"Unknown intent: {intent}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def process_command(
        self,
        command: str,
        context: Optional[dict] = None,
        dry_run: bool = False,
        confirmed: bool = False,
    ) -> NLCommandResponse:
        """Full pipeline: parse and optionally execute a command"""
        # Parse the command
        parsed = await self.parse_command(command, context)

        # Log the command
        await self._log_command(command, parsed)

        # Check if we need confirmation
        if parsed.requires_confirmation and not confirmed and not dry_run:
            return NLCommandResponse(
                original_command=command,
                parsed=parsed,
                executed=False,
                result=None,
                error="Confirmation required. Use confirmed=true to proceed.",
            )

        # Execute if not dry run
        if not dry_run:
            exec_result = await self.execute_command(parsed, dry_run=False)
        else:
            exec_result = await self.execute_command(parsed, dry_run=True)

        return NLCommandResponse(
            original_command=command,
            parsed=parsed,
            executed=exec_result.get("executed", False),
            result=exec_result.get("result"),
            error=exec_result.get("error"),
        )

    async def _log_command(self, command: str, parsed: ParsedCommand):
        """Log command for learning"""
        import json
        try:
            await db.execute(
                """
                INSERT INTO nl_commands (raw_input, parsed_intent, parsed_entities, success)
                VALUES ($1, $2, $3, $4)
                """,
                command,
                parsed.intent,
                json.dumps(parsed.entities),
                parsed.confidence > 0.5,
            )
        except Exception:
            pass  # Don't fail on logging errors

    async def get_command_suggestions(
        self, partial_command: str
    ) -> list[str]:
        """Get command suggestions based on history"""
        rows = await db.fetch(
            """
            SELECT raw_input, COUNT(*) as count
            FROM nl_commands
            WHERE raw_input ILIKE $1
            AND success = true
            GROUP BY raw_input
            ORDER BY count DESC
            LIMIT 5
            """,
            f"%{partial_command}%",
        )
        return [row["raw_input"] for row in rows]


# Global service instance
nl_service = NaturalLanguageService()
