from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def hello():
    return "hello"

if __name__ == "__main__":
    print("starting...")
    mcp.run(transport="stdio")
