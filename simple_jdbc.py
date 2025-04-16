#!/usr/bin/env python3
"""
A small self-contained JDBC MCP server for database querying and schema exploration.
"""
import sys
import logging
import json
from typing import Dict, Any, Optional, List
from enum import Enum
import os
import typer
import jaydebeapi
from mcp.server import FastMCP
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Set up logging to both stderr and file
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, "jdbc_mcp.log")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("simple_jdbc")
logger.info(f"Logging initialized, writing to {log_file}")

# Create the Typer app for CLI
app = typer.Typer()

class Transport(str, Enum):
    stdio = "stdio"
    sse = "sse"

class JdbcConfig(BaseModel):
    """JDBC configuration settings."""
    jdbc_url: str = Field(default=os.getenv("JDBC_URL", ""), description="JDBC URL (e.g., jdbc:postgresql://localhost:5432/mydb)")
    jdbc_driver: str = Field(default=os.getenv("JDBC_DRIVER", ""), description="JDBC driver class name")
    jdbc_driver_path: str = Field(default=os.getenv("JDBC_DRIVER_PATH", ""), description="Path to JDBC driver JAR file")
    username: str = Field(default=os.getenv("DB_USERNAME", ""), description="Database username")
    password: str = Field(default=os.getenv("DB_PASSWORD", ""), description="Database password")

class QueryArgs(BaseModel):
    """Arguments for the execute_query tool."""
    query: str = Field(description="SQL SELECT query to execute")
    max_rows: int = Field(default=100, description="Maximum number of rows to return", ge=1, le=1000)
    
    @field_validator('query')
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
        # Basic SQL injection prevention - only allow SELECT statements
        cleaned_query = v.strip().upper()
        if not cleaned_query.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for security reasons")
        
        return v.strip()

class GetTablesArgs(BaseModel):
    """Arguments for the get_tables tool."""
    schema: Optional[str] = Field(default=None, description="Schema name to list tables from (if None, uses default schema)")
    include_system: bool = Field(default=False, description="Whether to include system tables")

class GetColumnsArgs(BaseModel):
    """Arguments for the get_columns tool."""
    table_name: str = Field(description="Table name to get columns from")
    schema: Optional[str] = Field(default=None, description="Schema name (if None, uses default schema)")

    @field_validator('table_name')
    def validate_table_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Table name cannot be empty")
        return v.strip()

class JdbcError(Exception):
    """Base exception for JDBC errors."""
    pass

class JdbcClient:
    """Client for interacting with a database via JDBC with improved connection handling."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, config: JdbcConfig):
        self.config = config
        self._connection = None
        self._verify_config()
        self._last_used = 0
        self._connection_timeout = 300  # 5 minutes
        
    def _verify_config(self):
        """Verify that the configuration is valid."""
        if not self.config.jdbc_url:
            raise JdbcError("JDBC URL is required")
        if not self.config.jdbc_driver:
            raise JdbcError("JDBC driver class name is required")
        if not self.config.jdbc_driver_path:
            raise JdbcError("JDBC driver JAR path is required")
        if not os.path.exists(self.config.jdbc_driver_path):
            raise JdbcError(f"JDBC driver JAR not found at {self.config.jdbc_driver_path}")

    def _is_connection_valid(self) -> bool:
        """Check if the current connection is valid and not timed out."""
        if not self._connection:
            return False
        
        try:
            # Check if connection is too old
            if time.time() - self._last_used > self._connection_timeout:
                logger.info("Connection timed out, will reconnect")
                return False
            
            # Test connection with a lightweight query
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.warning(f"Connection test failed: {str(e)}")
            return False

    def connect(self) -> bool:
        """Establish a database connection with retry logic."""
        retries = 0
        last_error = None
        
        while retries < self.MAX_RETRIES:
            try:
                if self._connection:
                    try:
                        self._connection.close()
                    except Exception:
                        pass
                
                self._connection = jaydebeapi.connect(
                    self.config.jdbc_driver,
                    self.config.jdbc_url,
                    [self.config.username, self.config.password],
                    self.config.jdbc_driver_path,
                )
                self._last_used = time.time()
                logger.info("Successfully established database connection")
                return True
            except Exception as e:
                last_error = e
                retries += 1
                if retries < self.MAX_RETRIES:
                    logger.warning(f"Connection attempt {retries} failed: {str(e)}. Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
        
        logger.error(f"Failed to connect after {self.MAX_RETRIES} attempts. Last error: {str(last_error)}")
        raise JdbcError(f"Connection failed after {self.MAX_RETRIES} attempts: {str(last_error)}")

    def ensure_connection(self):
        """Ensure we have a valid connection, reconnecting if necessary."""
        if not self._is_connection_valid():
            self.connect()

    def close(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
            finally:
                self._connection = None
                self._last_used = 0

    def execute_query(self, query: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute a SELECT query with retry logic."""
        retries = 0
        last_error = None
        
        while retries < self.MAX_RETRIES:
            try:
                self.ensure_connection()
                
                with self._connection.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchmany(max_rows)
                    self._last_used = time.time()
                    
                    return {
                        "columns": columns,
                        "rows": [list(row) for row in rows],
                        "row_count": len(rows),
                        "has_more": cursor.fetchone() is not None
                    }
            except Exception as e:
                last_error = e
                retries += 1
                
                # Check if it's a connection error
                if "connection" in str(e).lower() or "network" in str(e).lower():
                    logger.warning(f"Connection error during query execution: {str(e)}")
                    # Force reconnection on next attempt
                    self._connection = None
                    if retries < self.MAX_RETRIES:
                        logger.info(f"Retrying query in {self.RETRY_DELAY} seconds...")
                        time.sleep(self.RETRY_DELAY)
                        continue
                else:
                    # If it's not a connection error, don't retry
                    logger.error(f"Query execution failed: {str(e)}")
                    raise JdbcError(f"Query failed: {str(e)}")
        
        logger.error(f"Query failed after {self.MAX_RETRIES} attempts. Last error: {str(last_error)}")
        raise JdbcError(f"Query failed after {self.MAX_RETRIES} attempts: {str(last_error)}")

    def get_tables(self, schema: Optional[str] = None, include_system: bool = False) -> Dict[str, Any]:
        """Get list of tables with retry logic."""
        retries = 0
        last_error = None
        
        while retries < self.MAX_RETRIES:
            try:
                self.ensure_connection()
                cursor = self._connection.cursor()
                
                # Use DatabaseMetaData through the connection directly
                metadata = self._connection.jconn.getMetaData()
                rs = metadata.getTables(None, schema, "%", ["TABLE"] if not include_system else None)
                
                tables = []
                while rs.next():
                    tables.append({
                        "table_name": rs.getString("TABLE_NAME"),
                        "schema": rs.getString("TABLE_SCHEM"),
                        "type": rs.getString("TABLE_TYPE"),
                        "remarks": rs.getString("REMARKS")
                    })
                
                self._last_used = time.time()
                return {
                    "tables": tables,
                    "count": len(tables)
                }
            except Exception as e:
                last_error = e
                retries += 1
                
                if "connection" in str(e).lower() or "network" in str(e).lower():
                    logger.warning(f"Connection error while getting tables: {str(e)}")
                    self._connection = None
                    if retries < self.MAX_RETRIES:
                        logger.info(f"Retrying get_tables in {self.RETRY_DELAY} seconds...")
                        time.sleep(self.RETRY_DELAY)
                        continue
                else:
                    logger.error(f"Failed to get tables: {str(e)}")
                    raise JdbcError(f"Failed to get tables: {str(e)}")
            finally:
                if 'cursor' in locals():
                    cursor.close()
        
        logger.error(f"Failed to get tables after {self.MAX_RETRIES} attempts. Last error: {str(last_error)}")
        raise JdbcError(f"Failed to get tables after {self.MAX_RETRIES} attempts: {str(last_error)}")

    def get_columns(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """Get column information with retry logic."""
        retries = 0
        last_error = None
        
        while retries < self.MAX_RETRIES:
            try:
                self.ensure_connection()
                cursor = self._connection.cursor()
                
                # Use DatabaseMetaData through the connection directly
                metadata = self._connection.jconn.getMetaData()
                rs = metadata.getColumns(None, schema, table_name, "%")
                
                columns = []
                while rs.next():
                    columns.append({
                        "name": rs.getString("COLUMN_NAME"),
                        "type": rs.getString("TYPE_NAME"),
                        "size": rs.getInt("COLUMN_SIZE"),
                        "nullable": rs.getBoolean("NULLABLE"),
                        "default": rs.getString("COLUMN_DEF"),
                        "remarks": rs.getString("REMARKS")
                    })
                
                # Get primary key information
                rs = metadata.getPrimaryKeys(None, schema, table_name)
                pk_columns = []
                while rs.next():
                    pk_columns.append(rs.getString("COLUMN_NAME"))
                
                # Get foreign key information
                rs = metadata.getImportedKeys(None, schema, table_name)
                foreign_keys = []
                while rs.next():
                    foreign_keys.append({
                        "fk_name": rs.getString("FK_NAME"),
                        "fk_column": rs.getString("FKCOLUMN_NAME"),
                        "pk_table": rs.getString("PKTABLE_NAME"),
                        "pk_column": rs.getString("PKCOLUMN_NAME")
                    })
                
                self._last_used = time.time()
                return {
                    "table_name": table_name,
                    "schema": schema,
                    "columns": columns,
                    "primary_keys": pk_columns,
                    "foreign_keys": foreign_keys
                }
            except Exception as e:
                last_error = e
                retries += 1
                
                if "connection" in str(e).lower() or "network" in str(e).lower():
                    logger.warning(f"Connection error while getting columns: {str(e)}")
                    self._connection = None
                    if retries < self.MAX_RETRIES:
                        logger.info(f"Retrying get_columns in {self.RETRY_DELAY} seconds...")
                        time.sleep(self.RETRY_DELAY)
                        continue
                else:
                    logger.error(f"Failed to get columns: {str(e)}")
                    raise JdbcError(f"Failed to get columns: {str(e)}")
            finally:
                if 'cursor' in locals():
                    cursor.close()
        
        logger.error(f"Failed to get columns after {self.MAX_RETRIES} attempts. Last error: {str(last_error)}")
        raise JdbcError(f"Failed to get columns after {self.MAX_RETRIES} attempts: {str(last_error)}")

# MCP handlers
async def execute_query(arguments: Dict[str, Any]) -> bytes:
    """Handle execute_query requests."""
    try:
        args = QueryArgs(**arguments)
        config = JdbcConfig()
        client = JdbcClient(config)
        
        result = client.execute_query(args.query, args.max_rows)
        return json.dumps(result).encode()
    except Exception as e:
        return json.dumps({"error": str(e)}).encode()
    finally:
        if 'client' in locals():
            client.close()

async def get_tables(arguments: Dict[str, Any]) -> bytes:
    """Handle get_tables requests."""
    try:
        args = GetTablesArgs(**arguments)
        config = JdbcConfig()
        client = JdbcClient(config)
        
        result = client.get_tables(args.schema, args.include_system)
        return json.dumps(result).encode()
    except Exception as e:
        return json.dumps({"error": str(e)}).encode()
    finally:
        if 'client' in locals():
            client.close()

async def get_columns(arguments: Dict[str, Any]) -> bytes:
    """Handle get_columns requests."""
    try:
        args = GetColumnsArgs(**arguments)
        config = JdbcConfig()
        client = JdbcClient(config)
        
        result = client.get_columns(args.table_name, args.schema)
        return json.dumps(result).encode()
    except Exception as e:
        return json.dumps({"error": str(e)}).encode()
    finally:
        if 'client' in locals():
            client.close()

@app.command()
def main(
    transport: Transport = typer.Option(Transport.stdio, help="Transport to use"),
    host: str = typer.Option("127.0.0.1", help="Host to listen on"),
    port: int = typer.Option(8000, help="Port to listen on"),
):
    """Run the JDBC MCP server."""
    mcp = FastMCP()
    
    mcp.add_tool(
        execute_query,
        name="execute_query",
        description="""Execute a SELECT query.

Required parameters:
- query: SQL SELECT query to execute

Optional parameters:
- max_rows: Maximum number of rows to return (default: 100, max: 1000)

Example:
{
    "query": "SELECT * FROM users WHERE active = true",
    "max_rows": 50
}
"""
    )
    
    mcp.add_tool(
        get_tables,
        name="get_tables",
        description="""List tables in the database.

Optional parameters:
- schema: Schema name to list tables from (if None, uses default schema)
- include_system: Whether to include system tables (default: false)

Example:
{
    "schema": "public",
    "include_system": false
}
"""
    )
    
    mcp.add_tool(
        get_columns,
        name="get_columns",
        description="""Get column information for a table.

Required parameters:
- table_name: Table name to get columns from

Optional parameters:
- schema: Schema name (if None, uses default schema)

Example:
{
    "table_name": "users",
    "schema": "public"
}
"""
    )
    
    # Run server
    if transport == Transport.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", host=host, port=port)

if __name__ == "__main__":
    app() 