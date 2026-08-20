import json
import asyncio
from typing import Dict, Any, Optional
from tools_engine import tools_gateway
from storage import storage

MCP_SERVER_INFO = {
    "name": "Stateful-Companion-MCP-Server",
    "version": "2.0.0",
    "protocolVersion": "2024-11-05",
    "description": "Official Model Context Protocol (MCP) Server for the Stateful AI Life Companion"
}

class MCPServer:
    """
    Standardized JSON-RPC 2.0 Model Context Protocol (MCP) Server.
    Provides tools/list, tools/call, resources/list, and resources/read endpoints.
    """
    def __init__(self, tool_gateway=tools_gateway, storage_manager=storage):
        self.gateway = tool_gateway
        self.storage = storage_manager

    async def handle_json_rpc(self, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handles JSON-RPC 2.0 request payload."""
        req_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        if not method:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: Missing method."}
            }

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "serverInfo": MCP_SERVER_INFO,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"subscribe": False}
                        }
                    }
                }

            elif method == "tools/list":
                tools = self.gateway.get_tool_definitions()
                mcp_tools = []
                for t in tools:
                    mcp_tools.append({
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t.get("parameters", {})
                    })
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": mcp_tools}
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                if not tool_name:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": "Invalid params: 'name' is required."}
                    }
                
                result = await self.gateway.execute_tool(user_id=user_id, name=tool_name, arguments=tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ],
                        "isError": (result.get("status") == "error")
                    }
                }

            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": [
                            {"uri": "companion://profile", "name": "User Profile Facts", "mimeType": "application/json"},
                            {"uri": "companion://knowledge_graph", "name": "Life Knowledge Graph", "mimeType": "application/json"},
                            {"uri": "companion://tasks", "name": "Active Tasks", "mimeType": "application/json"}
                        ]
                    }
                }

            elif method == "resources/read":
                uri = params.get("uri", "")
                if uri == "companion://profile":
                    data = self.storage.get_profile_facts(user_id)
                elif uri == "companion://knowledge_graph":
                    data = self.storage.get_knowledge_graph(user_id)
                elif uri == "companion://tasks":
                    data = self.storage.get_tasks(user_id)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": f"Unknown resource URI: '{uri}'"}
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [
                            {"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}
                        ]
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: '{method}'"}
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Internal Server Error: {str(e)}"}
            }

mcp_server = MCPServer()
