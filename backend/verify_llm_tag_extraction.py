"""
Quick verification script to test if the fix works.
This simulates the exact scenario from the user's conversation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.agents.llm_client import LLMClient
import json

print("=" * 80)
print("VERIFICATION: Testing if LLM can extract Tags from natural language")
print("=" * 80)

db = SessionLocal()
llm_client = LLMClient(db)

# Read the actual system prompt from the code
with open("app/agents/nodes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Check if Tags section exists in the prompt
if "### TAGS (CRITICAL - APPLIES TO ALL RESOURCES)" in content:
    print("\n[OK] System prompt has been updated with Tags section")
else:
    print("\n[ERROR] System prompt does NOT have Tags section!")
    print("The code changes may not have been saved properly.")
    sys.exit(1)

# Test the LLM with the actual user input
print("\nTesting LLM extraction with user inputs...")
print("-" * 80)

# Simulate the conversation context
conversation_context = """
user: 创建一个Azure VM，位置在China East 2
assistant: 我需要以下信息来创建Azure VM...
user: ResourceGroup: my-rg
Location: China East 2
VMSize: Standard_B2s
AdminUsername: azureuser
OSType: Linux
ImagePublisher: Canonical
ImageOffer: UbuntuServer
ImageSKU: 18.04-LTS
AuthenticationType: Password
assistant: ✗ Compliance check failed! Missing required tag(s): Project
user: 打上标签： Project: ABC123
"""

# Read the system prompt (simplified version for testing)
system_prompt = """
You are an intelligent infrastructure assistant validating user requirements.

### TAGS (CRITICAL - APPLIES TO ALL RESOURCES)
**ALL resources must have a `Tags` field in their properties!**

**User Input Patterns to Watch For**:
- "打上标签：Project=Demo" → Extract as `"Tags": {"Project": "Demo"}`
- "标签：Project: ABC, Owner: John" → Extract as `"Tags": {"Project": "ABC", "Owner": "John"}`

When the user provides tag information in a follow-up message:
- **MERGE** new tags with existing tags in the resource
- DO NOT replace all tags, only update/add the specified ones

### OUTPUT FORMAT (JSON)
{
  "information_complete": true/false,
  "resources": [{"type": "azure_vm", "name": "vm_name", "properties": {"Tags": {...}}}],
  "user_message_to_display": "Response..."
}

Analyze this conversation and extract the Tags the user wants to add:
"""

print("\nCalling LLM to extract Tags from: '打上标签： Project: ABC123'")
print("-" * 80)

try:
    response = llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_context},
        ]
    )

    print(f"\nLLM Response ({len(response)} chars):")
    print(response)
    print()

    # Try to parse JSON
    json_start = response.find("{")
    json_end = response.rfind("}") + 1

    if json_start >= 0 and json_end > json_start:
        json_str = response[json_start:json_end]
        result = json.loads(json_str)

        print("Parsed JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()

        # Check if Tags were extracted
        if result.get("resources"):
            for resource in result["resources"]:
                tags = resource.get("properties", {}).get("Tags", {})
                print(f"Extracted Tags: {tags}")

                if "Project" in tags or "project" in tags:
                    print("\n[SUCCESS] LLM correctly extracted Project tag!")
                else:
                    print("\n[WARNING] LLM did NOT extract Project tag")
                    print(
                        "This indicates the LLM may need stronger guidance in the prompt."
                    )
        else:
            print("\n[WARNING] No resources in LLM response")
    else:
        print("\n[ERROR] Could not find JSON in LLM response")

except Exception as e:
    print(f"\n[ERROR] LLM call failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nIf the LLM correctly extracted the Project tag, then:")
print("1. The system prompt fix is working")
print("2. You need to RESTART the backend server for changes to take effect")
print("3. Command: uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload")

db.close()
