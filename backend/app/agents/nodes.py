"""Agent nodes for LangGraph workflow."""

import json
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.llm_client import LLMClient
from app.agents.progress import ProgressTracker, AgentType
from app.services.excel_parser import ExcelParserService
from app.models import SecurityPolicy
from app.core.database import SessionLocal


class AgentNodes:
    """Collection of agent nodes for the workflow."""

    def __init__(self, db: Session):
        """Initialize nodes with database session."""
        self.db = db
        self.llm_client = LLMClient(db)
        self.excel_parser = ExcelParserService()

    def input_parser(self, state: AgentState) -> AgentState:
        """
        Parse input (Excel or text) to identify resources.
        """
        session_id = state.get("session_id", "")
        ProgressTracker.agent_started(session_id, AgentType.INPUT_PARSER)

        print("\n" + "=" * 80)
        print("[AGENT: InputParser] STARTED")
        print(f"[AGENT: InputParser] Session ID: {state.get('session_id')}")
        print(f"[AGENT: InputParser] Workflow State: {state.get('workflow_state')}")
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        print(f"[AGENT: InputParser] Total messages in state: {len(messages)}")

        # Check if resources are already provided (from Excel upload)
        # IMPORTANT: Only skip parsing if resources came from Excel, not from previous NL conversation!
        # We identify Excel resources by checking specific indicators
        is_excel_upload = (
            state.get("excel_data") is not None
            or state.get("input_type") == "excel"
            or (
                state.get("resources") and len(state.get("messages", [])) <= 1
            )  # First message with resources
        )

        if (
            state.get("resources")
            and len(state.get("resources", [])) > 0
            and is_excel_upload
        ):
            print(
                f"[AGENT: InputParser] Resources already in state: {len(state['resources'])} resources"
            )
            print(
                "[AGENT: InputParser] Skipping parsing, resources already provided from Excel upload"
            )

            # Ensure all resources have proper structure
            for r in state["resources"]:
                # Normalize resource_type if not present
                if "resource_type" not in r and "type" in r:
                    r["resource_type"] = r["type"]
                # Ensure cloud_platform is set
                if "cloud_platform" not in r:
                    rtype = r.get("resource_type", "").lower()
                    if rtype.startswith("aws") or "aws" in rtype:
                        r["cloud_platform"] = "aws"
                    elif rtype.startswith("azure") or "azure" in rtype:
                        r["cloud_platform"] = "azure"

            # Mark information as complete (Excel has all details)
            state["information_complete"] = True
            state["workflow_state"] = "checking_compliance"

            # Add a confirmation message
            resource_summary = (
                f"Received {len(state['resources'])} resources from Excel upload."
            )
            state["messages"].append({"role": "assistant", "content": resource_summary})

            print(
                f"[AGENT: InputParser] Set information_complete=True, transitioning to checking_compliance"
            )
            print("[AGENT: InputParser] FINISHED")
            print("=" * 80 + "\n")
            ProgressTracker.agent_completed(session_id, AgentType.INPUT_PARSER)
            return state

        # Check if Excel data is present (raw bytes)
        if state.get("excel_data"):
            print("[AGENT: InputParser] Excel data detected, skipping text parsing")
            # ... Excel logic ...
            ProgressTracker.agent_completed(session_id, AgentType.INPUT_PARSER)
            return state

        # Text input processing
        print(
            f"[AGENT: InputParser] Processing user input: {last_message['content'][:100]}..."
        )
        user_input = last_message["content"] if last_message else ""
        print(f"[AGENT: InputParser] Full user input length: {len(user_input)} chars")

        # Use LLM to extract resources or understand intent
        system_prompt = """
        You are an Infrastructure as Code (IaC) assistant. 
        Analyze the user's request and extract cloud resources (AWS or Azure).
        
        If resources are identified, output them in this EXACT JSON structure:
        {
          "resources": [
            {
              "type": "aws_ec2" | "aws_s3" | "azure_vm" | "azure_storage" | ...,
              "name": "resource_name",
              "properties": {
                "Region": "us-east-1",
                "ResourceGroup": "my-rg",
                "ResourceGroupExists": "y",  // IMPORTANT: Set to "y" if user says the resource group already exists
                "VNet": "my-vnet",
                "VNetExists": "y",  // IMPORTANT: Set to "y" if user says the VNet already exists
                "Subnet": "my-subnet",
                "SubnetExists": "y",  // IMPORTANT: Set to "y" if user says the subnet already exists
                "NSG": "my-nsg",
                "NSGExists": "y",  // IMPORTANT: Set to "y" if user says the NSG already exists
                "IngressRules": [
                  {"to_port": 3389, "cidr_blocks": ["0.0.0.0/0"]}
                ],
                ... other properties
              }
            }
          ]
        }
        
        ### IMPORTANT: Existing Resource Detection
        When the user mentions that a resource ALREADY EXISTS (using phrases like):
        - "资源组已存在", "已有的资源组", "existing resource group", "resource group exists"
        - "VNet已存在", "使用现有VNet", "existing VNet"
        - "子网已存在", "existing subnet"
        - "不需要新建", "don't create new"
        
        You MUST set the corresponding "*Exists" flag to "y":
        - ResourceGroupExists: "y" - if resource group already exists
        - VNetExists: "y" - if VNet already exists
        - SubnetExists: "y" - if subnet already exists
        - NSGExists: "y" - if NSG already exists
        
        Default value for all *Exists flags is "n" (will create new resources).
        
        Important: For Security Groups, flatten rules into 'IngressRules' list in properties.
        Format rules as: {"to_port": <int>, "cidr_blocks": ["<ip>/<mask>"]}
        
        If more information is needed, ask clarifying questions.
        """

        print("[AGENT: InputParser] Calling LLM to parse user input...")
        response = self.llm_client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]
        )

        print(f"[AGENT: InputParser] LLM response received ({len(response)} chars)")
        print(f"[AGENT: InputParser] LLM response preview: {response[:200]}...")

        # Try to parse JSON from response if resources are identified
        import json

        try:
            # Extract JSON from response (LLM might wrap it in markdown)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                if result.get("resources"):
                    print(
                        f"[AGENT: InputParser] Extracted {len(result['resources'])} resources"
                    )
                    print(
                        f"[AGENT: InputParser] Resources: {json.dumps(result['resources'], indent=2)}"
                    )
                    state["resources"] = result["resources"]

                    # Helper to normalize types
                    def normalize_type(resource_type):
                        if not resource_type:
                            return ""
                        rt = resource_type.lower().replace(" ", "_")
                        type_map = {
                            # AWS resources
                            "ec2": "aws_ec2",
                            "aws_ec2": "aws_ec2",
                            "s3": "aws_s3",
                            "aws_s3": "aws_s3",
                            "vpc": "aws_vpc",
                            "aws_vpc": "aws_vpc",
                            "rds": "aws_rds",
                            "aws_rds": "aws_rds",
                            "subnet": "aws_subnet",
                            "aws_subnet": "aws_subnet",
                            "security_group": "aws_security_group",
                            "aws_security_group": "aws_security_group",
                            "securitygroup": "aws_security_group",
                            # Azure resources
                            "vm": "azure_vm",
                            "azure_vm": "azure_vm",
                            "vnet": "azure_vnet",
                            "azure_vnet": "azure_vnet",
                            "virtual_network": "azure_vnet",
                            "nsg": "azure_nsg",
                            "azure_nsg": "azure_nsg",
                            "network_security_group": "azure_nsg",
                            "storage": "azure_storage",
                            "azure_storage": "azure_storage",
                            "storage_account": "azure_storage",
                            "sql": "azure_sql",
                            "azure_sql": "azure_sql",
                            "resource_group": "azure_resource_group",
                            "azure_resource_group": "azure_resource_group",
                            "resourcegroup": "azure_resource_group",
                        }
                        return type_map.get(rt, rt)

                    # Ensure cloud_platform is set and type is normalized
                    for r in state["resources"]:
                        # Normalize type
                        r["type"] = normalize_type(r.get("type"))
                        r["resource_type"] = r["type"]

                        rtype = r.get("type", "").lower()
                        if rtype.startswith("aws"):
                            r["cloud_platform"] = "aws"
                        elif rtype.startswith("azure"):
                            r["cloud_platform"] = "azure"

                    state["workflow_state"] = "information_collection"
                    print(
                        f"[AGENT: InputParser] Successfully extracted resources, transitioning to information_collection"
                    )
                    print("[AGENT: InputParser] FINISHED")
                    print("=" * 80 + "\n")
                    ProgressTracker.agent_completed(session_id, AgentType.INPUT_PARSER)
                    return state
        except Exception as e:
            print(f"[AGENT: InputParser] ERROR - JSON parsing failed: {e}")
            import traceback

            traceback.print_exc()

        state["messages"].append({"role": "assistant", "content": response})

        # Simple heuristic: if LLM asks questions, we need more info
        if "?" in response and "resources" not in response:
            state["workflow_state"] = "information_collection"
            print(
                "[AGENT: InputParser] LLM is asking questions, setting state to information_collection"
            )
        else:
            state["workflow_state"] = "information_collection"
            print("[AGENT: InputParser] Setting state to information_collection")

        print("[AGENT: InputParser] FINISHED")
        print("=" * 80 + "\n")
        ProgressTracker.agent_completed(session_id, AgentType.INPUT_PARSER)
        return state

    def information_collector(self, state: AgentState) -> AgentState:
        session_id = state.get("session_id", "")
        ProgressTracker.agent_started(session_id, AgentType.INFORMATION_COLLECTOR)

        print("\n" + "=" * 80)
        print("[AGENT: InformationCollector] STARTED")
        print(f"[AGENT: InformationCollector] Session ID: {state.get('session_id')}")
        print(
            f"[AGENT: InformationCollector] Workflow State: {state.get('workflow_state')}"
        )
        print(
            f"[AGENT: InformationCollector] Current resources: {len(state.get('resources', []))}"
        )
        print(
            f"[AGENT: InformationCollector] Information complete: {state.get('information_complete', False)}"
        )

        # If information is already complete (from Excel), skip
        if state.get("information_complete"):
            print(
                "[AGENT: InformationCollector] Information already complete, transitioning to compliance checking"
            )
            state["workflow_state"] = "checking_compliance"
            print("[AGENT: InformationCollector] FINISHED")
            print("=" * 80 + "\n")
            ProgressTracker.agent_completed(session_id, AgentType.INFORMATION_COLLECTOR)
            return state

        # For text-based input, use LLM to determine if info is complete
        system_prompt = """You are an intelligent infrastructure assistant validating user requirements.

Your goal is to ensure we have all necessary details to generate Terraform code.

### RESOURCE REQUIREMENTS
For each resource type, check if the fields are provided.

**AWS EC2**
*   **Required**: Region (e.g., us-east-1), InstanceType (e.g., t2.micro), AMI (Image ID, e.g., ami-0c55b159cbfafe1f0)
*   **Optional**: VPC_ID (default used if missing), Subnet_ID (default used if missing), KeyPairName (recommended for SSH access), IAMRole

**AWS VPC**
*   **Required**: Region, CIDR_Block (e.g., 10.0.0.0/16)
*   **Optional**: Name, EnableDnsHostnames

**AWS S3**
*   **Required**: Region, BucketName (must be globally unique)
*   **Optional**: Versioning (Enabled/Disabled), Encryption (AES256/aws:kms)

**Azure VM**
*   **Required**: ResourceGroup, Location, VMSize, AdminUsername, OSType (Linux/Windows)
*   **Required (Image)**: ImagePublisher (e.g. Canonical), ImageOffer (e.g. 0001-com-ubuntu-server-jammy), ImageSKU (e.g. 22_04-lts)
*   **IMPORTANT**: Use the NEW Azure image URN format. Old offers like 'UbuntuServer' are DEPRECATED. Common mappings:
*     - Ubuntu 22.04: Publisher=Canonical, Offer=0001-com-ubuntu-server-jammy, SKU=22_04-lts
*     - Ubuntu 24.04: Publisher=Canonical, Offer=ubuntu-24_04-lts, SKU=server
*     - Windows Server 2022: Publisher=MicrosoftWindowsServer, Offer=WindowsServer, SKU=2022-datacenter-azure-edition
*   **Required (Auth)**: AuthenticationType (Password/SSH), AdminPassword OR SshPublicKey
*   **Optional**: VNet_Name, Subnet_Name

**Azure VNet**
*   **Required**: ResourceGroup, Location, AddressSpace (e.g. ["10.0.0.0/16"])

**Azure Storage Account**
*   **Required**: ResourceGroup, Location, StorageAccountName (3-24 chars, lowercase letters and numbers only)
*   **Optional**: AccountTier (Standard/Premium), AccountReplicationType (LRS/GRS/ZRS/RAGRS)

### EXISTING RESOURCE FLAGS (CRITICAL - ASK USER!)
When creating Azure resources, you MUST ask the user whether the following parent resources already exist:

**For ALL Azure resources:**
- **ResourceGroupExists**: Does the Resource Group already exist? (y/n)
  - If user says "资源组已存在", "existing resource group", "不需要新建资源组" → Set to "y"
  - If not specified, ASK the user: "Resource Group 'xxx' 是已存在的还是需要新建？"

**For Azure VM (when VNet/Subnet/NSG are specified):**
- **VNetExists**: Does the VNet already exist? (y/n)
- **SubnetExists**: Does the Subnet already exist? (y/n)  
- **NSGExists**: Does the NSG already exist? (y/n)

**IMPORTANT**: 
- Default value for all *Exists flags is "n" (will create new)
- If user provides a resource name but doesn't say it exists, ASK them!
- These flags determine whether Terraform will CREATE or REFERENCE existing resources

### TAGS (CRITICAL - APPLIES TO ALL RESOURCES)
**ALL resources must have a `Tags` field in their properties!**

*   **Format**: `"Tags": {"key1": "value1", "key2": "value2"}`
*   **Common Tags**: Project, Environment, Owner, CostCenter, Application, etc.
*   **User Input Patterns to Watch For**:
    - "打上标签：Project=Demo" → Extract as `"Tags": {"Project": "Demo"}`
    - "tag it with Environment: Production" → Extract as `"Tags": {"Environment": "Production"}`
    - "标签：Project: ABC, Owner: John" → Extract as `"Tags": {"Project": "ABC", "Owner": "John"}`
    - "add tags Project=X and Environment=Y" → Extract as `"Tags": {"Project": "X", "Environment": "Y"}`

**IMPORTANT**: When the user provides tag information in a follow-up message:
- **MERGE** new tags with existing tags in the resource
- DO NOT replace all tags, only update/add the specified ones
- Example: If resource has `{"Application": "Web"}` and user says "Project=Demo", result should be `{"Application": "Web", "Project": "Demo"}`

### INSTRUCTIONS
Review the conversation history.
1. Detect the language of the user's last input (Chinese or English).
2. Determine if "Required" fields are missing.
3. **Check if *Exists flags are specified** - if user mentions a ResourceGroup/VNet/Subnet but doesn't say if it exists, ASK!
4. Construct a friendly response in the **SAME LANGUAGE** as the user.

### OUTPUT FORMAT (JSON)
{
  "information_complete": true/false,
  "missing_fields": ["list", "of", "missing", "fields"],
  "resources": [{
    "type": "azure_storage", 
    "name": "mystorageaccount", 
    "properties": {
      "ResourceGroup": "rg-myproject",
      "ResourceGroupExists": "y",  // MUST include this!
      "Location": "eastus",
      "StorageAccountName": "mystorageaccount",
      "Tags": {"Project": "Demo"}
    }
  }],
  "user_message_to_display": "Natural language response..."
}

**CRITICAL**: ALWAYS include the "resources" field with ALL current resource information!
- If user provides Tags (like "标签：Project=X"), extract them and add to the resource properties
- If user provides other fields, merge them into existing properties
- The "resources" field should contain the COMPLETE and UP-TO-DATE resource definition
- Even if "information_complete" is false, you MUST output updated resources with any new information provided

**Example**: If existing resource has {Location: "China East"} and user says "标签：Project=ABC", output:
{
  "information_complete": false,  // still missing required fields
  "missing_fields": ["VMSize", "OSType", ...],
  "resources": [{
    "type": "azure_vm",
    "name": "vm-1",
    "properties": {
      "Location": "China East",  // keep existing
      "Tags": {"Project": "ABC"}  // add new Tags
    }
  }],
  "user_message_to_display": "已添加标签 Project=ABC。还需要以下信息..."
}

### GUIDE FOR 'user_message_to_display'
*   **Language**: Strictly follow user's language (Chinese -> Chinese, English -> English).
*   **Format**: Use Markdown.
*   **Content**:
    1. Acknowledge the request.
    2. List missing **Required** fields clearly.
    3. **ASK about existing resources** if ResourceGroup/VNet/Subnet is provided but *Exists flag is not set.
    4. List **Optional** fields separately.
    5. Provide a **Copy-Paste Template** for the user to fill in.
    6. Give specific examples for complex fields (like AMI IDs or Azure Image details).

**Example Response (Chinese) for Azure Storage with existing RG question:**
"我注意到您要创建 Azure Storage Account，并指定了 Resource Group: `rg-myproject-prod`。

**请确认以下问题：**
* **Resource Group 是否已存在？** 如果已存在请回复"是"或"已存在"，如果需要新建请回复"否"或"新建"。

**还需要以下信息：**
* **StorageAccountName**: 存储账户名称（3-24个字符，仅小写字母和数字）

**可选配置：**
* **AccountTier**: Standard 或 Premium（默认 Standard）
* **Tags**: 标签，格式如 Project=Demo, Environment=Prod

您可以这样回复：
```
资源组已存在
StorageAccountName: mystorageaccount
Tags: Project=Demo, Environment=Production
```"
"""

        # Get recent conversation context
        recent_messages = state["messages"][-6:]  # Last 3 exchanges
        context_str = "\n".join(
            [f"{m['role']}: {m['content']}" for m in recent_messages]
        )
        print(
            f"[AGENT: InformationCollector] Using {len(recent_messages)} recent messages for context"
        )

        messages = self.llm_client.generate_prompt(
            system_prompt,
            f"Validate this conversation and generate response:\n{context_str}",
        )

        print("[AGENT: InformationCollector] Calling LLM to validate information...")
        response = self.llm_client.chat(messages)
        print(
            f"[AGENT: InformationCollector] LLM response received ({len(response)} chars)"
        )
        print(
            f"[AGENT: InformationCollector] LLM response (first 500 chars):\n{response[:500]}"
        )

        # Try to parse JSON response
        try:
            # Extract JSON from response (LLM might wrap it in markdown)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                # Merge new resources into existing ones instead of overwriting
                existing_resources = state.get("resources", [])
                new_resources = result.get("resources", [])

                print(
                    f"[AGENT: InformationCollector] Existing resources: {len(existing_resources)}"
                )
                print(
                    f"[AGENT: InformationCollector] New resources from LLM: {len(new_resources)}"
                )

                # Smart merge strategy: match by normalized type
                # If existing resources is empty, just take the new ones
                if not existing_resources and new_resources:
                    state["resources"] = new_resources
                    print(
                        f"[AGENT: InformationCollector] No existing resources, using new ones"
                    )
                elif new_resources:
                    # Normalize type names for comparison
                    def normalize_type(resource_type):
                        """Normalize resource type to a common format."""
                        if not resource_type:
                            return ""
                        rt = resource_type.lower().replace(" ", "_")
                        # Map variations to standard types
                        type_map = {
                            # AWS resources
                            "ec2": "aws_ec2",
                            "aws_ec2": "aws_ec2",
                            "s3": "aws_s3",
                            "aws_s3": "aws_s3",
                            "vpc": "aws_vpc",
                            "aws_vpc": "aws_vpc",
                            "rds": "aws_rds",
                            "aws_rds": "aws_rds",
                            "subnet": "aws_subnet",
                            "aws_subnet": "aws_subnet",
                            "security_group": "aws_security_group",
                            "aws_security_group": "aws_security_group",
                            "securitygroup": "aws_security_group",
                            # Azure resources
                            "vm": "azure_vm",
                            "azure_vm": "azure_vm",
                            "vnet": "azure_vnet",
                            "azure_vnet": "azure_vnet",
                            "virtual_network": "azure_vnet",
                            "nsg": "azure_nsg",
                            "azure_nsg": "azure_nsg",
                            "network_security_group": "azure_nsg",
                            "storage": "azure_storage",
                            "azure_storage": "azure_storage",
                            "storage_account": "azure_storage",
                            "sql": "azure_sql",
                            "azure_sql": "azure_sql",
                            "resource_group": "azure_resource_group",
                            "azure_resource_group": "azure_resource_group",
                            "resourcegroup": "azure_resource_group",
                        }
                        return type_map.get(rt, rt)

                    # Create a map of existing resources by normalized type
                    res_map = {}
                    for idx, r in enumerate(existing_resources):
                        r_type = r.get("type") or r.get("resource_type")
                        normalized = normalize_type(r_type)
                        res_map[normalized] = idx

                    print(
                        f"[AGENT: InformationCollector] Existing resource types: {list(res_map.keys())}"
                    )

                    for nr in new_resources:
                        nr_type = nr.get("type") or nr.get("resource_type")
                        normalized_new = normalize_type(nr_type)

                        print(
                            f"[AGENT: InformationCollector] Processing new resource type: {nr_type} (normalized: {normalized_new})"
                        )

                        if normalized_new in res_map:
                            # Update existing resource
                            idx = res_map[normalized_new]
                            existing_res = existing_resources[idx]

                            print(
                                f"[AGENT: InformationCollector]   Merging with existing resource at index {idx}"
                            )

                            # Merge properties (new properties override old ones)
                            # BUT: Tags should be merged, not replaced!
                            current_props = existing_res.get("properties", {})
                            new_props = nr.get("properties", {})

                            # Special handling for Tags field - merge tags instead of replacing
                            if "Tags" in new_props:
                                current_tags = current_props.get("Tags", {})
                                new_tags = new_props.get("Tags", {})

                                print(
                                    f"[AGENT: InformationCollector]   Current Tags: {current_tags}"
                                )
                                print(
                                    f"[AGENT: InformationCollector]   New Tags from LLM: {new_tags}"
                                )

                                # Ensure both are dicts
                                if not isinstance(current_tags, dict):
                                    current_tags = {}
                                if not isinstance(new_tags, dict):
                                    new_tags = {}

                                # Merge: new tags override/add to existing tags
                                merged_tags = {**current_tags, **new_tags}
                                new_props["Tags"] = merged_tags
                                print(
                                    f"[AGENT: InformationCollector]   Merged Tags: {merged_tags}"
                                )

                            # Update all properties
                            current_props.update(new_props)
                            existing_res["properties"] = current_props

                            # Update other fields if present
                            if nr.get("name"):
                                existing_res["name"] = nr.get("name")
                            if nr.get("resource_name"):
                                existing_res["resource_name"] = nr.get("resource_name")
                            if nr.get("cloud_platform"):
                                existing_res["cloud_platform"] = nr.get(
                                    "cloud_platform"
                                )

                            # Ensure consistent type field (use the normalized version)
                            existing_res["type"] = normalized_new
                            existing_res["resource_type"] = normalized_new
                        else:
                            # Add new resource
                            print(
                                f"[AGENT: InformationCollector]   Adding as new resource"
                            )
                            # Normalize the type before adding
                            nr["type"] = normalized_new
                            nr["resource_type"] = normalized_new
                            existing_resources.append(nr)

                    # Update state
                    state["resources"] = existing_resources
                    print(
                        f"[AGENT: InformationCollector] Final resource count: {len(state['resources'])}"
                    )

                # Normalize and Log
                for r in state["resources"]:
                    # Fix keys to be TitleCase for consistency if needed, or normalize to snake_case
                    # Terraform generator expects specific keys.
                    # Let's ensure cloud_platform is set
                    if "cloud_platform" not in r:
                        if "aws" in r.get("type", "").lower():
                            r["cloud_platform"] = "aws"
                        if "azure" in r.get("type", "").lower():
                            r["cloud_platform"] = "azure"

                print(
                    f"[AGENT: InformationCollector] Updated resources count: {len(state['resources'])}"
                )
                print(
                    f"[AGENT: InformationCollector] Resources structure:\n{json.dumps(state['resources'], indent=2)}"
                )

                state["information_complete"] = result.get(
                    "information_complete", False
                )
                state["missing_fields"] = result.get("missing_fields", [])

                if state.get("resources"):
                    # Helper to normalize types (redefined for scope)
                    def normalize_type_final(resource_type):
                        if not resource_type:
                            return ""
                        rt = resource_type.lower().replace(" ", "_")
                        type_map = {
                            # AWS resources
                            "ec2": "aws_ec2",
                            "aws_ec2": "aws_ec2",
                            "s3": "aws_s3",
                            "aws_s3": "aws_s3",
                            "vpc": "aws_vpc",
                            "aws_vpc": "aws_vpc",
                            "rds": "aws_rds",
                            "aws_rds": "aws_rds",
                            "subnet": "aws_subnet",
                            "aws_subnet": "aws_subnet",
                            "security_group": "aws_security_group",
                            "aws_security_group": "aws_security_group",
                            "securitygroup": "aws_security_group",
                            # Azure resources
                            "vm": "azure_vm",
                            "azure_vm": "azure_vm",
                            "vnet": "azure_vnet",
                            "azure_vnet": "azure_vnet",
                            "virtual_network": "azure_vnet",
                            "nsg": "azure_nsg",
                            "azure_nsg": "azure_nsg",
                            "network_security_group": "azure_nsg",
                            "storage": "azure_storage",
                            "azure_storage": "azure_storage",
                            "storage_account": "azure_storage",
                            "sql": "azure_sql",
                            "azure_sql": "azure_sql",
                            "resource_group": "azure_resource_group",
                            "azure_resource_group": "azure_resource_group",
                            "resourcegroup": "azure_resource_group",
                        }
                        return type_map.get(rt, rt)

                    # Normalize resource structure for Terraform generator
                    normalized_resources = []
                    for r in state["resources"]:
                        # Check if it has 'type' instead of 'resource_type' (common LLM variance)
                        if "type" in r:
                            r["type"] = normalize_type_final(r["type"])

                        if "type" in r and "resource_type" not in r:
                            r["resource_type"] = r["type"]
                        elif "resource_type" in r:
                            r["resource_type"] = normalize_type_final(
                                r["resource_type"]
                            )

                        if "name" in r and "resource_name" not in r:
                            r["resource_name"] = r["name"]
                        # Ensure properties exists
                        if "properties" not in r:
                            r["properties"] = {}
                        # Ensure cloud_platform is set based on normalized type
                        if "cloud_platform" not in r:
                            rtype = r.get("type", r.get("resource_type", "")).lower()
                            if rtype.startswith("aws"):
                                r["cloud_platform"] = "aws"
                            elif rtype.startswith("azure"):
                                r["cloud_platform"] = "azure"
                        normalized_resources.append(r)
                    state["resources"] = normalized_resources

                if state["information_complete"]:
                    state["workflow_state"] = "checking_compliance"
                    print(
                        "[AGENT: InformationCollector] Information is complete, transitioning to checking_compliance"
                    )
                    # Allow LLM to generate the success message too if present, or use default
                    if result.get("user_message_to_display"):
                        ai_response = result.get("user_message_to_display")
                    else:
                        ai_response = "Great! I have all the information needed. Let me check compliance policies..."
                else:
                    state["workflow_state"] = "waiting_for_user"
                    print(
                        f"[AGENT: InformationCollector] Missing fields: {state.get('missing_fields', [])}"
                    )
                    print("[AGENT: InformationCollector] Waiting for more user input")
                    # Use the enhanced message from LLM
                    if result.get("user_message_to_display"):
                        ai_response = result.get("user_message_to_display")
                    else:
                        ai_response = f"I need more information: {', '.join(state['missing_fields'])}"

            else:
                # Couldn't parse JSON, continue conversation
                print(
                    "[AGENT: InformationCollector] Could not parse JSON from LLM response"
                )
                state["workflow_state"] = "waiting_for_user"
                ai_response = response

        except json.JSONDecodeError as e:
            # JSON parsing failed, treat as continued conversation
            print(f"[AGENT: InformationCollector] JSON decode error: {e}")
            state["workflow_state"] = "waiting_for_user"
            ai_response = response

        state["ai_response"] = ai_response
        state["messages"].append({"role": "assistant", "content": ai_response})
        print(f"[AGENT: InformationCollector] AI Response: {ai_response[:100]}...")
        print("[AGENT: InformationCollector] FINISHED")
        print("=" * 80 + "\n")

        ProgressTracker.agent_completed(session_id, AgentType.INFORMATION_COLLECTOR)
        return state

    def compliance_checker(self, state: AgentState) -> AgentState:
        """
        Check resources against security compliance policies.

        Args:
            state: Current agent state

        Returns:
            Updated state
        """
        session_id = state.get("session_id", "")
        ProgressTracker.agent_started(session_id, AgentType.COMPLIANCE_CHECKER)

        print("\n" + "=" * 80)
        print("[AGENT: ComplianceChecker] STARTED")
        print(f"[AGENT: ComplianceChecker] Session ID: {state.get('session_id')}")
        print(
            f"[AGENT: ComplianceChecker] Resources to check: {len(state.get('resources', []))}"
        )
        state["workflow_state"] = "compliance_checking"

        # Get enabled policies from database
        policies = (
            self.db.query(SecurityPolicy).filter(SecurityPolicy.enabled == True).all()
        )

        print(f"[AGENT: ComplianceChecker] Found {len(policies)} enabled policies")

        if not policies:
            # No policies configured, skip compliance check
            print(
                "[AGENT: ComplianceChecker] No policies configured, skipping compliance check"
            )
            state["compliance_checked"] = True
            state["compliance_passed"] = True
            state["workflow_state"] = "generating_code"
            state["ai_response"] = (
                "No compliance policies configured. Proceeding to code generation..."
            )
            state["messages"].append(
                {"role": "assistant", "content": state["ai_response"]}
            )
            print("[AGENT: ComplianceChecker] FINISHED")
            print("=" * 80 + "\n")
            return state

        violations = []
        warnings = []

        print(
            f"[AGENT: ComplianceChecker] Checking {len(policies)} policies against resources..."
        )
        # Iterate through all enabled policies
        for policy in policies:
            print(f"[AGENT: ComplianceChecker] Checking policy: {policy.name}")
            rule_logic = policy.executable_rule or {}

            # 1. Block Ports Logic
            if "block_ports" in rule_logic:
                blocked_ports = rule_logic["block_ports"]
                print(
                    f"[AGENT: ComplianceChecker]   - Block ports policy: {blocked_ports}"
                )

                for resource in state.get("resources", []):
                    resource_props = resource.get("properties", {})

                    # Check AWS Security Groups - IngressRules
                    if "IngressRules" in resource_props:
                        ingress_rules = resource_props.get("IngressRules", [])
                        print(
                            f"[AGENT: ComplianceChecker]   - Checking {len(ingress_rules)} AWS ingress rules for resource {resource.get('resource_name', 'unknown')}"
                        )
                        for rule in ingress_rules:
                            if isinstance(rule, dict):
                                cidr_blocks = rule.get("cidr_blocks", [])
                                port = rule.get("to_port")

                                # Check if port is in blocked list and open to world
                                if port in blocked_ports and "0.0.0.0/0" in cidr_blocks:
                                    violation_msg = f"Port {port} is blocked by policy but open to 0.0.0.0/0"
                                    print(
                                        f"[AGENT: ComplianceChecker]   - VIOLATION: {violation_msg}"
                                    )
                                    violations.append(
                                        {
                                            "policy": policy.name,
                                            "description": policy.description,
                                            "resource": resource.get(
                                                "resource_name", "unknown"
                                            ),
                                            "issue": violation_msg,
                                        }
                                    )

                    # Check Azure NSG - SecurityRules
                    if "SecurityRules" in resource_props:
                        security_rules = resource_props.get("SecurityRules", [])
                        print(
                            f"[AGENT: ComplianceChecker]   - Checking {len(security_rules)} Azure security rules for resource {resource.get('resource_name', 'unknown')}"
                        )
                        for rule in security_rules:
                            if isinstance(rule, dict):
                                # Azure NSG rule structure:
                                # {"name": "...", "direction": "Inbound/Outbound", "access": "Allow/Deny",
                                #  "protocol": "Tcp/Udp/*", "destination_port_range": "443" or "80-443",
                                #  "source_address_prefix": "*" or "0.0.0.0/0" or specific IP}

                                direction = rule.get("direction", "").lower()
                                access = rule.get("access", "").lower()
                                source_prefix = rule.get("source_address_prefix", "")
                                dest_port_range = rule.get("destination_port_range", "")

                                # Only check inbound allow rules
                                if direction == "inbound" and access == "allow":
                                    # Check if source is open to the internet
                                    if source_prefix in ["*", "0.0.0.0/0", "Internet"]:
                                        # Parse port range (can be single port like "443" or range like "80-443")
                                        ports_to_check = []
                                        if dest_port_range and dest_port_range != "*":
                                            if "-" in str(dest_port_range):
                                                # Port range
                                                try:
                                                    start, end = dest_port_range.split(
                                                        "-"
                                                    )
                                                    ports_to_check = list(
                                                        range(int(start), int(end) + 1)
                                                    )
                                                except (ValueError, AttributeError):
                                                    ports_to_check = []
                                            else:
                                                # Single port
                                                try:
                                                    ports_to_check = [
                                                        int(dest_port_range)
                                                    ]
                                                except (ValueError, TypeError):
                                                    ports_to_check = []

                                        # Check if any port in the range is blocked
                                        for port in ports_to_check:
                                            if port in blocked_ports:
                                                rule_name = rule.get("name", "unknown")
                                                violation_msg = f"Port {port} (rule: {rule_name}) is blocked by policy but open to internet (source: {source_prefix})"
                                                print(
                                                    f"[AGENT: ComplianceChecker]   - VIOLATION: {violation_msg}"
                                                )
                                                violations.append(
                                                    {
                                                        "policy": policy.name,
                                                        "description": policy.description,
                                                        "resource": resource.get(
                                                            "resource_name", "unknown"
                                                        ),
                                                        "issue": violation_msg,
                                                    }
                                                )
                                                break  # Only report once per rule

            # 2. Required Tags Logic
            if "required_tags" in rule_logic:
                required_tags = rule_logic["required_tags"]
                print(
                    f"[AGENT: ComplianceChecker]   - Required tags policy: {required_tags}"
                )

                # Azure resources that technically cannot have tags
                # (checking these would be incorrect - they fail at terraform apply)
                azure_no_tags_resources = {
                    "subnet",
                    "azurerm_subnet",
                    "azurerm_subnet_network_security_group_association",
                    "azurerm_subnet_route_table_association",
                    "azurerm_network_interface_security_group_association",
                    "azurerm_virtual_network_peering",
                }

                for resource in state.get("resources", []):
                    resource_name = resource.get("resource_name", "unknown")
                    resource_type = resource.get(
                        "resource_type", resource.get("type", "")
                    ).lower()
                    resource_props = resource.get("properties", {})
                    resource_tags = resource_props.get("Tags", {})

                    # Skip resources that cannot have tags
                    if resource_type in azure_no_tags_resources:
                        print(
                            f"[AGENT: ComplianceChecker]   - Skipping {resource_name} ({resource_type}) - does not support tags"
                        )
                        continue

                    print(
                        f"[AGENT: ComplianceChecker]   - Checking tags for resource {resource_name}"
                    )
                    print(
                        f"[AGENT: ComplianceChecker]   - Resource tags: {resource_tags}"
                    )

                    # Check if resource_tags is a dict (expected format)
                    if not isinstance(resource_tags, dict):
                        print(
                            f"[AGENT: ComplianceChecker]   - WARNING: Tags field is not a dict for {resource_name}"
                        )
                        resource_tags = {}

                    # Check each required tag
                    missing_tags = []
                    for required_tag in required_tags:
                        # Case-insensitive check (convert both to lowercase)
                        tag_keys_lower = {k.lower(): k for k in resource_tags.keys()}
                        if required_tag.lower() not in tag_keys_lower:
                            missing_tags.append(required_tag)

                    if missing_tags:
                        violation_msg = (
                            f"Missing required tag(s): {', '.join(missing_tags)}"
                        )
                        print(
                            f"[AGENT: ComplianceChecker]   - VIOLATION: {violation_msg}"
                        )
                        violations.append(
                            {
                                "policy": policy.name,
                                "description": policy.description,
                                "resource": resource_name,
                                "issue": violation_msg,
                            }
                        )
                    else:
                        print(
                            f"[AGENT: ComplianceChecker]   - PASSED: All required tags present"
                        )

            # 3. Future logic for other rule types (e.g., allowed_regions) can be added here

        state["compliance_checked"] = True
        state["compliance_violations"] = violations
        state["compliance_warnings"] = warnings
        state["compliance_passed"] = len(violations) == 0

        print(f"[AGENT: ComplianceChecker] Compliance check complete")
        print(f"[AGENT: ComplianceChecker] Violations: {len(violations)}")
        print(f"[AGENT: ComplianceChecker] Warnings: {len(warnings)}")

        if state["compliance_passed"]:
            state["workflow_state"] = "generating_code"
            ai_response = f"✓ Compliance check passed! Checked {len(policies)} policies. Proceeding to code generation..."
            print(f"[AGENT: ComplianceChecker] Result: PASSED")
        else:
            state["workflow_state"] = "compliance_failed"
            state["should_continue"] = False
            ai_response = (
                f"✗ Compliance check failed! Found {len(violations)} violations:\n"
            )
            for v in violations:
                ai_response += f"- {v['resource']}: {v['issue']}\n"
                print(f"[AGENT: ComplianceChecker]   - {v['resource']}: {v['issue']}")
            ai_response += "\nPlease fix these issues before proceeding."
            print(f"[AGENT: ComplianceChecker] Result: FAILED")

        state["ai_response"] = ai_response
        state["messages"].append({"role": "assistant", "content": ai_response})

        print("[AGENT: ComplianceChecker] FINISHED")
        print("=" * 80 + "\n")

        ProgressTracker.agent_completed(session_id, AgentType.COMPLIANCE_CHECKER)
        return state

    def code_reviewer(self, state: AgentState) -> AgentState:
        """
        Review generated Terraform code for:
        1. Best practices compliance
        2. Syntax correctness (can apply without errors)
        3. Alignment with user requirements

        If review fails, triggers regeneration with feedback.
        """
        session_id = state.get("session_id", "")
        ProgressTracker.agent_started(session_id, AgentType.CODE_REVIEWER)

        print("\n" + "=" * 80)
        print("[AGENT: CodeReviewer] STARTED")
        print(f"[AGENT: CodeReviewer] Session ID: {state.get('session_id')}")
        state["workflow_state"] = "reviewing_code"

        generated_files = state.get("generated_code") or {}
        resources = state.get("resources") or []
        review_attempt = (state.get("review_attempt") or 0) + 1
        state["review_attempt"] = review_attempt

        print(f"[AGENT: CodeReviewer] Review attempt: {review_attempt}/3")
        print(f"[AGENT: CodeReviewer] Generated files: {len(generated_files)}")
        print(f"[AGENT: CodeReviewer] Resources: {len(resources)}")

        # Log files being reviewed
        if generated_files:
            print("[AGENT: CodeReviewer] Files to review:")
            for idx, (file_name, content) in enumerate(generated_files.items(), 1):
                print(f"  [{idx}] {file_name} ({len(content)} chars)")

        # Log resources being reviewed
        if resources:
            print("[AGENT: CodeReviewer] Resources being reviewed:")
            for idx, resource in enumerate(resources, 1):
                resource_type = resource.get("resource_type", "N/A")
                resource_name = resource.get("name", "N/A")
                print(f"  [{idx}] Type: {resource_type}, Name: {resource_name}")

        # No code to review
        if not generated_files:
            print("[AGENT: CodeReviewer] No generated files to review")
            state["review_passed"] = False
            state["review_feedback"] = "No code was generated to review."
            state["workflow_state"] = "review_failed"
            print("[AGENT: CodeReviewer] FINISHED")
            print("=" * 80 + "\n")
            return state

        # Max attempts reached - accept code as-is
        if review_attempt > 3:
            print("[AGENT: CodeReviewer] Max review attempts reached, accepting code")
            state["review_passed"] = True
            state["review_feedback"] = "Code accepted after maximum review attempts."
            state["workflow_state"] = "completed"
            print("[AGENT: CodeReviewer] FINISHED")
            print("=" * 80 + "\n")
            return state

        # Prepare code for review
        files_content = "\n\n".join(
            [
                f"=== File: {name} ===\n{content}"
                for name, content in generated_files.items()
            ]
        )
        requirements = json.dumps(resources, indent=2)

        # Get previous feedback if this is a retry
        previous_feedback = state.get("review_feedback", "")

        # Build LLM prompt for code review
        system_prompt = """You are an expert Terraform code reviewer. Review the generated Terraform code and evaluate:

1. **Terraform Syntax**: Will the code run `terraform init` and `terraform apply` without errors?
2. **Best Practices**:
   - Proper resource naming conventions
   - Security best practices (no overly permissive rules unless explicitly requested)
   - Proper provider configuration

##############################################################################
# IMPORTANT: DO NOT FLAG HARDCODED VALUES
##############################################################################

- DO NOT report hardcoded values as an issue
- DO NOT suggest replacing actual values with var.xxx variable references
- The Jinja2 templates inject actual values from Excel data on purpose
- These values MUST remain as literals (passwords, usernames, regions, sizes, etc.)
- Only provider-level config like subscription_id should use variables

3. **Requirements Match**: Does the code match ALL user requirements?

##############################################################################
# AZURE TECHNICAL CONSTRAINTS (Provider Limitations)
##############################################################################

The following Azure resources DO NOT support certain parameters:

Resources that DO NOT support `tags`:
- azurerm_subnet
- azurerm_subnet_network_security_group_association
- azurerm_subnet_route_table_association
- azurerm_network_interface_security_group_association
- azurerm_virtual_network_peering

CRITICAL AzureRM Provider v4.x Changes for Network Interface:
- azurerm_network_interface NO LONGER supports `network_security_group_id` parameter (removed in v4.x)
- To associate NSG with NIC, you MUST use separate resource: azurerm_network_interface_security_group_association
- Example v4.x pattern:
  resource "azurerm_network_interface" "example" {
    # ... NO network_security_group_id here ...
  }
  resource "azurerm_network_interface_security_group_association" "example" {
    network_interface_id      = azurerm_network_interface.example.id
    network_security_group_id = azurerm_network_security_group.example.id
  }

Resources that DO NOT support inline `data_disk` blocks:
- azurerm_linux_virtual_machine
- azurerm_windows_virtual_machine
(Data disks must be created as separate azurerm_managed_disk resources)

CRITICAL AzureRM Provider v4.x Changes (DO NOT USE v3.x parameters):

Storage Account (azurerm_storage_account):
- USE `https_traffic_only_enabled` NOT `enable_https_traffic_only` (deprecated in v4.x)
- USE `min_tls_version` NOT `minimum_tls_version` for storage account
- USE `allow_nested_items_to_be_public` NOT `allow_blob_public_access` (deprecated in v4.x)

SQL Database (azurerm_mssql_database):
- TDE (Transparent Data Encryption) is enabled by default, DO NOT create separate `azurerm_mssql_database_transparent_data_encryption` resource (does not exist in v4.x)
- Vulnerability Assessment is configured via `azurerm_mssql_server` or `azurerm_mssql_server_security_alert_policy`, DO NOT create `azurerm_mssql_database_vulnerability_assessment` resource (does not exist in v4.x)

If you see these deprecated parameters or invalid resources in the code, report them as CRITICAL errors.

##############################################################################
# IMPORTANT: DO NOT CHECK FOR TAGS
##############################################################################

- DO NOT check if resources have tags
- DO NOT report "missing tags" as an issue
- DO NOT suggest adding tags to any resource
- Tag requirements are handled by a separate Compliance Policy system

##############################################################################

Respond in this EXACT JSON format:
{
  "passed": true/false,
  "overall_score": 1-10,
  "issues": [
    {
      "severity": "critical" | "warning" | "info",
      "file": "filename.tf",
      "description": "Issue description",
      "suggestion": "How to fix"
    }
  ],
  "summary": "Brief summary of the review"
}

Rules:
- "passed": true only if there are NO critical issues and score >= 7
- Critical issues: syntax errors, missing required resources, security vulnerabilities, unsupported parameters
- Warning issues: suboptimal practices, hardcoded values
- Info issues: style suggestions, optional improvements
"""

        user_prompt = f"""Review the following Terraform code generated for these requirements:

## User Requirements:
{requirements}

## Generated Terraform Code:
{files_content}

"""

        if previous_feedback and review_attempt > 1:
            user_prompt += f"""
## Previous Review Feedback (this is attempt {review_attempt}):
{previous_feedback}

Please verify if the issues from previous review have been addressed.
"""

        print("[AGENT: CodeReviewer] Calling LLM for code review...")
        response = self.llm_client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Lower temperature for more consistent review
        )

        print(f"[AGENT: CodeReviewer] LLM response received ({len(response)} chars)")

        # Parse review response
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                review_result = json.loads(response[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")

            passed = review_result.get("passed", False)
            issues = review_result.get("issues", [])
            summary = review_result.get("summary", "Review completed")
            score = review_result.get("overall_score", 0)

            # Note: Tag-related compliance is handled by ComplianceChecker via Policy module
            # CodeReviewer only checks syntax and Azure technical constraints

            print(f"[AGENT: CodeReviewer] Review passed: {passed}")
            print(f"[AGENT: CodeReviewer] Overall Score: {score}/10")
            print(f"[AGENT: CodeReviewer] Summary: {summary}")
            print(f"[AGENT: CodeReviewer] Total Issues: {len(issues)}")

            state["review_passed"] = passed
            state["review_issues"] = issues
            state["review_feedback"] = summary

            if passed:
                state["workflow_state"] = "completed"

                # Build success message
                ai_response = f"**Code Review Passed** (Score: {score}/10)\n\n"
                ai_response += f"{summary}\n\n"

                if issues:
                    ai_response += "**Minor suggestions (optional):**\n"
                    for issue in issues:
                        if issue.get("severity") in ["warning", "info"]:
                            ai_response += f"- [{issue.get('severity')}] {issue.get('description')}\n"

                ai_response += "\nThe code is ready for download and deployment."
                state["ai_response"] = ai_response
                state["messages"].append({"role": "assistant", "content": ai_response})

                print("[AGENT: CodeReviewer] Code review PASSED")
                # Log all issues details (even for passed reviews, there might be warnings)
                if issues:
                    print("[AGENT: CodeReviewer] Issues details:")
                    for idx, issue in enumerate(issues, 1):
                        print(
                            f"  [{idx}] [{issue.get('severity', 'N/A')}] [{issue.get('file', 'general')}]"
                        )
                        print(f"      Description: {issue.get('description', 'N/A')}")
                        print(f"      Suggestion: {issue.get('suggestion', 'N/A')}")
            else:
                state["workflow_state"] = "review_failed"

                # Build feedback for regeneration
                critical_issues = [i for i in issues if i.get("severity") == "critical"]
                warning_issues = [i for i in issues if i.get("severity") == "warning"]
                info_issues = [i for i in issues if i.get("severity") == "info"]

                print(f"[AGENT: CodeReviewer] Critical Issues: {len(critical_issues)}")
                print(f"[AGENT: CodeReviewer] Warning Issues: {len(warning_issues)}")
                print(f"[AGENT: CodeReviewer] Info Issues: {len(info_issues)}")

                # Log detailed issue information
                if issues:
                    print("[AGENT: CodeReviewer] === DETAILED ISSUES ===")
                    for idx, issue in enumerate(issues, 1):
                        severity = issue.get("severity", "N/A")
                        file_name = issue.get("file", "general")
                        description = issue.get("description", "N/A")
                        suggestion = issue.get("suggestion", "N/A")
                        print(f"  Issue #{idx}:")
                        print(f"    Severity: {severity}")
                        print(f"    File: {file_name}")
                        print(f"    Description: {description}")
                        print(f"    Suggestion: {suggestion}")
                        print()

                feedback_for_regeneration = (
                    f"Review failed (Score: {score}/10). Issues found:\n\n"
                )

                if critical_issues:
                    feedback_for_regeneration += "CRITICAL ISSUES (must fix):\n"
                    for issue in critical_issues:
                        feedback_for_regeneration += f"- [{issue.get('file', 'general')}] {issue.get('description')}\n"
                        feedback_for_regeneration += (
                            f"  Fix: {issue.get('suggestion', 'N/A')}\n"
                        )

                if warning_issues:
                    feedback_for_regeneration += "\nWARNINGS (should fix):\n"
                    for issue in warning_issues:
                        feedback_for_regeneration += f"- [{issue.get('file', 'general')}] {issue.get('description')}\n"

                state["review_feedback"] = feedback_for_regeneration

                # Print the complete feedback that will be sent to regeneration
                print(
                    "[AGENT: CodeReviewer] === REGENERATION FEEDBACK (will be sent to LLM) ==="
                )
                print(feedback_for_regeneration)
                print("[AGENT: CodeReviewer] === END OF REGENERATION FEEDBACK ===")

                print(
                    f"[AGENT: CodeReviewer] Code review FAILED - {len(critical_issues)} critical, {len(warning_issues)} warnings"
                )

        except Exception as e:
            print(f"[AGENT: CodeReviewer] ERROR parsing review response: {e}")
            import traceback

            traceback.print_exc()

            # On parse error, assume code is acceptable (don't block user)
            state["review_passed"] = True
            state["review_feedback"] = (
                "Review completed (response parsing issue, code accepted)"
            )
            state["workflow_state"] = "completed"
            state["ai_response"] = "Code generation completed. Ready for download."
            state["messages"].append(
                {"role": "assistant", "content": state["ai_response"]}
            )

        print(f"[AGENT: CodeReviewer] FINISHED - Status: {state['workflow_state']}")
        print("=" * 80 + "\n")

        ProgressTracker.agent_completed(session_id, AgentType.CODE_REVIEWER)
        return state

    def should_regenerate_code(self, state: AgentState) -> str:
        """
        Determine if code should be regenerated based on review results.

        Returns:
            "regenerate" if review failed and attempts remain
            "end" if review passed or max attempts reached
        """
        review_passed = (
            state.get("review_passed")
            if state.get("review_passed") is not None
            else True
        )
        review_attempt = state.get("review_attempt") or 0

        if review_passed:
            print("[ROUTER: CodeReviewer] Review PASSED - ending workflow")
            return "end"

        if review_attempt >= 3:
            print(
                f"[ROUTER: CodeReviewer] Max attempts ({review_attempt}) reached - ending workflow"
            )
            return "end"

        print(
            f"[ROUTER: CodeReviewer] Review FAILED (attempt {review_attempt}/3) - regenerating code"
        )
        return "regenerate"

    def _regenerate_with_llm(
        self,
        state: AgentState,
        existing_code: Dict[str, str],
        review_feedback: str,
    ) -> AgentState:
        """
        Use LLM to fix Terraform code based on review feedback.

        Args:
            state: Current agent state
            existing_code: Existing generated code files
            review_feedback: Feedback from code reviewer

        Returns:
            Updated state with fixed code
        """
        session_id = state.get("session_id", "")
        print("[AGENT: CodeGenerator] === REGENERATION WITH LLM STARTED ===")
        print(f"[AGENT: CodeGenerator] Session ID: {session_id}")
        print("[AGENT: CodeGenerator] Using LLM to fix code based on review feedback")

        resources = state.get("resources", [])

        # Prepare existing code for LLM
        files_content = "\n\n".join(
            [f"=== {name} ===\n{content}" for name, content in existing_code.items()]
        )

        # Log files being regenerated
        print("[AGENT: CodeGenerator] Files to be regenerated:")
        for idx, (file_name, content) in enumerate(existing_code.items(), 1):
            print(f"  [{idx}] {file_name} ({len(content)} chars)")

        # Log the feedback again for clarity
        print("[AGENT: CodeGenerator] Review feedback being used:")
        print("=" * 60)
        print(review_feedback)
        print("=" * 60)

        system_prompt = """You are an expert Terraform engineer. Your task is to fix the provided Terraform code based on the review feedback.

Rules:
1. Fix ALL issues mentioned in the feedback
2. Maintain proper Terraform syntax
3. Follow best practices (proper naming, add tags where supported)
4. Ensure the code will run without errors
5. Keep the same file structure

CRITICAL - DO NOT REPLACE ACTUAL VALUES WITH VARIABLES:
- Keep ALL hardcoded values as they are (passwords, usernames, regions, VM sizes, etc.)
- These values come from Excel input and MUST remain as literals
- NEVER replace admin_password = "xxx" with var.admin_password
- NEVER replace admin_username = "xxx" with var.admin_username
- NEVER replace location/region values with variables
- Only provider-level subscription_id should use variables

CRITICAL Azure-Specific Constraints (DO NOT VIOLATE):
- NEVER add tags to azurerm_subnet - it does NOT support tags parameter
- NEVER add tags to azurerm_subnet_network_security_group_association
- Only add tags to Azure resources that explicitly support them:
  * azurerm_resource_group
  * azurerm_virtual_network
  * azurerm_network_security_group
  * azurerm_network_interface
  * azurerm_public_ip
  * azurerm_virtual_machine / azurerm_linux_virtual_machine / azurerm_windows_virtual_machine
  * azurerm_storage_account
  * azurerm_mssql_server / azurerm_mssql_database

CRITICAL Azure VM Constraints:
- For azurerm_linux_virtual_machine and azurerm_windows_virtual_machine:
  * USE 'zone' (string, e.g., zone = "1") NOT 'zones' (list)
- For azurerm_managed_disk:
  * USE 'zone' (string, e.g., zone = "1") NOT 'zones' (list)
- For azurerm_public_ip:
  * USE 'zones' (list of strings, e.g., zones = ["1"])

CRITICAL Azure VM Authentication Constraints:
- For azurerm_linux_virtual_machine with PASSWORD authentication (when admin_password is set):
  * MUST include: disable_password_authentication = false
  * Do NOT include admin_ssh_key block
- For azurerm_linux_virtual_machine with SSH authentication:
  * MUST include: disable_password_authentication = true
  * MUST include admin_ssh_key block with public_key
- NEVER remove authentication settings from the original code unless explicitly asked

CRITICAL AzureRM Provider v4.x Parameter Changes (MUST USE NEW NAMES):
- Storage Account (azurerm_storage_account):
  * USE `https_traffic_only_enabled` NOT `enable_https_traffic_only` (v3.x deprecated)
  * USE `min_tls_version` NOT `minimum_tls_version` for storage account
  * USE `allow_nested_items_to_be_public` NOT `allow_blob_public_access` (v3.x deprecated)
- SQL Database (azurerm_mssql_database):
  * DO NOT create `azurerm_mssql_database_transparent_data_encryption` resource (does not exist in v4.x, TDE is enabled by default)
  * DO NOT create `azurerm_mssql_database_vulnerability_assessment` resource (does not exist in v4.x)
  * Vulnerability assessment is configured via `azurerm_mssql_server_security_alert_policy` or server-level settings
- Network Interface (azurerm_network_interface):
  * NEVER use `network_security_group_id` parameter inside azurerm_network_interface resource (REMOVED in v4.x)
  * To associate NSG with NIC, MUST create separate `azurerm_network_interface_security_group_association` resource
  * CORRECT v4.x pattern:
    resource "azurerm_network_interface" "example" { ... }  # NO network_security_group_id here!
    resource "azurerm_network_interface_security_group_association" "example" {
      network_interface_id      = azurerm_network_interface.example.id
      network_security_group_id = azurerm_network_security_group.example.id
    }

Output ONLY the fixed code in this exact format:
```filename.tf
<file content>
```

For each file, use the above format. Do not include explanations outside the code blocks.
"""

        user_prompt = f"""## Original Requirements:
{json.dumps(resources, indent=2)}

## Current Code (needs fixing):
{files_content}

## Review Feedback (issues to fix):
{review_feedback}

Please fix all the issues and output the corrected Terraform code.
"""

        print("[AGENT: CodeGenerator] Calling LLM to fix code...")
        response = self.llm_client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,  # Low temperature for more precise fixes
            max_tokens=8000,
        )

        print(f"[AGENT: CodeGenerator] LLM response received ({len(response)} chars)")

        # Parse the fixed code from response
        fixed_files = self._parse_code_blocks(response, existing_code)

        # Auto-fix Azure compatibility issues
        if fixed_files:
            from app.services.azure_validator import AzureTerraformValidator

            print(
                "[AGENT: CodeGenerator] Running Azure validator on regenerated code..."
            )
            fixed_files = AzureTerraformValidator.validate_generated_files(fixed_files)

        if fixed_files:
            state["generated_code"] = fixed_files
            state["workflow_state"] = "code_regenerated"
            state["generation_summary"] = (
                f"Regenerated {len(fixed_files)} Terraform files based on review feedback"
            )

            ai_response = f"♻ Code regenerated based on review feedback.\n\n"
            ai_response += f"**Files updated:** {', '.join(fixed_files.keys())}\n"
            ai_response += "Submitting for re-review..."

            print(
                f"[AGENT: CodeGenerator] Successfully regenerated {len(fixed_files)} files"
            )
            print("[AGENT: CodeGenerator] Regenerated files:")
            for idx, (file_name, content) in enumerate(fixed_files.items(), 1):
                print(f"  [{idx}] {file_name} ({len(content)} chars)")
                # Print first 200 chars of each file for verification
                preview = content[:200].replace("\n", " ")
                print(f"      Preview: {preview}...")
        else:
            # Fallback: keep original code
            state["workflow_state"] = "code_regenerated"
            ai_response = "Code regeneration attempted. Submitting for re-review..."
            print("[AGENT: CodeGenerator] Could not parse fixed code, keeping original")
            print("[AGENT: CodeGenerator] Original files preserved:")
            for idx, (file_name, content) in enumerate(existing_code.items(), 1):
                print(f"  [{idx}] {file_name} ({len(content)} chars)")

        state["ai_response"] = ai_response
        state["messages"].append({"role": "assistant", "content": ai_response})

        print("[AGENT: CodeGenerator] === REGENERATION FINISHED ===")
        print("[AGENT: CodeGenerator] FINISHED - Regeneration complete")
        print("=" * 80 + "\n")

        ProgressTracker.agent_completed(session_id, AgentType.CODE_GENERATOR)
        return state

    def _parse_code_blocks(
        self, response: str, fallback: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Parse code blocks from LLM response.

        Args:
            response: LLM response containing code blocks
            fallback: Fallback files if parsing fails

        Returns:
            Dictionary of filename -> content
        """
        import re

        files = {}

        # Pattern to match ```filename.tf\n<content>\n```
        pattern = r"```(\S+\.tf)\s*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        for filename, content in matches:
            files[filename] = content.strip()
            print(
                f"[AGENT: CodeGenerator] Parsed file: {filename} ({len(content)} chars)"
            )

        # If no files parsed, try alternative pattern
        if not files:
            # Try pattern: === filename.tf ===\n<content>
            alt_pattern = r"===\s*(\S+\.tf)\s*===\s*\n(.*?)(?====|$)"
            alt_matches = re.findall(alt_pattern, response, re.DOTALL)
            for filename, content in alt_matches:
                files[filename] = content.strip()

        # If still no files, return fallback
        if not files:
            print("[AGENT: CodeGenerator] No code blocks found, using fallback")
            return fallback

        return files

    def code_generator(self, state: AgentState) -> AgentState:
        """
        Generate IaC code from validated resources.
        If review feedback exists, use LLM to fix issues.

        Args:
            state: Current agent state

        Returns:
            Updated state
        """
        session_id = state.get("session_id", "")
        ProgressTracker.agent_started(session_id, AgentType.CODE_GENERATOR)

        print("\n" + "=" * 80)
        print("[AGENT: CodeGenerator] STARTED")
        print(f"[AGENT: CodeGenerator] Session ID: {state.get('session_id')}")
        state["workflow_state"] = "generating_code"

        # Check if this is a regeneration attempt with review feedback
        review_feedback = state.get("review_feedback") or ""
        existing_code = state.get("generated_code") or {}
        review_attempt = state.get("review_attempt") or 0

        if review_feedback and existing_code and review_attempt > 0:
            # Use LLM to fix the code based on review feedback
            print(f"[AGENT: CodeGenerator] Regeneration attempt {review_attempt}")
            print("[AGENT: CodeGenerator] === FULL REVIEW FEEDBACK RECEIVED ===")
            print(review_feedback)
            print("[AGENT: CodeGenerator] === END OF REVIEW FEEDBACK ===")
            print(
                f"[AGENT: CodeGenerator] Existing files to fix: {list(existing_code.keys())}"
            )
            return self._regenerate_with_llm(state, existing_code, review_feedback)

        # First-time generation: Use Terraform code generator service
        from app.services.terraform_generator import TerraformCodeGenerator
        from app.services.azure_validator import AzureTerraformValidator

        generator = TerraformCodeGenerator()
        generated_files = {}

        if state.get("resources"):
            print(
                f"[AGENT: CodeGenerator] Received {len(state['resources'])} resources"
            )
            print(f"[AGENT: CodeGenerator] Resources structure:")
            for idx, resource in enumerate(state["resources"]):
                print(
                    f"  [{idx}] Type: {resource.get('resource_type', resource.get('type'))}, "
                    f"Name: {resource.get('resource_name', resource.get('name'))}, "
                    f"Platform: {resource.get('cloud_platform')}"
                )
            print(
                f"[AGENT: CodeGenerator] Full resource data:\n{json.dumps(state['resources'], indent=2)}"
            )

            try:
                # Generate Terraform code using Jinja2 templates
                print(
                    "[AGENT: CodeGenerator] Calling TerraformCodeGenerator.generate_code()..."
                )
                generated_files = generator.generate_code(state["resources"])

                # Auto-fix Azure compatibility issues
                print("[AGENT: CodeGenerator] Running Azure validator...")
                generated_files = AzureTerraformValidator.validate_generated_files(
                    generated_files
                )

                print(
                    f"[AGENT: CodeGenerator] Successfully generated {len(generated_files)} files"
                )
                for filename, content in generated_files.items():
                    content_preview = content[:200] if len(content) > 200 else content
                    print(
                        f"[AGENT: CodeGenerator]   - {filename}: {len(content)} bytes"
                    )
                    print(f"[AGENT: CodeGenerator]     Preview: {content_preview}...")

                if not generated_files or all(
                    len(content) == 0 for content in generated_files.values()
                ):
                    raise Exception("Generated files are empty or missing")

                state["generated_code"] = generated_files
                state["workflow_state"] = "completed"
                state["generation_summary"] = (
                    f"Generated {len(generated_files)} Terraform files for {len(state['resources'])} resources"
                )

                print(
                    f"[AGENT: CodeGenerator] Generation summary: {state['generation_summary']}"
                )

                ai_response = f"✓ Successfully generated Terraform code!\n\n"
                ai_response += (
                    f"**Files created:** {', '.join(generated_files.keys())}\n"
                )
                ai_response += f"**Resource count:** {len(state['resources'])}\n\n"
                ai_response += "The code is ready for download. You can review it in the code preview panel."

            except Exception as e:
                print(f"[AGENT: CodeGenerator] ERROR during code generation: {str(e)}")
                import traceback

                traceback.print_exc()

                generated_files = {}
                state["errors"] = (state.get("errors") or []) + [
                    f"Code generation error: {str(e)}"
                ]
                ai_response = f"✗ Error generating code: {str(e)}"
                print(f"[AGENT: CodeGenerator] Error details added to state")
        else:
            print("[AGENT: CodeGenerator] No resources found in state")
            ai_response = "No resources to generate code for."

        state["ai_response"] = ai_response
        state["messages"].append({"role": "assistant", "content": ai_response})

        print(
            f"[AGENT: CodeGenerator] FINISHED - Status: {'SUCCESS' if generated_files else 'FAILED'}"
        )
        print("=" * 80 + "\n")

        ProgressTracker.agent_completed(session_id, AgentType.CODE_GENERATOR)
        return state

    def should_continue_workflow(self, state: AgentState) -> str:
        """
        Determine next step in workflow.

        Args:
            state: Current agent state

        Returns:
            Next node name or "end"
        """
        if not state.get("should_continue", True):
            return "end"

        workflow_state = state.get("workflow_state", "")

        if (
            workflow_state == "parsing_excel"
            or workflow_state == "collecting_information"
            or workflow_state == "information_collection"
        ):
            return "information_collector"
        elif workflow_state == "waiting_for_user":
            return "end"
        elif workflow_state == "information_collected":
            return "compliance_checker"
        elif (
            workflow_state == "checking_compliance"
            or workflow_state == "compliance_check"
        ):
            return "compliance_checker"
        elif workflow_state == "compliance_failed":
            return "end"
        elif workflow_state == "generating_code":
            return "code_generator"
        elif workflow_state == "completed":
            return "end"
        else:
            # Default: end to prevent loops if state is unknown
            return "end"
