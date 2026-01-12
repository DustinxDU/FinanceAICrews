# MCP服务器工具使用与调用说明文档

## 1. 项目概述

本文档详细记录了FinanceAICrews项目中三个MCP服务器的测试过程、使用方法和最佳实践。三个MCP服务器分别提供不同市场的金融数据服务：

- **OpenBB MCP Server**: 提供美股、全球指数、外汇和大宗商品数据
- **Akshare MCP Server**: 提供中国A股、港股市场数据及宏观经济数据
- **YFinance MCP Server**: 提供美股和全球市场的详细金融数据

## 2. 测试环境配置

### 2.1 Docker容器配置

所有MCP服务器均通过Docker容器运行，确保环境隔离和依赖一致性。以下是各服务器的Docker配置信息：

**OpenBB MCP Server**
- 端口: 8008
- Dockerfile路径: /home/dustin/stock/FinanceAICrews/docker/mcp/openbb/Dockerfile
- 依赖文件: requirements.txt

**Akshare MCP Server**
- 端口: 8010
- Dockerfile路径: /home/dustin/stock/FinanceAICrews/docker/mcp/akshare/Dockerfile
- 核心依赖: akshare, pandas, mcp, starlette
- 服务器实现: server.py (SSE传输协议)

**YFinance MCP Server**
- 端口: 8009
- Dockerfile路径: /home/dustin/stock/FinanceAICrews/docker/mcp/yfinance/Dockerfile
- 核心依赖: yfinance, pandas, mcp, starlette
- 服务器实现: server.py (SSE传输协议)

### 2.2 传输协议

所有MCP服务器均采用SSE (Server-Sent Events) 传输协议,这是MCP规范的推荐传输方式。SSE协议允许服务器向客户端推送实时数据,特别适合金融数据这种需要持续更新的场景。

## 3. 测试方法论

### 3.1 测试流程

测试遵循以下标准流程:

1. **服务器状态检查**: 验证MCP服务器是否正常运行
2. **工具列表获取**: 获取服务器提供的所有可用工具
3. **单个工具测试**: 对每个工具进行功能验证
4. **集成测试**: 测试多个工具的协同工作能力
5. **性能测试**: 评估响应时间和数据吞吐量

### 3.2 测试工具

测试使用了Python的requests库进行HTTP请求,测试脚本位于:
- /home/dustin/stock/FinanceAICrews/tests/test_openbb_yfinance.py
- /home/dustin/stock/FinanceAICrews/tests/test_mcp_connection.py

## 4. OpenBB MCP服务器测试

### 4.1 服务器端点

OpenBB MCP服务器提供以下REST API端点:

- **GET /mcp/**: 服务器健康检查
- **GET /mcp/tools**: 获取可用工具列表
- **GET /mcp/quote**: 获取股票/指数报价数据

### 4.2 测试用例

**测试用例1: 服务器状态检查**

```python
def check_server_status(self):
    """检查 OpenBB MCP 服务器状态"""
    try:
        response = requests.get(f"{self.base_url}/mcp/", timeout=10)
        if response.status_code == 200:
            self.log_test("服务器状态检查", "SUCCESS", "OpenBB MCP 服务器运行正常")
            return True
        else:
            self.log_test("服务器状态检查", "FAILED", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        self.log_test("服务器状态检查", "ERROR", f"连接失败: {str(e)}")
        return False
```

**测试用例2: 美股数据获取**

```python
def test_stock_data(self, symbol="AAPL"):
    """测试美股数据获取"""
    try:
        response = requests.get(
            f"{self.base_url}/mcp/quote",
            params={"symbol": symbol},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "error" not in data:
                self.log_test(f"美股数据 ({symbol})", "SUCCESS", "成功获取股票数据")
                return True
            else:
                self.log_test(f"美股数据 ({symbol})", "FAILED", f"API错误: {data.get('error')}")
                return False
        else:
            self.log_test(f"美股数据 ({symbol})", "FAILED", f"HTTP {response.status_code}")
            return False
    except Exception as e:
        self.log_test(f"美股数据 ({symbol})", "ERROR", f"请求失败: {str(e)}")
        return False
```

**测试用例3: 指数数据获取**

```python
def test_index_data(self, symbol="^GSPC"):
    """测试指数数据获取 (S&P 500)"""
```

**测试用例4: 汇率数据获取**

```python
def test_fx_data(self, symbol="USDCNY=X"):
    """测试汇率数据获取 (USD/CNY)"""
```

**测试用例5: 大宗商品期货数据获取**

```python
def test_commodity_data(self, symbol="GC=F"):
    """测试大宗商品期货数据获取 (黄金)"""
```

### 4.3 预期响应格式

成功的API调用将返回以下格式的JSON响应:

```json
{
    "symbol": "AAPL",
    "data": [
        {
            "日期": "2024-01-02",
            "开盘": 185.56,
            "收盘": 186.19,
            "最高": 187.48,
            "最低": 185.30,
            "成交量": 45678900,
            "成交额": 8512345678
        }
    ],
    "count": 1
}
```

## 5. Akshare MCP服务器测试

### 5.1 服务器架构

Akshare MCP服务器采用标准MCP协议实现,主要组件包括:

- **AkshareClient**: 直接访问Akshare库的客户端
- **DataCache**: 内存TTL缓存,支持按数据类型设置不同过期时间
- **RateLimiter**: 滑动窗口速率限制器,默认每分钟60次请求
- **SseServerTransport**: SSE传输层

### 5.2 核心工具列表

Akshare服务器提供超过100个工具,按功能分类如下:

**股票价格数据工具 (10个)**
- stock_zh_a_hist: A股历史行情
- stock_zh_a_spot_em: A股实时行情
- stock_zh_a_minute: A股分钟级行情
- stock_hk_hist: 港股历史行情
- stock_hk_spot_em: 港股实时行情
- stock_us_hist: 美股历史行情
- stock_us_spot_em: 美股实时行情
- stock_individual_info_em: 个股基本信息
- stock_zh_a_hist_pre_min_em: 盘前分时数据
- stock_bid_ask_em: 买卖盘口数据

**财务报表工具 (8个)**
- stock_profit_sheet_by_report_em: 利润表
- stock_balance_sheet_by_report_em: 资产负债表
- stock_cash_flow_sheet_by_report_em: 现金流量表
- stock_financial_analysis_indicator: 财务分析指标
- stock_yjbb_em: 业绩报表
- stock_yjyg_em: 业绩预告
- stock_yjkb_em: 业绩快报
- stock_fhps_em: 分红配送

**估值指标工具 (8个)**
- stock_a_ttm_lyr: PE/PB估值数据
- stock_a_all_pb: 市净率数据
- stock_a_high_low_statistics: 创新高新低统计
- stock_a_below_net_asset_statistics: 破净股统计

### 5.3 缓存配置

Akshare服务器支持灵活的缓存策略:

```python
@dataclass
class AkshareConfig:
    """Akshare MCP server configuration."""
    enable_caching: bool = True
    cache_ttl_default: int = 300  # 默认5分钟
    
    cache_ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "stock_price": 60,          # 股票价格缓存1分钟
        "fundamentals": 3600,       # 财务数据缓存1小时
        "financial_statements": 86400,  # 财务报表缓存1天
        "macro_data": 86400,        # 宏观数据缓存1天
        "news": 300,                # 新闻缓存5分钟
        "hk_stock": 60,             # 港股缓存1分钟
    })
```

### 5.4 数据获取示例

**A股历史行情数据**

```python
async def get_stock_price(
    self,
    symbol: str,
    period: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq",
) -> Dict[str, Any]:
    """获取中国A股股票价格数据。"""
    def _fetch():
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date or "",
                end_date=end_date or "",
                adjust=adjust,
            )
            if not df.empty:
                return df_to_dict(df, symbol=symbol)
        except Exception as e:
            logger.warning(f"Akshare fetch failed for {symbol}: {e}")
        
        # 降级方案: 直接调用东方财富API
        import requests
        market = "1" if symbol.startswith("6") else "0"
        secid = f"{market}.{symbol}"
        # ... API调用逻辑
```

### 5.5 降级机制

当Akshare库无法获取数据时,服务器会自动降级到东方财富API:

```python
# 直接调用东方财富API
url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
params = {
    "secid": secid,
    "fields1": "f1,f2,f3,f4,f5,f6",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    "klt": klt,
    "fqt": fqt,
    "beg": start_date.replace("-", "") if start_date else "0",
    "end": end_date.replace("-", "") if end_date else "20500101",
}
```

## 6. YFinance MCP服务器测试

### 6.1 服务器架构

YFinance MCP服务器提供美股和全球市场数据,主要特点:

- 完整的yfinance库功能封装
- 高级财务指标和统计数据分析
- 选项链数据支持
- 加密货币数据支持
- 行业和板块表现数据

### 6.2 核心工具分类

**股票价格工具**
- stock_history: 历史价格数据
- stock_info: 基本信息
- stock_actions: 分红和拆股
- stock_dividends: 股息历史
- stock_splits: 股票拆分

**财务分析工具**
- stock_financials: 财务报表
- stock_holders: 股东信息
- stock_recommendations: 分析师推荐
- stock_calendar: 收益日历
- stock_earnings: 收益历史

**市场数据工具**
- market_summary: 市场概况
- sector_performance: 行业表现
- trending_tickers: 热门股票

**衍生品工具**
- options_chain: 期权链数据
- crypto_history: 加密货币历史

### 6.3 缓存策略

```python
@dataclass
class YFinanceConfig:
    """YFinance MCP server configuration."""
    enable_caching: bool = True
    cache_ttl_default: int = 300
    rate_limit_per_minute: int = 120  # YFinance限制更宽松
    
    cache_ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "stock_price": 60,
        "fundamentals": 3600,
        "financial_statements": 86400,
        "options": 300,
        "crypto": 60,
        "news": 300,
        "info": 3600,
    })
```

### 6.4 高级数据分析

**关键统计指标获取**

```python
async def get_key_stats(self, symbol: str) -> Dict[str, Any]:
    """获取股票的关键统计指标。"""
    def _fetch():
        ticker = yf.Ticker(symbol)
        info = ticker.info
        stats = {
            "symbol": symbol,
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "profit_margin": info.get("profitMargins"),
            "return_on_assets": info.get("returnOnAssets"),
            "return_on_equity": info.get("returnOnEquity"),
            "beta": info.get("beta"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
        }
        return stats
    return await asyncio.to_thread(_fetch)
```

**市场概况获取**

```python
async def get_market_summary(self) -> Dict[str, Any]:
    """获取主要指数的市场概况。"""
    def _fetch():
        indices = ["^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX"]
        results = []
        for idx in indices:
            try:
                ticker = yf.Ticker(idx)
                info = ticker.info
                results.append({
                    "symbol": idx,
                    "name": info.get("shortName", idx),
                    "price": info.get("regularMarketPrice"),
                    "change": info.get("regularMarketChange"),
                    "change_percent": info.get("regularMarketChangePercent"),
                })
            except Exception as e:
                logger.warning(f"Failed to get {idx}: {e}")
        return {"indices": results, "count": len(results)}
    return await asyncio.to_thread(_fetch)
```

## 7. 集成测试

### 7.1 测试场景

**场景1: 多数据源交叉验证**

使用OpenBB和YFinance同时获取同一股票数据,验证数据一致性:

```python
def test_data_consistency(self):
    """测试不同数据源的数据一致性。"""
    symbol = "AAPL"
    
    # 通过OpenBB获取
    openbb_data = self.get_openbb_data(symbol)
    
    # 通过YFinance获取
    yfinance_data = self.get_yfinance_data(symbol)
    
    # 比较关键指标
    openbb_price = openbb_data.get("price")
    yfinance_price = yfinance_data.get("price")
    
    tolerance = 0.02  # 2%容差
    if abs(openbb_price - yfinance_price) / openbb_price < tolerance:
        return True
    return False
```

**场景2: 数据时效性测试**

评估各数据源的更新频率和延迟:

```python
def test_data_freshness(self):
    """测试数据时效性。"""
    test_cases = [
        ("AAPL", "美股"),
        ("600519", "A股"),
        ("USDCNY=X", "汇率"),
        ("GC=F", "黄金"),
    ]
    
    results = []
    for symbol, market in test_cases:
        start_time = time.time()
        data = self.get_market_data(symbol)
        latency = time.time() - start_time
        
        results.append({
            "market": market,
            "symbol": symbol,
            "latency": latency,
            "data_timestamp": data.get("timestamp"),
        })
    
    return results
```

### 7.2 性能测试

**响应时间测试**

```python
def benchmark_api_performance(self):
    """API响应时间基准测试。"""
    endpoints = [
        ("/mcp/quote", {"symbol": "AAPL"}),
        ("/mcp/quote", {"symbol": "600519"}),
        ("/mcp/history", {"symbol": "MSFT", "period": "1mo"}),
    ]
    
    results = []
    for endpoint, params in endpoints:
        latencies = []
        for _ in range(10):  # 多次测试取平均
            start = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            latencies.append(time.time() - start)
        
        results.append({
            "endpoint": endpoint,
            "avg_latency": sum(latencies) / len(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
        })
    
    return results
```

## 8. 故障排除指南

### 8.1 常见问题

**问题1: 连接超时**

```
错误信息: requests.exceptions.ConnectionError
解决步骤:
1. 检查Docker容器是否运行: docker ps
2. 检查端口是否正确: netstat -tlnp | grep 8008
3. 检查防火墙设置
4. 查看容器日志: docker logs <container_id>
```

**问题2: 数据获取失败**

```
错误信息: {"error": "No data found"}
可能原因:
1. 股票代码格式错误
2. 数据源暂时不可用
3. 请求频率超过限制
解决步骤:
1. 验证股票代码格式
2. 检查网络连接
3. 实现重试机制
4. 添加降级数据源
```

**问题3: 缓存未更新**

```
错误信息: 返回过期数据
解决步骤:
1. 手动清除缓存: cache.clear()
2. 检查缓存TTL配置
3. 强制刷新: 设置cache_bust参数
```

### 8.2 日志查看

**查看OpenBB服务器日志**

```bash
docker logs openbb-mcp-server --tail 100 -f
```

**查看Akshare服务器日志**

```bash
docker logs akshare-mcp-server --tail 100 -f
```

**查看YFinance服务器日志**

```bash
docker logs yfinance-mcp-server --tail 100 -f
```

## 9. 最佳实践

### 9.1 错误处理

实现健壮的错误处理机制:

```python
def safe_api_call(func, max_retries=3):
    """安全的API调用,带重试机制。"""
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"API call failed after {max_retries} attempts: {e}")
                raise
            time.sleep(2 ** attempt)  # 指数退避
```

### 9.2 速率限制

根据不同数据源调整速率限制:

```python
# Akshare: 较严格,每分钟60次
rate_limiter_akshare = RateLimiter(limit_per_minute=60)

# YFinance: 较宽松,每分钟120次
rate_limiter_yfinance = RateLimiter(limit_per_minute=120)
```

### 9.3 数据验证

实现数据验证确保数据质量:

```python
def validate_stock_data(data: Dict) -> bool:
    """验证股票数据的完整性和有效性。"""
    required_fields = ["symbol", "open", "high", "low", "close", "volume"]
    
    if not all(field in data for field in required_fields):
        return False
    
    # 验证价格逻辑
    if data["high"] < data["low"]:
        return False
    
    # 验证成交量
    if data["volume"] < 0:
        return False
    
    return True
```

## 10. 结论与建议

### 10.1 测试结果总结

经过全面测试,三个MCP服务器均能正常运行:

- **OpenBB MCP Server**: 提供稳定的美股和全球市场数据访问
- **Akshare MCP Server**: 提供完整的A股和港股数据,具有降级机制
- **YFinance MCP Server**: 提供丰富的美股基本面数据和衍生品信息

### 10.2 优化建议

1. **增加监控**: 部署Prometheus指标收集,实时监控服务器状态
2. **负载均衡**: 对高频率访问的工具实现负载均衡
3. **数据持久化**: 考虑将高频访问数据持久化到数据库
4. **API网关**: 部署统一的API网关,提供认证和限流功能

### 10.3 未来工作

1. 实现自动化测试套件,集成到CI/CD流程
2. 添加更多数据源的MCP服务器
3. 实现跨数据源的数据标准化层
4. 开发Web管理界面,便于监控和配置

---

**文档版本**: 1.0  
**最后更新**: 2024年  
**维护者**: FinanceAICrews Team
