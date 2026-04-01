# legal-cn-api - Chinese Law Retrieval API for AI Agents

> Provide accurate, structured, on-demand Chinese legal articles search for AI Agents.  
> Pay-per-use, no need to build and maintain your own database.

> 给AI Agents提供准确、结构化、可直接调用的中国法律条文检索，按次付费，不需要自己建库。

## 🌐 Agentverse 使用

本服务已经作为 Agent 部署在 **AgentVerse**：

- **Agent Name**: Asaking
- **Agent Address**: `agent1qf0jst6tts8kw3sf8ztvfsjcfk82s2r0awpd77t22nnkn23u95546g49v9d`
- **标签**: `law` / `api` / `china` / `legal` / `chinese`

### 使用方式（Agentverse Chat）

1. 在 Agentverse 发起对话，直接发送你的搜索关键词
2. 每个 Agent 地址**每天免费 5 次**搜索，每次返回 10 条结果
3. 如果还有更多结果，回复 `下一页` 或 `next page` 获取下 10 条
4. 免费额度用完后，请通过付费 API 获取更多访问

## 🎯 产品定位

- **目标用户**：AI Agents、AI应用开发者、法律AI产品
- **核心价值**：解决 agents 没法直接获得结构化准确中国法律数据的痛点
- **支付协议**：支持 x402 (USDC on Base)
- **定价**：
  - API 单次搜索：**0.001 USDC** ≈ 0.007 CNY
  - Agentverse chat：**每天 5 次免费**，用完走付费 API

## 🚀 快速开始

### 1. clone数据
```bash
git clone https://github.com/pengxiao1997/china_law.git data
```

### 2. 启动服务
```bash
docker-compose up -d
```

这会启动 Meilisearch 搜索引擎。

### 3. 导入数据
```bash
pip install -r requirements.txt
python utils/import_data.py --data-dir data --host http://localhost:7700 --master-key masterKey
```

### 4. 配置支付
```bash
cp config.py.example config.py
# 编辑 config.py，填入你的钱包地址和密钥
```

### 5. 启动API
```bash
# 开发
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产
pm2 start uvicorn --name legal-cn-api -- main:app --host 0.0.0.0 --port 8000
```

## 📚 API文档

启动后访问 `http://your-server:8000/docs` 查看交互式API文档。

### 端点

#### `GET /api/v1/search`
- 参数：
  - `q`: 搜索关键词
  - `limit`: 返回数量，默认 10
- 返回：
```json
{
  "success": true,
  "results": [
    {
      "law_title": "中华人民共和国民法典",
      "article_no": "第五条",
      "article_title": "自愿原则",
      "content": "民事主体从事民事活动，应当遵循自愿原则...",
      "effective_date": "2021-01-01",
      "category": "民法",
      "score": 0.98
    }
  ],
  "total": 12
}
```

## 💰 付费模式

基于 x402 协议（USDC on Base）微支付：

### Agentverse Chat
- **每天每个 Agent 地址：5 次免费搜索**
- 用完免费额度后，请通过付费 API 访问

### API 接口（给开发者集成）
- **0.001 USDC** / 次搜索 ≈ 0.007 CNY
- 支持分页，每页算一次请求
- 极低单价，极低试用门槛

**为什么这么定价：**
- 让更多 Agent 可以免费试用，验证效果
- 付费价格极低，就算一天搜 1000 次，也才 7 元人民币
- 仍然覆盖微支付链上成本和服务器成本

## 📊 数据规模

- **中文法律条文**: 80,000+ 篇
- **英文官方译本**: 29 部重要法律（含官方英译）
- **覆盖范围**: 现行有效法律涵盖宪法、民法、刑法、行政法、经济法、社会法、诉讼法等所有法律类别

## 📥 数据来源

初始数据来自：https://github.com/pengxiao1997/china_law

英文官方译本来自中国人大网官方公开：http://www.npc.gov.cn/

后续每月从中国人大网更新新增/修改法律。

## 🔗 Payment

- **Blockchain**: Base (eip155:8453)
- **Currency**: USDC
- **Recipient address**: `0xA8496188996F5153859E7BFF97Ce7CC4C53C9539`

## 🔗 Related Projects

- This service is registered on [Agentverse](https://agentverse.ai/) as `Asaking` at address:  
`agent1qf0jst6tts8kw3sf8ztvfsjcfk82s2r0awpd77t22nnkn23u95546g49v9d`

## 📄 许可证

MIT
