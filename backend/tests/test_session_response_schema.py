"""Regression tests for SessionResponse schema compatibility."""

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import SessionResponse


def test_session_response_allows_nested_conversation_history_values():
    """Session history entries can include nested structures such as code blocks."""
    payload = {
        "session_id": "session-1",
        "created_at": datetime.now(timezone.utc),
        "conversation_history": [
            {"role": "user", "content": "generate terraform"},
            {
                "role": "assistant",
                "content": "done",
                "code_blocks": [
                    {
                        "filename": "main.tf",
                        "content": 'resource "aws_s3_bucket" "b" {}',
                        "language": "hcl",
                    }
                ],
            },
        ],
    }

    response = SessionResponse.model_validate(payload)

    assert response.session_id == "session-1"
    assert response.conversation_history is not None
    assert isinstance(response.conversation_history[1]["code_blocks"], list)
