# JDBC Simple MCP

A Model Context Protocol (MCP) implementation for interacting with databases via JDBC. This implementation provides a simple interface for:
- Executing SELECT queries
- Exploring database schema (tables and columns)
- Viewing table relationships (primary and foreign keys)

This project was developed using an AI coding assistant (Claude) in Cursor IDE to quickly create a read-only database exploration tool. The implementation is intentionally restricted to SELECT queries for security purposes.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Features](#features)
- [Setup](#setup)
- [Using with Cursor IDE](#using-with-cursor-ide)
- [Using with Claude Code](#using-with-claude-code)
- [Available Tools](#available-tools)
- [Example Responses](#example-responses)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **JDBC Driver**:
   - Download the appropriate JDBC driver for your database and place it in the `libs` directory:
     - Oracle: [ojdbc11.jar](https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html)
       - This is the primary database driver we've tested with
     - PostgreSQL: [postgresql-42.6.0.jar](https://jdbc.postgresql.org/download/)
     - MySQL: [mysql-connector-j-8.2.0.jar](https://dev.mysql.com/downloads/connector/j/)
     - H2 (lightweight embedded database): [h2-2.2.224.jar](https://mvnrepository.com/artifact/com.h2database/h2)
   - Create a `libs` directory in the project root if it doesn't exist
   - Place the downloaded driver JAR in the `libs` directory

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

2. Create a `.env` file with your database configuration (use `.env.example` as a template):
```env
# Oracle example (primary tested database)
JDBC_URL=jdbc:oracle:thin:@//hostname:port/service_name
JDBC_DRIVER=oracle.jdbc.OracleDriver
JDBC_DRIVER_PATH=/path/to/ojdbc11.jar
DB_USERNAME=your_username
DB_PASSWORD=your_password

# PostgreSQL example
# JDBC_URL=jdbc:postgresql://localhost:5432/mydb
# JDBC_DRIVER=org.postgresql.Driver
# JDBC_DRIVER_PATH=/path/to/postgresql-42.6.0.jar
# DB_USERNAME=myuser
# DB_PASSWORD=mypassword

# MySQL example
# JDBC_URL=jdbc:mysql://localhost:3306/mydb
# JDBC_DRIVER=com.mysql.cj.jdbc.Driver
# JDBC_DRIVER_PATH=/path/to/mysql-connector-j-8.2.0.jar
# DB_USERNAME=myuser
# DB_PASSWORD=mypassword

# H2 example
# JDBC_URL=jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1
# JDBC_DRIVER=org.h2.Driver
# JDBC_DRIVER_PATH=/path/to/h2-2.2.224.jar
# DB_USERNAME=sa
# DB_PASSWORD=
```

> **Note on Configuration Precedence**: When running the MCP server directly, it will use the values from this `.env` file. However, when running through Cursor IDE or Claude Code, the environment variables specified in their respective JSON configuration files (shown in sections below) will take precedence over the values in this `.env` file.

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
        "JDBC_URL": "jdbc:oracle:thin:@//hostname:port/service_name",
        "JDBC_DRIVER": "oracle.jdbc.OracleDriver",
        "JDBC_DRIVER_PATH": "/path/to/ojdbc11.jar",
        "DB_USERNAME": "your_username",
        "DB_PASSWORD": "your_password"
        
        // For PostgreSQL/MySQL/H2, adjust the connection parameters accordingly:
        // "JDBC_URL": "jdbc:postgresql://localhost:5432/mydb",
        // "JDBC_DRIVER": "org.postgresql.Driver",
        // "JDBC_DRIVER_PATH": "/path/to/postgresql-42.6.0.jar",
        // "DB_USERNAME": "myuser",
        // "DB_PASSWORD": "mypassword"
        
        // H2 in-memory database:
        // "JDBC_URL": "jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1",
        // "JDBC_DRIVER": "org.h2.Driver",
        // "JDBC_DRIVER_PATH": "/path/to/h2-2.2.224.jar",
        // "DB_USERNAME": "sa",
        // "DB_PASSWORD": ""
      }
    }
  }
}
```

Replace the environment variables with your actual database configuration. Remember that these settings will take precedence over any values in the `.env` file.

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

1. Configure Claude Code to start the MCP server automatically using a config file:
   - Create a file at `~/.claude-code/config.json` with:
   ```json
   {
     "mcp_servers": [
       {
         "name": "jdbc-mcp",
         "command": "/absolute/path/to/jdbc-mcp/run-jdbc-mcp.sh",
         "env": {
           "JDBC_URL": "jdbc:oracle:thin:@//hostname:port/service_name",
           "JDBC_DRIVER": "oracle.jdbc.OracleDriver",
           "JDBC_DRIVER_PATH": "/path/to/ojdbc11.jar",
           "DB_USERNAME": "your_username",
           "DB_PASSWORD": "your_password"
           
           // For other database types including H2, update accordingly
           // H2 example:
           // "JDBC_URL": "jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1",
           // "JDBC_DRIVER": "org.h2.Driver", 
           // "JDBC_DRIVER_PATH": "/path/to/h2-2.2.224.jar",
           // "DB_USERNAME": "sa",
           // "DB_PASSWORD": ""
         }
       }
     ]
   }
   ```

2. Replace the environment variables with your actual database configuration. Note that these settings will override any values from the `.env` file.

3. Run Claude Code without additional flags:
   ```bash
   claude-code
   ```

4. The JDBC tools will be automatically available in Claude Code, with tool names prefixed by `mcp__jdbc-mcp__` (e.g., `mcp__jdbc-mcp__execute_query`).

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