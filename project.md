# Agentic Web Search

The goal of this project is to expand OpenCode with web search capabilities. To achieve this, we need
to create an MCP server that can perform web searches by using, for example, Duck Duck Go, or Google search API.

We then leverage this server to create a new tool into OpenCode, something like "web-search".

## Basic Tech Stack

We use Docker to encapsulate the service. Base image can be Ubuntu server, for example, or other
similar common Linux distro.

We use Python for MCP server development due to its more mature ecosystem and established tooling (FastMCP, comprehensive SDK), despite Node.js/TS preference.

Other details about the tech stack will be updated once the development starts.

## Implementation Plan

### Phase 1: Research and Setup
1. **Evaluate MCP Ecosystem Maturity**
   - Research completed: Python chosen for mature MCP ecosystem (FastMCP, comprehensive SDK)
   - Node.js/TS has basic support but less mature tooling and documentation

2. **Choose Search API**
   - Evaluate DuckDuckGo API (free, no API key required)
   - Research Google Search API (requires API key, more comprehensive results)
   - Select API based on ease of integration and rate limits

3. **Project Structure Setup**
   - Initialize Python project with FastMCP
   - Create basic directory structure for MCP server
   - Set up Docker configuration

### Phase 2: MCP Server Development
1. **Core MCP Server Implementation**
   - Set up basic MCP server following protocol specifications
   - Implement server lifecycle (start, stop, health checks)
   - Add logging and error handling

2. **Web Search Integration**
   - Implement search API client (DuckDuckGo or Google)
   - Create search tool with proper input validation
   - Handle API rate limits and errors gracefully
   - Format search results for OpenCode consumption

3. **Docker Containerization**
   - Create Dockerfile with appropriate base image
   - Configure environment variables for API keys
   - Set up proper networking and port exposure
   - Test container build and execution

### Phase 3: OpenCode Integration
1. **Tool Wrapper Development**
   - Create OpenCode tool interface for "web-search"
   - Implement communication between OpenCode and MCP server
   - Add configuration options for search providers

2. **Testing and Validation**
   - Write unit tests for MCP server components
   - Test integration with OpenCode
   - Validate search functionality with various queries
   - Performance testing and optimization

### Phase 4: Documentation and Deployment
1. **Documentation**
   - Update AGENTS.md with build/test commands
   - Create README with setup instructions
   - Document API usage and configuration

2. **Final Integration**
   - Ensure seamless integration with OpenCode workflow
   - Add error handling for network issues
   - Optimize for performance and reliability

## MVP Status - COMPLETE ✅

The first version of the MCP Web Search tool has been successfully implemented and tested with the following features:

- ✅ Python-based HTTP API server using FastAPI framework
- ✅ DuckDuckGo search integration with proper HTML parsing
- ✅ Comprehensive error handling and logging
- ✅ Docker containerization with docker-compose
- ✅ RESTful API endpoints: `/health` and `/search`
- ✅ Port 8000 exposed and working
- ✅ Proper project structure and documentation

The server runs as an HTTP API that can be configured as a remote MCP server in OpenCode.

### Live Testing Results
- **Health Check**: ✅ Returns `{"status":"healthy","message":"Web search service is operational","test_query_successful":true}`
- **Search Query**: ✅ Successfully returns 10 DuckDuckGo search results for test queries
- **Docker Integration**: ✅ Container runs properly and exposes port 8000

Next steps involve configuring OpenCode to use this as a remote MCP server and testing the integration.

## Success Criteria
- Functional MCP server that performs web searches
- Successful integration with OpenCode as "web-search" tool
- Dockerized deployment ready for production use
- Comprehensive documentation and testing
