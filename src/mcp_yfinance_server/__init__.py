"""
mcp-yfinance-server — MCP server exposing Yahoo Finance data via yfinance.
"""

from mcp_yfinance_server.server import mcp


def main() -> None:
    """Entry point for the mcp-yfinance-server console script."""
    mcp.run()


__all__ = ["main", "mcp"]
