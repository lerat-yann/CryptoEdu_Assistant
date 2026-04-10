from dotenv import load_dotenv
load_dotenv()

from integrations.composio_google import get_mcp_url

url = get_mcp_url("yayahoo06200@gmail.com")
print("URL MCP :", url)