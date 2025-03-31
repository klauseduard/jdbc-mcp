# JDBC Simple MCP

A Model Context Protocol (MCP) implementation for interacting with databases via JDBC. This implementation provides a simple interface for:
- Executing SELECT queries
- Exploring database schema (tables and columns)
- Viewing table relationships (primary and foreign keys)

## Features

- **Safe Query Execution**: Only SELECT queries are allowed for security
- **Schema Exploration**: List tables and their columns
- **Relationship Discovery**: View primary keys and foreign key relationships
- **Connection Management**: Automatic connection handling and cleanup

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Download the appropriate JDBC driver JAR for your database. Common drivers:
- PostgreSQL: [postgresql-42.6.0.jar](https://jdbc.postgresql.org/download/)
  - Driver class: `org.postgresql.Driver`
  - URL format: `jdbc:postgresql://localhost:5432/mydb`
- MySQL: [mysql-connector-j-8.2.0.jar](https://dev.mysql.com/downloads/connector/j/)
  - Driver class: `com.mysql.cj.jdbc.Driver`
  - URL format: `jdbc:mysql://localhost:3306/mydb`
- Oracle: [ojdbc11.jar](https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html)
  - Driver class: `oracle.jdbc.OracleDriver`
  - URL format: `jdbc:oracle:thin:@localhost:1521:orcl`

3. Create a `.env` file with your database configuration:
```env
# PostgreSQL example
JDBC_URL=jdbc:postgresql://localhost:5432/mydb
JDBC_DRIVER=org.postgresql.Driver
JDBC_DRIVER_PATH=/path/to/postgresql-42.6.0.jar

# MySQL example
# JDBC_URL=jdbc:mysql://localhost:3306/mydb
# JDBC_DRIVER=com.mysql.cj.jdbc.Driver
# JDBC_DRIVER_PATH=/path/to/mysql-connector-j-8.2.0.jar

# Oracle example
# JDBC_URL=jdbc:oracle:thin:@localhost:1521:orcl
# JDBC_DRIVER=oracle.jdbc.OracleDriver
# JDBC_DRIVER_PATH=/path/to/ojdbc11.jar

DB_USERNAME=myuser
DB_PASSWORD=mypassword
```

## Using with Cursor IDE

1. Make sure the run script is executable:
```bash
chmod +x run-jdbc-mcp.sh
```

2. Configure the MCP server by creating `.cursor/mcp.json` in your project directory (for project-specific configuration) or `~/.cursor/mcp.json` in your home directory (for global configuration):

```json
{
  "mcpServers": {
    "jdbc-explorer": {
      "command": "/absolute/path/to/our-jdbc-simple/run-jdbc-mcp.sh",
      "env": {
        "JDBC_URL": "jdbc:postgresql://localhost:5432/mydb",
        "JDBC_DRIVER": "org.postgresql.Driver",
        "JDBC_DRIVER_PATH": "/path/to/postgresql-42.6.0.jar",
        "DB_USERNAME": "myuser",
        "DB_PASSWORD": "mypassword"
      }
    }
  }
}
```

Replace the paths and environment variables with your actual database configuration.

3. Restart Cursor IDE to load the new MCP configuration.

4. The JDBC tools will now be available in Cursor IDE:
   - `execute_query`: Run SELECT queries
   - `get_tables`: List database tables
   - `get_columns`: Get table structure

Example prompts:
- "Show me all users from the database"
- "What tables are available in the public schema?"
- "Tell me about the structure of the orders table"

Note: Cursor will automatically discover and make available the tools provided by the MCP server. You don't need to explicitly list them in the configuration.

## Using with Claude Code

1. Start the MCP server in SSE mode:
```bash
./run-jdbc-mcp.sh --transport sse --host 127.0.0.1 --port 8000
```

2. Configure Claude Code to use the MCP server:
```json
{
    "mcp_server": {
        "type": "sse",
        "url": "http://127.0.0.1:8000"
    }
}
```

3. The JDBC tools will be available through Claude Code's interface.

## Available Tools

1. `execute_query`:
   - Executes a SELECT query
   - Arguments:
     - `query`: SQL SELECT query to execute
     - `max_rows`: Maximum number of rows to return (default: 100, max: 1000)

2. `get_tables`:
   - Lists tables in the database
   - Arguments:
     - `schema`: Schema name (optional)
     - `include_system`: Whether to include system tables (default: false)

3. `get_columns`:
   - Gets column information for a table
   - Arguments:
     - `table_name`: Name of the table
     - `schema`: Schema name (optional)

## Example Responses

### Execute Query
```json
{
    "columns": ["id", "name", "email"],
    "rows": [
        [1, "John Doe", "john@example.com"],
        [2, "Jane Smith", "jane@example.com"]
    ],
    "row_count": 2,
    "has_more": false
}
```

### Get Tables
```json
{
    "tables": [
        {
            "table_name": "users",
            "schema": "public",
            "type": "TABLE",
            "remarks": "User accounts"
        }
    ],
    "count": 1
}
```

### Get Columns
```json
{
    "table_name": "users",
    "schema": "public",
    "columns": [
        {
            "name": "id",
            "type": "INTEGER",
            "size": 10,
            "nullable": false,
            "default": "nextval('users_id_seq')",
            "remarks": "Primary key"
        }
    ],
    "primary_keys": ["id"],
    "foreign_keys": [
        {
            "fk_name": "users_role_id_fkey",
            "fk_column": "role_id",
            "pk_table": "roles",
            "pk_column": "id"
        }
    ]
}
```

## Security Considerations

- Only SELECT queries are allowed to prevent data modification
- Connection details should be stored securely in environment variables
- Database user should have minimal required permissions
- Consider network security when connecting to remote databases

## Troubleshooting

1. **JDBC Driver Issues**:
   - Make sure the JDBC driver JAR file exists at the path specified in `.env`
   - Verify the driver class name matches your database type
   - Check that the JAR file has read permissions

2. **Connection Issues**:
   - Verify database credentials in `.env`
   - Check if the database is accessible from your machine
   - Make sure the database port is open and not blocked by firewall

3. **Python Environment**:
   - The run script automatically creates and manages a virtual environment
   - If you encounter issues, try removing the `venv` directory and letting it recreate 