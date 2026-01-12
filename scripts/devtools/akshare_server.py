"""
Akshare MCP Server Wrapper

Wraps Akshare functionality as an MCP server to provide Chinese market data
where OpenBB has limited coverage.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AkshareServer:
    """Akshare MCP 服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 3001):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.running = False
    
    async def start_server(self):
        """启动 MCP 服务器"""
        logger.info(f"Starting Akshare MCP server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("Akshare MCP server started successfully")
            self.running = True
            await asyncio.Future()  # Run forever
    
    async def stop_server(self):
        """停止服务器"""
        self.running = False
        for client in self.clients:
            await client.close()
        self.clients.clear()
        logger.info("Akshare MCP server stopped")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    request = json.loads(message)
                    response = await self.process_request(request)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await self.send_error(websocket, -32700, "Parse error")
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    await self.send_error(websocket, -32603, f"Internal error: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        # JSON-RPC 2.0 响应格式
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id")
        }
        
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "tools/list":
                result = await self.list_tools()
            elif method == "tools/call":
                result = await self.call_tool(params.get("name"), params.get("arguments", {}))
            elif method == "initialize":
                result = {"status": "ready", "server": "akshare-mcp"}
            else:
                raise ValueError(f"Unknown method: {method}")
            
            response["result"] = result
            
        except Exception as e:
            response["error"] = {
                "code": -32602,
                "message": str(e)
            }
        
        return response
    
    async def send_error(self, websocket: WebSocketServerProtocol, code: int, message: str):
        """发送错误响应"""
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None
        }
        await websocket.send(json.dumps(error_response))
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具"""
        return [
            {
                "name": "china_stock_price",
                "description": "Get Chinese stock price data (A-shares, Hong Kong, US)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol (e.g., 000001 for SZSE, 600000 for SSE)"},
                        "period": {"type": "string", "description": "Period: daily, weekly, monthly", "default": "daily"},
                        "start_date": {"type": "string", "description": "Start date in YYYYMMDD format"},
                        "end_date": {"type": "string", "description": "End date in YYYYMMDD format"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "china_fundamentals",
                "description": "Get Chinese company fundamental data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"},
                        "report_type": {"type": "string", "description": "Report type: profit, balance, cash", "default": "profit"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "china_macro",
                "description": "Get Chinese macro economic data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "indicator": {"type": "string", "description": "Indicator name (e.g., GDP, CPI, PMI)"},
                        "period": {"type": "string", "description": "Period: monthly, quarterly, yearly", "default": "monthly"}
                    },
                    "required": ["indicator"]
                }
            },
            {
                "name": "china_news",
                "description": "Get Chinese financial news",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "News source: sina, eastmoney, hexun", "default": "sina"},
                        "limit": {"type": "integer", "description": "Number of news items", "default": 20}
                    },
                    "required": []
                }
            },
            {
                "name": "china_stock_info",
                "description": "Get Chinese stock basic information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"}
                    },
                    "required": ["symbol"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用具体工具"""
        try:
            if tool_name == "china_stock_price":
                return await self.get_china_stock_price(**arguments)
            elif tool_name == "china_fundamentals":
                return await self.get_china_fundamentals(**arguments)
            elif tool_name == "china_macro":
                return await self.get_china_macro(**arguments)
            elif tool_name == "china_news":
                return await self.get_china_news(**arguments)
            elif tool_name == "china_stock_info":
                return await self.get_china_stock_info(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    async def get_china_stock_price(self, symbol: str, period: str = "daily", 
                                  start_date: Optional[str] = None, 
                                  end_date: Optional[str] = None) -> Dict[str, Any]:
        """获取中国股票价格"""
        try:
            # 判断市场类型
            if symbol.startswith("6"):
                # 上海证券交易所
                df = ak.stock_zh_a_hist(symbol=symbol, period=period, 
                                      start_date=start_date, end_date=end_date)
            elif symbol.startswith("0") or symbol.startswith("3"):
                # 深圳证券交易所
                df = ak.stock_zh_a_hist(symbol=symbol, period=period,
                                      start_date=start_date, end_date=end_date)
            elif symbol.startswith("00") and len(symbol) == 5:
                # 港股
                df = ak.stock_hk_hist(symbol=symbol, period=period,
                                    start_date=start_date, end_date=end_date)
            else:
                # 默认处理
                df = ak.stock_zh_a_hist(symbol=symbol, period=period,
                                      start_date=start_date, end_date=end_date)
            
            # 转换为标准格式
            if not df.empty:
                result = {
                    "symbol": symbol,
                    "data": df.to_dict('records'),
                    "columns": df.columns.tolist(),
                    "count": len(df)
                }
            else:
                result = {
                    "symbol": symbol,
                    "data": [],
                    "columns": df.columns.tolist() if hasattr(df, 'columns') else [],
                    "count": 0,
                    "message": "No data found"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting stock price for {symbol}: {e}")
            raise
    
    async def get_china_fundamentals(self, symbol: str, report_type: str = "profit") -> Dict[str, Any]:
        """获取中国股票基本面数据"""
        try:
            if report_type == "profit":
                df = ak.stock_financial_analysis_indicator(symbol=symbol)
            elif report_type == "balance":
                df = ak.stock_balance_sheet_by_reportly(symbol=symbol)
            elif report_type == "cash":
                df = ak.stock_cash_flow_by_reportly(symbol=symbol)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            if not df.empty:
                # 取最新的财务数据
                if 'report_date' in df.columns:
                    df = df.sort_values('report_date', ascending=False)
                
                result = {
                    "symbol": symbol,
                    "report_type": report_type,
                    "data": df.head(10).to_dict('records'),  # 返回最近10期
                    "columns": df.columns.tolist(),
                    "count": len(df)
                }
            else:
                result = {
                    "symbol": symbol,
                    "report_type": report_type,
                    "data": [],
                    "columns": [],
                    "count": 0,
                    "message": "No fundamental data found"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {symbol}: {e}")
            raise
    
    async def get_china_macro(self, indicator: str, period: str = "monthly") -> Dict[str, Any]:
        """获取中国宏观经济数据"""
        try:
            # 根据指标类型调用不同的 akshare 函数
            if indicator.upper() == "GDP":
                df = ak.macro_china_gdp()
            elif indicator.upper() == "CPI":
                df = ak.macro_china_cpi()
            elif indicator.upper() == "PMI":
                df = ak.macro_china_pmi()
            elif indicator.upper() == "M2":
                df = ak.macro_china_m2()
            else:
                # 尝试使用通用函数
                df = getattr(ak, f"macro_china_{indicator.lower()}", None)
                if df is None or not callable(df):
                    raise ValueError(f"Unknown indicator: {indicator}")
                df = df()
            
            if not df.empty:
                result = {
                    "indicator": indicator,
                    "period": period,
                    "data": df.to_dict('records'),
                    "columns": df.columns.tolist(),
                    "count": len(df)
                }
            else:
                result = {
                    "indicator": indicator,
                    "period": period,
                    "data": [],
                    "columns": [],
                    "count": 0,
                    "message": "No macro data found"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting macro data for {indicator}: {e}")
            raise
    
    async def get_china_news(self, source: str = "sina", limit: int = 20) -> Dict[str, Any]:
        """获取中国财经新闻"""
        try:
            if source == "sina":
                df = ak.stock_news_em()
            elif source == "eastmoney":
                df = ak.stock_news_jr()
            elif source == "hexun":
                df = ak.stock_news_ths()
            else:
                raise ValueError(f"Unknown news source: {source}")
            
            if not df.empty:
                # 限制返回数量
                news_data = df.head(limit).to_dict('records')
                result = {
                    "source": source,
                    "data": news_data,
                    "count": len(news_data)
                }
            else:
                result = {
                    "source": source,
                    "data": [],
                    "count": 0,
                    "message": "No news found"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting news from {source}: {e}")
            raise
    
    async def get_china_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取中国股票基本信息"""
        try:
            # 获取股票基本信息
            info = ak.stock_individual_info_em(symbol=symbol)
            
            if not info.empty:
                # 转换为字典格式
                info_dict = dict(zip(info['item'], info['value']))
                
                result = {
                    "symbol": symbol,
                    "info": info_dict,
                    "name": info_dict.get('股票简称', ''),
                    "industry": info_dict.get('所属行业', ''),
                    "market": info_dict.get('所属板块', ''),
                    "listing_date": info_dict.get('上市时间', '')
                }
            else:
                result = {
                    "symbol": symbol,
                    "info": {},
                    "message": "No stock info found"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")
            raise


# 启动 Akshare MCP 服务器的便捷函数
async def start_akshare_server(host: str = "localhost", port: int = 3001):
    """启动 Akshare MCP 服务器"""
    server = AkshareServer(host, port)
    await server.start_server()


if __name__ == "__main__":
    # 直接运行时启动服务器
    asyncio.run(start_akshare_server())
