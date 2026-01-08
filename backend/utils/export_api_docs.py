#!/usr/bin/env python3
"""
FastAPI API 文档导出工具
支持导出为 Markdown、HTML、JSON 等格式
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    print("需要安装 requests 库: pip install requests")
    sys.exit(1)


class APIDocExporter:
    """API 文档导出器"""
    
    def __init__(self, base_url: str = "http://0.0.0.0:3000"):
        self.base_url = base_url.rstrip('/')
        self.openapi_url = f"{self.base_url}/openapi.json"
    
    def fetch_openapi_spec(self) -> Dict[str, Any]:
        """从服务器获取 OpenAPI 规范"""
        try:
            response = requests.get(self.openapi_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器 {self.openapi_url}")
            print(f"   错误: {e}")
            print(f"\n💡 请确保服务器正在运行:")
            print(f"   python main.py")
            sys.exit(1)
    
    def export_json(self, output_path: str, spec: Dict[str, Any]):
        """导出为 JSON 格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON 文档已导出: {output_path}")
    
    def export_markdown(self, output_path: str, spec: Dict[str, Any]):
        """导出为 Markdown 格式"""
        md_lines = []
        
        # 标题和元信息
        info = spec.get('info', {})
        md_lines.append(f"# {info.get('title', 'API 文档')}")
        md_lines.append("")
        if info.get('description'):
            md_lines.append(info['description'])
            md_lines.append("")
        md_lines.append(f"**版本**: {info.get('version', 'N/A')}")
        md_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # 服务器信息
        servers = spec.get('servers', [])
        if servers:
            md_lines.append("## 服务器地址")
            for server in servers:
                md_lines.append(f"- {server.get('url', '')}")
                if server.get('description'):
                    md_lines.append(f"  - {server['description']}")
            md_lines.append("")
        
        # 路径和端点
        paths = spec.get('paths', {})
        if paths:
            md_lines.append("## API 端点")
            md_lines.append("")
            
            # 按路径分组
            for path, methods in sorted(paths.items()):
                md_lines.append(f"### {path}")
                md_lines.append("")
                
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        md_lines.append(f"#### `{method.upper()}` {path}")
                        md_lines.append("")
                        
                        # 描述
                        if details.get('summary'):
                            md_lines.append(f"**{details['summary']}**")
                            md_lines.append("")
                        
                        if details.get('description'):
                            md_lines.append(details['description'])
                            md_lines.append("")
                        
                        # 参数
                        parameters = details.get('parameters', [])
                        if parameters:
                            md_lines.append("**请求参数:**")
                            md_lines.append("")
                            md_lines.append("| 参数名 | 位置 | 类型 | 必填 | 描述 |")
                            md_lines.append("|--------|------|------|------|------|")
                            for param in parameters:
                                param_schema = param.get('schema', {})
                                param_type = param_schema.get('type', 'string')
                                if param_schema.get('format'):
                                    param_type = f"{param_type} ({param_schema['format']})"
                                required = "✅" if param.get('required', False) else "❌"
                                md_lines.append(
                                    f"| `{param.get('name', '')}` | "
                                    f"{param.get('in', '')} | "
                                    f"{param_type} | "
                                    f"{required} | "
                                    f"{param.get('description', '')} |"
                                )
                            md_lines.append("")
                        
                        # 请求体
                        request_body = details.get('requestBody')
                        if request_body:
                            md_lines.append("**请求体:**")
                            md_lines.append("")
                            content = request_body.get('content', {})
                            for content_type, schema_info in content.items():
                                md_lines.append(f"Content-Type: `{content_type}`")
                                md_lines.append("")
                                schema = schema_info.get('schema', {})
                                if schema.get('$ref'):
                                    md_lines.append(f"Schema: {schema['$ref']}")
                                else:
                                    md_lines.append("```json")
                                    md_lines.append(self._format_schema_example(schema))
                                    md_lines.append("```")
                                md_lines.append("")
                        
                        # 响应
                        responses = details.get('responses', {})
                        if responses:
                            md_lines.append("**响应:**")
                            md_lines.append("")
                            for status_code, response_info in sorted(responses.items()):
                                md_lines.append(f"**{status_code}** - {response_info.get('description', '')}")
                                md_lines.append("")
                                content = response_info.get('content', {})
                                if content:
                                    for content_type, schema_info in content.items():
                                        schema = schema_info.get('schema', {})
                                        md_lines.append("```json")
                                        md_lines.append(self._format_schema_example(schema))
                                        md_lines.append("```")
                                        md_lines.append("")
                        
                        md_lines.append("---")
                        md_lines.append("")
        
        # 数据模型
        components = spec.get('components', {})
        schemas = components.get('schemas', {})
        if schemas:
            md_lines.append("## 数据模型")
            md_lines.append("")
            for schema_name, schema_def in sorted(schemas.items()):
                md_lines.append(f"### {schema_name}")
                md_lines.append("")
                if schema_def.get('description'):
                    md_lines.append(schema_def['description'])
                    md_lines.append("")
                
                properties = schema_def.get('properties', {})
                if properties:
                    md_lines.append("| 字段名 | 类型 | 必填 | 描述 |")
                    md_lines.append("|--------|------|------|------|")
                    required_fields = schema_def.get('required', [])
                    for prop_name, prop_def in sorted(properties.items()):
                        prop_type = prop_def.get('type', 'string')
                        if prop_def.get('format'):
                            prop_type = f"{prop_type} ({prop_def['format']})"
                        if prop_def.get('items'):
                            prop_type = f"array[{prop_def['items'].get('type', 'object')}]"
                        required = "✅" if prop_name in required_fields else "❌"
                        md_lines.append(
                            f"| `{prop_name}` | {prop_type} | {required} | "
                            f"{prop_def.get('description', '')} |"
                        )
                    md_lines.append("")
                md_lines.append("---")
                md_lines.append("")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        print(f"✅ Markdown 文档已导出: {output_path}")
    
    def _format_schema_example(self, schema: Dict[str, Any]) -> str:
        """格式化 schema 为示例 JSON"""
        if schema.get('$ref'):
            return f"// 引用: {schema['$ref']}"
        
        example = {}
        properties = schema.get('properties', {})
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get('type', 'string')
            if prop_type == 'string':
                example[prop_name] = prop_def.get('example', 'string')
            elif prop_type == 'integer':
                example[prop_name] = prop_def.get('example', 0)
            elif prop_type == 'number':
                example[prop_name] = prop_def.get('example', 0.0)
            elif prop_type == 'boolean':
                example[prop_name] = prop_def.get('example', False)
            elif prop_type == 'array':
                example[prop_name] = []
            else:
                example[prop_name] = {}
        
        return json.dumps(example, indent=2, ensure_ascii=False)
    
    def export_html(self, output_path: str, spec: Dict[str, Any]):
        """导出为 HTML 格式（使用 ReDoc）"""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{spec.get('info', {}).get('title', 'API 文档')}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.css">
</head>
<body>
    <redoc spec-url="{self.openapi_url}"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML 文档已导出: {output_path}")
        print(f"   注意: HTML 文件需要服务器运行才能显示完整内容")
    
    def export(self, output_dir: str = "docs", formats: list = None):
        """导出文档"""
        if formats is None:
            formats = ['markdown', 'json']
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 获取 OpenAPI 规范
        print(f"📡 正在从 {self.base_url} 获取 API 文档...")
        spec = self.fetch_openapi_spec()
        
        # 导出各种格式
        if 'json' in formats:
            self.export_json(
                str(output_path / 'api-docs.json'),
                spec
            )
        
        if 'markdown' in formats:
            self.export_markdown(
                str(output_path / 'api-docs.md'),
                spec
            )
        
        if 'html' in formats:
            self.export_html(
                str(output_path / 'api-docs.html'),
                spec
            )
        
        print(f"\n✨ 文档导出完成！")
        print(f"   输出目录: {output_path.absolute()}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='FastAPI API 文档导出工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导出 Markdown 和 JSON
  python export_api_docs.py
  
  # 导出所有格式
  python export_api_docs.py --format markdown --format json --format html
  
  # 指定服务器地址
  python export_api_docs.py --url http://localhost:3000
  
  # 指定输出目录
  python export_api_docs.py --output ./api-documentation
        """
    )
    
    parser.add_argument(
        '--url',
        default='http://0.0.0.0:3000',
        help='API 服务器地址 (默认: http://0.0.0.0:3000)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='docs',
        help='输出目录 (默认: docs)'
    )
    
    parser.add_argument(
        '--format', '-f',
        action='append',
        choices=['markdown', 'json', 'html'],
        default=['markdown', 'json'],
        help='导出格式 (可多次指定，默认: markdown, json)'
    )
    
    args = parser.parse_args()
    
    exporter = APIDocExporter(args.url)
    exporter.export(args.output, args.format)


if __name__ == '__main__':
    main()

