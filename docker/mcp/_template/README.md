# MCP Server Template

Template for creating new SDK-as-MCP servers.

## Quick Start

1. **Copy this directory**:
   ```bash
   cp -r docker/mcp/_template docker/mcp/<your_server_name>
   ```

2. **Customize files**:
   - `server.py` - Implement your SDK client and tools
   - `requirements.txt` - Add your SDK dependencies
   - `Dockerfile` - Adjust ports and environment variables
   - `README.md` - Document your server

3. **Add to docker-compose.yml**:
   ```yaml
   <your_server_name>_mcp:
     build:
       context: ./docker/mcp/<your_server_name>
       dockerfile: Dockerfile
     container_name: <your_server_name>_mcp
     restart: unless-stopped
     ports:
       - "8010:8010"  # Adjust port
     environment:
       - MCP_SERVER_HOST=0.0.0.0
       - MCP_SERVER_PORT=8010
     healthcheck:
       test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')"]
       interval: 30s
       timeout: 10s
       retries: 3
       start_period: 10s
     networks:
       - financeai_net
   ```

4. **Add to config/mcp_servers.yaml**:
   ```yaml
   <your_server_name>:
     enabled: true
     transport: sse
     url: "http://localhost:8010/sse"
     description: "Your server description"
     cache_tools_list: true
     tool_filter:
       allowlist: []
       blocklist: []
   ```

5. **Build and run**:
   ```bash
   docker-compose up <your_server_name>_mcp -d
   ```

## File Structure

```
docker/mcp/<your_server_name>/
├── Dockerfile          # Container build instructions
├── requirements.txt    # Python dependencies
├── server.py          # MCP server implementation
└── README.md          # Server documentation
```

## Implementation Checklist

- [ ] Define `TOOL_DEFINITIONS` with JSON Schema
- [ ] Implement `SDKClient` with your SDK calls
- [ ] Implement `_execute_tool()` to route tool calls
- [ ] Configure cache TTL per data type (optional)
- [ ] Add health check endpoint
- [ ] Test with `curl http://localhost:<port>/health`
- [ ] Test tools with `curl http://localhost:<port>/tools`

## Transport Options

### SSE (Recommended for HTTP servers)
```python
from mcp.server.sse import SseServerTransport
sse_transport = SseServerTransport("/sse")
```

### Streamable HTTP (Alternative)
For servers using streamable HTTP transport, see OpenBB example.

## Best Practices

1. **Caching**: Implement TTL-based caching for expensive API calls
2. **Rate Limiting**: Protect upstream APIs with rate limiting
3. **Error Handling**: Return structured error responses
4. **Logging**: Use structured logging for debugging
5. **Health Checks**: Always implement `/health` endpoint
