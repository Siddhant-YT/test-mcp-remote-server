## Here we are creating a simple MCP remote server.

from fastmcp import FastMCP
import random, json

# Creating MCP server instance
mcp = FastMCP(name="Simple Calculation Server")

## Adding tools to the server

# This is a simple addition tool that takes two integers and returns their sum. The @mcp.tool() decorator registers this function as a tool that can be called remotely by clients connected to the MCP server.
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


# Adding another tool to the server, this is to generate a ranodm number
@mcp.tool()
def random_number(min: int=1, max: int=100) -> int:
    """Generate a random number between min and max"""
    return random.randint(min, max)


## Adding a resource that tells us about the server information
@mcp.resource("info://server")
def server_info():
    """Return information about the server"""
    info = {
        "name": mcp.name,
        "version": mcp.version,
        "description": "A basic MCP remote server with math tools.",
        "tools": ['add', 'random_number'],
        "authors": "SK",
    }
    return json.dumps(info, indent=2)


## Starting the server
if __name__ == "__main__":
    # The main change we get to see when comparing with local server is in the below line
    # mcp.run()  # This is what we used in local server. If by default understands that we are making the transport through stdio

    # This is the mostimportant change that we have to make in order to make a remote server. Above remaining code is same as local server. We just have to change the way we run the server. Instead of using mcp.run() which is for local server, we use mcp.run(transport="http", host="0.0.0.0", port=8000) for remote server. This tells the MCP server to use HTTP as the transport protocol and listen on all available network interfaces (0.0.0.0) on port 8000 for incoming requests.
    mcp.run(transport="http", host="0.0.0.0", port=8000)  # This is what we use for remote server. We specify the transport as http and provide host and port information. This will start the MCP server and listen for incoming HTTP requests on the specified host and port.


## To run this server : fast mcp run main.py --transport http --host 0.0.0.0 --port 8000
#  If the above command is hard to remember then we can use : uv run main.py

# To run the server in development mode inspector tool, we can use the following command:
# # set MCP_AUTO_OPEN_ENABLED=false  (Set this environment variable to prevent the browser from automatically opening (whch gives dev error) when the server starts)
# # uv run fastmcp dev inspector main.py  (To run the inspector tool, which allows you to test the tools and see the interactions in a web interface)

## Now in the inspector tool - 
    # Keep transport type as Stremable HTTP
    # URL as http://127.0.0.1:8000/mcp
    # Connection type as Via Proxy
    # And then connect. You should see the connection established in the inspector tool and you can start testing the tools we have created (add and random_number) by sending requests to the server through the inspector interface.
    