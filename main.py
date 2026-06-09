# ## Here we are creating a simple MCP remote server. 
# For demo purposes we will create a simple server that has two tools - one for adding two numbers and another for generating a random number. We will also add a resource that provides information about the server. Finally, we will run the server using HTTP transport so that it can be accessed remotely.

# from fastmcp import FastMCP
# import random, json

# # Creating MCP server instance
# mcp = FastMCP(name="Simple Calculation Server")

# ## Adding tools to the server

# # This is a simple addition tool that takes two integers and returns their sum. The @mcp.tool() decorator registers this function as a tool that can be called remotely by clients connected to the MCP server.
# @mcp.tool()
# def add(a: int, b: int) -> int:
#     """Add two numbers together"""
#     return a + b


# # Adding another tool to the server, this is to generate a ranodm number
# @mcp.tool()
# def random_number(min: int=1, max: int=100) -> int:
#     """Generate a random number between min and max"""
#     return random.randint(min, max)


# ## Adding a resource that tells us about the server information
# @mcp.resource("info://server")
# def server_info():
#     """Return information about the server"""
#     info = {
#         "name": mcp.name,
#         "version": mcp.version,
#         "description": "A basic MCP remote server with math tools.",
#         "tools": ['add', 'random_number'],
#         "authors": "SK",
#     }
#     return json.dumps(info, indent=2)


# ## Starting the server
# if __name__ == "__main__":
#     # The main change we get to see when comparing with local server is in the below line
#     # mcp.run()  # This is what we used in local server. If by default understands that we are making the transport through stdio

#     # This is the mostimportant change that we have to make in order to make a remote server. Above remaining code is same as local server. We just have to change the way we run the server. Instead of using mcp.run() which is for local server, we use mcp.run(transport="http", host="0.0.0.0", port=8000) for remote server. This tells the MCP server to use HTTP as the transport protocol and listen on all available network interfaces (0.0.0.0) on port 8000 for incoming requests.
#     mcp.run(transport="http", host="0.0.0.0", port=8000)  # This is what we use for remote server. We specify the transport as http and provide host and port information. This will start the MCP server and listen for incoming HTTP requests on the specified host and port.


# ## To run this server : fast mcp run main.py --transport http --host 0.0.0.0 --port 8000
# #  If the above command is hard to remember then we can use : uv run main.py

# # To run the server in development mode inspector tool, we can use the following command:
# # # set MCP_AUTO_OPEN_ENABLED=false  (Set this environment variable to prevent the browser from automatically opening (whch gives dev error) when the server starts)
# # # uv run fastmcp dev inspector main.py  (To run the inspector tool, which allows you to test the tools and see the interactions in a web interface)

# ## Now in the inspector tool - 
#     # Keep transport type as Stremable HTTP
#     # URL as http://127.0.0.1:8000/mcp
#     # Connection type as Via Proxy
#     # And then connect. You should see the connection established in the inspector tool and you can start testing the tools we have created (add and random_number) by sending requests to the server through the inspector interface.









## Here we have used the same expense tracker server code that we had in the local server, but have made few changes to make it work as a remote server. 
# Also we have made it to asynchronous using aiosqlite to handle database operations asynchronously which is more suitable for a remote server handling multiple requests concurrently. The main change is in the way we run the server at the end of the code, where we specify the transport as HTTP and provide host and port information to listen for incoming requests.
# Like in local server its okay we do not add async functionality as we are the only one user accessing the server, but in remote server we can have multiple users accessing the server concurrently, so it is better to use async functionality to handle multiple requests efficiently without blocking the server.

from fastmcp import FastMCP
import os
import aiosqlite  # Changed: sqlite3 → aiosqlite
import tempfile
# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

def init_db():  # Keep as sync for initialization
    try:
        # Use synchronous sqlite3 just for initialization
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database synchronously at module load
init_db()

@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):  # Changed: added async
    '''Add a new expense entry to the database.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:  # Changed: added async
            cur = await c.execute(  # Changed: added await
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            await c.commit()  # Changed: added await
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except Exception as e:  # Changed: simplified exception handling
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status": "error", "message": f"Database error: {str(e)}"}
    
@mcp.tool()
async def list_expenses(start_date, end_date):  # Changed: added async
    '''List expense entries within an inclusive date range.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:  # Changed: added async
            cur = await c.execute(  # Changed: added await
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]  # Changed: added await
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}

@mcp.tool()
async def summarize(start_date, end_date, category=None):  # Changed: added async
    '''Summarize expenses by category within an inclusive date range.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:  # Changed: added async
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await c.execute(query, params)  # Changed: added await
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]  # Changed: added await
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}

@mcp.resource("expense:///categories", mime_type="application/json")  # Changed: expense:// → expense:///
def categories():
    try:
        # Provide default categories if file doesn't exist
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }
        
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()