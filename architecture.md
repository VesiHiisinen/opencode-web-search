# MCP Web Search Server - Architecture

## What is MCP?

**MCP (Model Context Protocol)** is a protocol for connecting AI assistants to external tools and data sources. Think of it as "USB-C for AI applications" - a standardized way for LLMs to discover and use capabilities provided by external servers.

### Key Characteristics

| Aspect | REST API | MCP |
|--------|----------|-----|
| **Purpose** | Client-server communication for apps | LLM-tool communication |
| **Discovery** | Manual (read docs) | Automatic (tool schemas exposed) |
| **Transport** | HTTP/HTTPS | HTTP/SSE or stdio |
| **Protocol** | HTTP verbs + JSON | JSON-RPC 2.0 |
| **State** | Stateless | Stateful connection with lifecycle |
| **Intent** | CRUD operations | Tool execution + context sharing |

## Architecture Overview

```mermaid
graph TB
    subgraph "OpenCode"
        OC[OpenCode Client]
        MCP_Client[MCP Client Implementation]
    end
    
    subgraph "Network"
        HTTP[HTTP/HTTPS]
        SSE[Server-Sent Events]
    end
    
    subgraph "MCP Server"
        Transport[MCP Transport Layer<br/>HTTP + SSE]
        Protocol[MCP Protocol Layer<br/>JSON-RPC 2.0]
        Server[MCPServer Class]
        Tools[Tools Registry]
        Search[DuckDuckGoSearcher]
    end
    
    subgraph "External"
        DDG[DuckDuckGo HTML Search]
    end
    
    OC --> MCP_Client
    MCP_Client -->|HTTP POST| Transport
    MCP_Client -->|SSE GET| Transport
    Transport --> Protocol
    Protocol -->|tools/call| Server
    Server --> Tools
    Tools -->|web_search| Search
    Search -->|HTTP GET| DDG
```

## MCP Protocol Flow

### 1. Connection Lifecycle

```mermaid
sequenceDiagram
    participant Client as OpenCode MCP Client
    participant SSE as SSE Endpoint (/)
    participant MCP as MCP Endpoint (/mcp)
    participant Server as MCPServer
    
    Note over Client,Server: Phase 1: Transport Connection
    Client->>+SSE: GET / (Accept: text/event-stream)
    SSE-->>Client: event: endpoint<br/>data: /mcp
    
    Note over Client,Server: Phase 2: Protocol Initialization
    Client->>+MCP: POST /mcp<br/>{jsonrpc: "2.0", method: "initialize", ...}
    MCP->>Server: handle_request(initialize)
    Server-->>MCP: {protocolVersion, capabilities, serverInfo}
    MCP-->>-Client: {jsonrpc: "2.0", result: {...}, id: 1}
    
    Note over Client,Server: Phase 3: Tool Discovery
    Client->>+MCP: POST /mcp<br/>{method: "tools/list"}
    MCP->>Server: handle_request(tools/list)
    Server-->>MCP: {tools: [...]}
    MCP-->>-Client: {jsonrpc: "2.0", result: {tools: [...]}}
    
    Note over Client,Server: Phase 4: Tool Execution
    Client->>+MCP: POST /mcp<br/>{method: "tools/call", params: {name: "web_search", ...}}
    MCP->>Server: handle_request(tools/call)
    Server->>Server: Execute web_search
    Server-->>MCP: {content: [...]}
    MCP-->>-Client: {jsonrpc: "2.0", result: {content: [...]}}
```

### 2. Transport Layer Detail

```mermaid
graph LR
    subgraph "Client"
        C_HTTP[HTTP Client]
    end
    
    subgraph "Connection"
        direction TB
        S_SSE[SSE Stream<br/>Server → Client]
        S_HTTP[HTTP POST<br/>Client → Server]
    end
    
    subgraph "Server"
        S_SSE_EP[SSE Endpoint<br/>GET /]
        S_MCP_EP[MCP Endpoint<br/>POST /mcp]
        S_JSON[JSON-RPC<br/>Handler]
    end
    
    C_HTTP -->|"SSE Subscribe"| S_SSE
    C_HTTP -->|"JSON-RPC Request"| S_HTTP
    S_SSE --> S_SSE_EP
    S_HTTP --> S_MCP_EP
    S_SSE_EP --> S_JSON
    S_MCP_EP --> S_JSON
```

## Comparison: REST vs MCP

### REST API Approach

```mermaid
sequenceDiagram
    participant Client
    participant REST as REST API Server
    participant Service
    
    Note over Client,Service: REST: Resource-oriented, Stateless
    
    Client->>+REST: GET /api/search?q=python
    REST->>Service: Perform search
    Service-->>REST: Results
    REST-->>-Client: HTTP 200<br/>{results: [...]}
    
    Note over Client,Service: Every request is independent
    
    Client->>+REST: GET /api/search?q=java
    REST->>Service: Perform search
    Service-->>REST: Results
    REST-->>-Client: HTTP 200<br/>{results: [...]}
```

### MCP Approach

```mermaid
sequenceDiagram
    participant Client as OpenCode
    participant MCP as MCP Server
    participant Search as Search Tool
    
    Note over Client,Search: MCP: Capability-oriented, Stateful
    
    Client->>+MCP: initialize()
    MCP-->>Client: Server capabilities + tools
    
    Client->>MCP: tools/list
    MCP-->>Client: Available tools with schemas
    
    loop Multiple Queries
        Client->>+MCP: tools/call<br/>{name: "web_search", args: {...}}
        MCP->>Search: Execute web_search
        Search-->>MCP: Results
        MCP-->>-Client: Tool output
    end
    
    Note over Client,Search: Tools are discovered, not hardcoded
```

## System Components

### Component Architecture

```mermaid
graph TB
    subgraph "MCP Server Container"
        direction TB
        
        subgraph "Transport Layer"
            HTTP_EP[HTTP Endpoints<br/>FastAPI]
            Health[/health]
            Search[/search]
            Root[/]
            MCP_EP[/mcp]
            SSE_EP[/sse]
            
            HTTP_EP --> Health
            HTTP_EP --> Search
            HTTP_EP --> Root
            HTTP_EP --> MCP_EP
            HTTP_EP --> SSE_EP
        end
        
        subgraph "Protocol Layer"
            MCP[MCPServer Class]
            JSON_RPC[JSON-RPC 2.0<br/>Request Handler]
            
            MCP --> JSON_RPC
        end
        
        subgraph "Application Layer"
            WS[web_search function]
            SH[search_health function]
            DDGS[DuckDuckGoSearcher]
            
            WS --> DDGS
        end
        
        MCP_EP --> JSON_RPC
        JSON_RPC --> WS
        JSON_RPC --> SH
    end
    
    subgraph "External"
        DDG[DuckDuckGo]
    end
    
    DDGS -->|HTTP Request| DDG
```

### Data Flow

```mermaid
flowchart LR
    A[Client Request] --> B{Endpoint Type}
    
    B -->|/health| C[search_health]
    B -->|/search| D[web_search]
    B -->|/mcp| E[JSON-RPC Handler]
    B -->|/| F[SSE Stream]
    
    E --> G{Method}
    G -->|initialize| H[Return Capabilities]
    G -->|tools/list| I[Return Tool Registry]
    G -->|tools/call| J[Execute Tool]
    G -->|ping| K[Return Pong]
    
    J --> L[web_search]
    L --> M[DuckDuckGoSearcher]
    M --> N[HTTP GET<br/>DuckDuckGo]
    N --> O[Parse HTML]
    O --> P[Extract URLs]
    P --> Q[Return Results]
    
    D --> L
    C --> R[Check Searcher]
```

## Why MCP Instead of REST?

### The Problem with REST for LLMs

```mermaid
graph LR
    subgraph "REST Approach"
        A1[LLM] -->|"Needs to know"| B1[API Documentation]
        B1 -->|"Hardcoded"| C1["GET /api/search?q=query"]
        A1 --> C1
        C1 --> D1[Results]
        D1 --> A1
    end
    
    subgraph "MCP Approach"
        A2[LLM] -->|"Discovers"| B2[MCP Server]
        B2 -->|"Exposes"| C2["Tool Schema: name, description, inputSchema"]
        A2 -->|"Uses"| C2
        C2 -->|"Calls"| D2["tools/call"]
        D2 --> E2[Results]
        E2 --> A2
    end
```

### Key Differences

| Feature | REST API | MCP |
|---------|----------|-----|
| **API Discovery** | Manual (docs, OpenAPI) | Automatic (tools/list) |
| **Tool Schema** | Separate (OpenAPI spec) | Built-in (inputSchema) |
| **Context Sharing** | Custom headers/cookies | Protocol-level support |
| **Multiple Tools** | Multiple endpoints | Single endpoint, dynamic dispatch |
| **LLM Optimized** | ❌ | ✅ (designed for LLM agents) |

## MCP Protocol Details

### JSON-RPC Message Format

```mermaid
classDiagram
    class JSON_RPC_Request {
        +string jsonrpc = "2.0"
        +string method
        +any params
        +any id
    }
    
    class JSON_RPC_Response {
        +string jsonrpc = "2.0"
        +any result
        +any id
    }
    
    class JSON_RPC_Error {
        +string jsonrpc = "2.0"
        +ErrorObject error
        +any id
    }
    
    class ErrorObject {
        +int code
        +string message
        +any data
    }
    
    class MCPTool {
        +string name
        +string description
        +InputSchema inputSchema
    }
    
    class InputSchema {
        +string type = "object"
        +Object properties
        +string[] required
    }
    
    JSON_RPC_Request --> JSON_RPC_Response : Success
    JSON_RPC_Request --> JSON_RPC_Error : Failure
    JSON_RPC_Error --> ErrorObject
    MCPTool --> InputSchema
```

### Server-Sent Events (SSE) Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    
    Note over C,S: SSE maintains persistent connection
    
    C->>S: GET / (Accept: text/event-stream)
    S-->>C: HTTP 200 (text/event-stream)
    
    Note over C,S: Server sends endpoint URL
    S-->>C: event: endpoint\ndata: /mcp\n\n
    
    Note over C,S: Connection stays open
    loop Keep-Alive
        S-->>C: : ping\n\n
    end
    
    Note over C,S: Client uses /mcp for messages
    C->>S: POST /mcp {jsonrpc: "2.0", ...}
    S-->>C: {jsonrpc: "2.0", result: {...}}
```

## Implementation Specifics

### Tool Definition

```mermaid
graph TD
    Tool[MCPTool] --> Schema[inputSchema]
    Schema --> Type[type: object]
    Schema --> Props[properties]
    Schema --> Required[required]
    
    Props --> Query[query: string]
    Props --> Max[max_results: integer]
    
    Query --> QDesc["description: Search query string"]
    Max --> MDesc["description: Maximum results (default: 10, min: 1, max: 50)"]
    
    Required --> ReqQuery[query]
```

### URL Extraction Flow

```mermaid
flowchart TD
    A[Raw DuckDuckGo URL] --> B{Protocol-relative?}
    B -->|Yes| C[Add https: prefix]
    B -->|No| D[Keep as-is]
    C --> E[Parse URL]
    D --> E
    E --> F{Has 'uddg' param?}
    F -->|Yes| G[Extract value]
    G --> H[URL Decode]
    F -->|No| I[Return original]
    H --> J[Return decoded URL]
    I --> K[Return URL]
    J --> K
```

## Summary

MCP is essentially a **capability discovery and execution protocol** built on JSON-RPC over HTTP+SSE. While REST is resource-oriented ("GET /users/123"), MCP is capability-oriented ("Call the web_search tool with these parameters").

The key insight: MCP servers **advertise their capabilities** with schemas, allowing LLMs to discover and use tools dynamically rather than relying on hardcoded API endpoints.

**For experienced REST developers:**
- Replace REST endpoints with `tools/call` endpoint
- Replace HTTP verbs with `method` field in JSON-RPC
- Replace API docs with `tools/list` response
- Add SSE for bidirectional communication
- Get automatic tool discovery and schema validation
