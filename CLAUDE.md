# JDBC-MCP Project Guidelines

## Authoritative Documentation
- Claude Code MCP Configuration: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/tutorials

## Build/Run/Test Commands
- Install dependencies: `pip install -r requirements.txt`
- Run MCP server in stdio mode: `./run-jdbc-mcp.sh`
- Run MCP server with SSE: `./run-jdbc-mcp.sh --transport sse --host 127.0.0.1 --port 8000`
- Logging: Check logs in `logs/jdbc_mcp.log`

## Code Style Guidelines
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Imports**: Group standard lib, third-party, then local imports with a blank line between groups
- **Types**: Always use type annotations from `typing` module; use Pydantic for data validation
- **Error Handling**: Use specific exceptions with meaningful error messages; log errors with context
- **Documentation**: Use docstrings for classes/functions; add inline comments for complex logic
- **Validation**: Use Pydantic validators for input validation; implement security checks (SQL injection)
- **Structure**: Keep code modular with clear separation of concerns (configuration, client, API)
- **Security**: Only allow SELECT queries; validate all inputs; use environment variables for credentials
- **Logging**: Use structured logging with appropriate log levels; log both to file and stderr