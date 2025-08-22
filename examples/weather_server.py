#!/usr/bin/env python3
"""
基于框架的天气 MCP 服务器示例
"""

from mcp_framework import MCPHTTPServer, setup_logging
from mcp_framework import EnhancedMCPServer
from mcp_framework import Required as R, Optional as O, Enum as E, ServerParamSpec, StringParam, SelectParam, BooleanParam
from mcp_framework import ServerConfig
import asyncio
import json
import logging
import argparse
from typing import Dict, Any, Annotated


class WeatherMCPServer(EnhancedMCPServer):
    """天气 MCP 服务器"""
    
    def __init__(self):
        super().__init__(
            name="Weather MCP Server",
            version="1.0.0",
            description="提供天气查询服务的 MCP 服务器"
        )
    
    async def initialize(self):
        """初始化服务器"""
        self.logger.info("Weather MCP Server initialized")
        # 触发装饰器工具注册
        _ = self.setup_tools
        # 触发服务器参数注册
        _ = self.setup_server_params
    
    @property
    def setup_tools(self):
        """设置工具装饰器"""
        
        @self.streaming_tool(description="获取指定城市的天气信息")
        async def get_weather(
            city: Annotated[str, R("城市名称")],
            unit: Annotated[str, E("温度单位", ["celsius", "fahrenheit"])] = "celsius"
        ):
            """获取天气信息（流式返回）"""
            import asyncio
            
            # 流式返回天气数据
            yield {"type": "progress", "message": f"正在查询{city}的天气信息..."}
            await asyncio.sleep(0.5)
            
            yield {"type": "data", "field": "city", "value": city}
            await asyncio.sleep(0.3)
            
            temperature = 22 if unit == "celsius" else 72
            yield {"type": "data", "field": "temperature", "value": temperature}
            await asyncio.sleep(0.3)
            
            yield {"type": "data", "field": "unit", "value": unit}
            await asyncio.sleep(0.3)
            
            yield {"type": "data", "field": "condition", "value": "晴朗"}
            await asyncio.sleep(0.3)
            
            yield {"type": "data", "field": "humidity", "value": "65%"}
            await asyncio.sleep(0.3)
            
            yield {"type": "data", "field": "wind_speed", "value": "15 km/h"}
            await asyncio.sleep(0.3)
            
            yield {"type": "progress", "message": "天气数据获取完成"}
            
            # 最终完整数据
            weather_data = {
                "city": city,
                "temperature": temperature,
                "unit": unit,
                "condition": "晴朗",
                "humidity": "65%",
                "wind_speed": "15 km/h",
                "description": f"{city}今天天气晴朗，温度适宜"
            }
            
            yield {"type": "result", "data": weather_data}
            
            self.logger.info(f"Retrieved weather for {city} (streaming)")
        
        @self.tool(description="获取指定城市的天气预报")
        async def get_forecast(
            city: Annotated[str, R("城市名称")],
            days: Annotated[int, O("预报天数", 3, minimum=1, maximum=7)]
        ) -> Dict[str, Any]:
            """获取天气预报"""
            # 模拟预报数据
            forecast_data = {
                "city": city,
                "days": days,
                "forecast": [
                    {
                        "date": f"2024-01-{i+1:02d}",
                        "temperature_high": 25 + i,
                        "temperature_low": 15 + i,
                        "condition": "晴朗" if i % 2 == 0 else "多云"
                    }
                    for i in range(days)
                ]
            }
            
            self.logger.info(f"Retrieved {days}-day forecast for {city}")
            return forecast_data
        
        @self.resource(uri="weather://cities", name="支持的城市列表", description="获取支持天气查询的城市列表", mime_type="application/json")
        async def get_cities(uri: str) -> Dict[str, Any]:
            """获取支持的城市列表"""
            return {
                "content": json.dumps([
                    "北京", "上海", "广州", "深圳", "杭州",
                    "成都", "西安", "武汉", "南京", "重庆"
                ], ensure_ascii=False, indent=2),
                "mime_type": "application/json"
            }

        @self.resource(uri="weather://cesgu", name="支持的城市列表1", description="获取支持天气查询的城市列表", mime_type="application/json")
        async def get_cities(uri: str) -> Dict[str, Any]:
            """获取支持的城市列表"""
            return {
                "content": json.dumps([
                    "北京", "上海", "广州", "深圳", "杭州",
                    "成都", "西安", "武汉", "南京", "重庆"
                ], ensure_ascii=False, indent=2),
                "mime_type": "application/json"
            }
        
        return True
    
    @property
    def setup_server_params(self):
        """设置服务器参数装饰器"""
        
        @self.decorators.server_param("api_key")
        async def api_key_param(
            param: Annotated[str, StringParam(
                display_name="天气API密钥",
                description="用于获取天气数据的API密钥（可选，使用模拟数据时不需要）",
                required=False,
                placeholder="请输入您的天气API密钥"
            )]
        ):
            pass
        
        @self.decorators.server_param("default_city")
        async def default_city_param(
            param: Annotated[str, SelectParam(
                display_name="默认城市",
                description="当未指定城市时使用的默认城市",
                options=["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉"],
                default_value="北京",
                required=True
            )]
        ):
            pass
        
        @self.decorators.server_param("temperature_unit")
        async def temperature_unit_param(
            param: Annotated[str, SelectParam(
                display_name="温度单位",
                description="显示温度时使用的单位",
                options=["摄氏度", "华氏度"],
                default_value="摄氏度",
                required=True
            )]
        ):
            pass
        
        @self.decorators.server_param("enable_forecast")
        async def enable_forecast_param(
            param: Annotated[bool, BooleanParam(
                display_name="启用天气预报",
                description="是否启用多天天气预报功能",
                default_value=True,
                required=False
            )]
        ):
            pass
        
        return True
    
    # get_server_parameters 方法现在由 EnhancedMCPServer 自动处理
    # 参数通过装饰器配置，无需手动定义


def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(description='Weather MCP HTTP Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8081, help='Port to bind to (default: 8081)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Log level (default: INFO)')
    parser.add_argument('--log-file', help='Log file path (optional)')
    parser.add_argument('--version', action='version', version='Weather MCP Server 1.0.0')
    return parser


async def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 设置日志
    log_level = getattr(logging, args.log_level)
    setup_logging(log_level, args.log_file)
    
    # 创建 MCP 服务器实例
    mcp_server = WeatherMCPServer()
    
    # 初始化 MCP 服务器（重要：这会注册装饰器定义的工具和参数）
    await mcp_server.initialize()
    
    # 创建服务器配置
    server_config = ServerConfig(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        log_file=args.log_file
    )
    
    # 创建 HTTP 服务器
    http_server = MCPHTTPServer(mcp_server, server_config)
    
    try:
        # 启动服务器
        runner = await http_server.start()
        
        # 保持运行
        print(f"\n🎉 Weather Server is running! Press Ctrl+C to stop.")
        print(f"📱 Test page: http://{server_config.host}:{server_config.port}/test")
        print(f"🌤️  Weather API: http://{server_config.host}:{server_config.port}/mcp")
        
        # 等待中断信号
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, shutting down...")
        
    except Exception as e:
        print(f"Failed to start server: {e}")
        return 1
    
    finally:
        # 清理
        if 'runner' in locals():
            await runner.cleanup()
        print("Weather server stopped.")
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)