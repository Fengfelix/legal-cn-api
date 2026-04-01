"""
legal-cn-api - 中国法律条文检索付费API
Author: Felix Feng + Asaking
License: MIT
"""

import os
from typing import cast

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from meilisearch import Client
from pydantic import BaseModel
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
)
from uagents_core.envelope import Envelope
from uagents_core.identity import Identity
from uagents_core.utils.messages import parse_envelope, send_message_to_agent

import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agentverse Identity setup
# Generate a stable identity from a seed phrase
AGENT_SEED_PHRASE = os.environ.get("AGENT_SEED_PHRASE", "legal-cn-api-seed-phrase-for-felix")
AGENT_EXTERNAL_ENDPOINT = os.environ.get("AGENT_EXTERNAL_ENDPOINT", "http://101.32.245.66:8000")

identity = Identity.from_seed(AGENT_SEED_PHRASE, 0)
agent_name = "Legal CN API"
agent_readme = """# Legal CN API

Chinese law retrieval API with 80,000+ legal articles in Chinese and 29 important laws in official English translation.

## Features

- 80,000+ Chinese legal articles
- 29 important laws in English (official translations)
- Bilingual search (Chinese/English/mixed)
- x402 micro-payments ready (0.001 USDC per request)
- Agentverse Chat Protocol compatible

## Usage

Send a chat message with your search query, get matching legal articles.

**Price**: 0.001 USDC per search on Base network.
"""

logger.info(f"✅ Agent identity created: {identity.address}")

# Meilisearch client
meili = Client(config.MEILISEARCH_HOST, config.MEILISEARCH_MASTER_KEY)
INDEX_NAME = "legal_cn"
index = meili.index(INDEX_NAME)

app = FastAPI(
    title="legal-cn-api",
    description="中国法律条文检索付费API (x402微支付) - Agentverse Chat Protocol compatible",
    version="1.0.0",
)

class SearchResponse(BaseModel):
    success: bool
    results: list
    total: int

class SearchResult(BaseModel):
    law_title: str
    article_no: str
    article_title: str
    content: str
    effective_date: str
    category: str
    score: float

# 限流 - 每分钟请求限制
from collections import defaultdict
from datetime import datetime, timedelta
request_counts = defaultdict(list)

def check_rate_limit(client_ip: str) -> bool:
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    # 清理旧请求
    request_counts[client_ip] = [t for t in request_counts[client_ip] if t > minute_ago]
    request_counts[client_ip].append(now)
    return len(request_counts[client_ip]) <= config.MAX_REQUESTS_PER_MINUTE

# 每日免费额度 - 每个sender地址每天免费N次
from datetime import date
daily_free_counts = defaultdict(int)
FREE_REQUESTS_PER_DAY = 5  # 每天免费5次请求

def check_and_increment_free_quota(sender: str) -> bool:
    """检查是否还有免费额度，如果有则消耗一个并返回True"""
    today = date.today()
    # 重置日期（新的一天）
    # 这里简化处理，每天启动自动清空，内存存储
    # 如果需要持久化可以存数据库，但早期阶段没必要
    if str(sender) not in daily_free_counts:
        daily_free_counts[sender] = 0
    
    if daily_free_counts[sender] >= FREE_REQUESTS_PER_DAY:
        return False  # 额度用完
    
    daily_free_counts[sender] += 1
    return True

def get_remaining_free_quota(sender: str) -> int:
    """获取剩余免费额度"""
    today = date.today()
    if str(sender) not in daily_free_counts:
        return FREE_REQUESTS_PER_DAY
    return max(0, FREE_REQUESTS_PER_DAY - daily_free_counts[sender])

# 分页状态记录 - 记录每个sender最近一次搜索的offset
# 这样用户说"下一页"就能继续翻页
last_search_state = {}  # key: sender, value: (last_query, last_offset)

# Base mainnet constants
BASE_CHAIN_ID = 8453
# USDC on Base
USDC_ADDRESS = "0x833589fCD6eDb6AD44080C48D3068386FBDC3170"

# ====== x402 支付验证 ======
# Use official FastAPI middleware integration with error handling wrapper
from x402.http.middleware.fastapi import payment_middleware_from_config
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from eth_account import Account
from web3 import Web3
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

x402_enabled = False
if config.X402_ENABLED and config.X402_WALLET_PRIVATE_KEY:
    try:
        # Create local account from private key
        account = Account.from_key(config.X402_WALLET_PRIVATE_KEY)
        # Verify address matches
        derived_address = account.address
        expected_recipient = Web3.to_checksum_address(config.X402_WALLET_ADDRESS)
        if derived_address.lower() != expected_recipient.lower():
            logger.error(f"❌ Address mismatch: derived {derived_address} != configured {expected_recipient}")
            raise ValueError("Private key does not match configured address")
        
        # Create the exact mechanism instance
        mechanism = ExactEvmScheme()
        
        # Configure route - all search and detail endpoints require payment
        # /chat is FREE for Agentverse testing and preview
        # Full results via /api/v1/search still require payment
        price_decimal = float(config.PRICE_PER_REQUEST) / 1e6
        routes_config = {
            "GET /api/v1/search": {
                "accepts": [
                    {
                        "scheme": "exact",
                        "payTo": derived_address,
                        "price": str(price_decimal),
                        "network": "eip155:8453",
                    }
                ]
            },
            "GET /api/v1/law/*": {
                "accepts": [
                    {
                        "scheme": "exact",
                        "payTo": derived_address,
                        "price": str(price_decimal),
                        "network": "eip155:8453",
                    }
                ]
            }
            # POST /chat is FREE for Agentverse testing and preview
            # Users get preview results directly, full API access requires payment
        }
        
        # Schemes - list of dicts with 'network' and 'server'
        schemes = [
            {
                "network": "eip155:8453",
                "server": mechanism
            }
        ]
        
        # Get the original middleware
        original_middleware = payment_middleware_from_config(
            routes=routes_config,
            schemes=schemes
        )
        
        # Wrap it with proper error handling - any exception from middleware that indicates
        # payment required gets converted to proper 402 instead of 500
        class X402ErrorHandlingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await original_middleware(request, call_next)
                except Exception as e:
                    # Check if this is a payment required case
                    error_str = str(e).lower()
                    if ("payment" in error_str and "required" in error_str) or "402" in error_str:
                        # Return proper 402 Payment Required instead of 500
                        logger.info(f"💰 Payment required for {request.url.path} from {request.client.host if request.client else 'unknown'}")
                        return JSONResponse(
                            status_code=402,
                            content={
                                "success": False,
                                "error": "Payment Required",
                                "message": "This endpoint requires payment via x402 (USDC on Base)",
                                "payment_required": True,
                                "price": str(price_decimal),
                                "currency": "USDC",
                                "network": "Base (eip155:8453)",
                                "recipient": derived_address
                            }
                        )
                    # Other errors - log and return 500
                    logger.error(f"❌ x402 middleware error: {e}")
                    import traceback
                    traceback.print_exc()
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": "Internal Server Error during payment verification",
                            "message": str(e)
                        }
                    )
        
        # Add our wrapped middleware
        app.add_middleware(X402ErrorHandlingMiddleware)
        
        logger.info("✅ x402 payment verification enabled")
        logger.info(f"   Network: Base (eip155:8453)")
        logger.info(f"   Recipient: {derived_address}")
        logger.info(f"   Token: USDC 0x833589fCD6eDb6AD44080C48D3068386FBDC3170")
        logger.info(f"   Price per request: {price_decimal} USDC")
        x402_enabled = True
    except Exception as e:
        logger.error(f"❌ Failed to initialize x402: {e}")
        import traceback
        traceback.print_exc()
        x402_enabled = False
else:
    x402_enabled = False
    logger.info("⚠️ x402 payment disabled - running in open access mode")

@app.get("/api/v1/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, description="返回结果数量", ge=1, le=50),
    authorization: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
):
    # 限流检查
    client_ip = "127.0.0.1"  # TODO: get client ip from request
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
    
    # x402 middleware already handles payment verification
    # If we reach here, payment is verified or not required
    
    # 调试日志
    logger.info(f"Search query: q='{q}', limit={limit}, len(q)={len(q)}")
    
    # 搜索
    search_result = index.search(q, {"limit": limit})
    logger.info(f"✅ Search completed: q='{q}', estimatedTotalHits={search_result.get('estimatedTotalHits', 0)}, hits={len(search_result.get('hits', []))}")
    
    results = []
    for hit in search_result["hits"]:
        results.append(SearchResult(
            law_title=hit.get("law_title", ""),
            article_no=hit.get("article_no", ""),
            article_title=hit.get("article_title", ""),
            content=hit.get("content", ""),
            effective_date=hit.get("effective_date", ""),
            category=hit.get("category", ""),
            score=hit.get("_score", 0.0)
        ))
    
    return SearchResponse(
        success=True,
        results=results,
        total=search_result["estimatedTotalHits"]
    )

@app.get("/categories")
def get_categories():
    """获取所有法律分类，免费发现"""
    # 免费接口，不需要支付
    # 获取facet分布统计
    facet_result = index.search("", {
        "facets": ["category"],
        "limit": 1
    })
    
    categories = []
    if "facetDistribution" in facet_result and "category" in facet_result["facetDistribution"]:
        for category, count in facet_result["facetDistribution"]["category"].items():
            categories.append({
                "name": category,
                "count": count
            })
    
    # 按名称排序
    categories.sort(key=lambda x: x["name"])
    
    return {
        "success": True,
        "categories": categories,
        "total": len(categories)
    }

@app.get("/api/v1/law/{law_id}")
def get_law_article(
    law_id: str,
    authorization: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
):
    """获取单条法律条文的完整内容"""
    # 限流检查
    client_ip = "127.0.0.1"  # TODO: get client ip from request
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
    
    # x402 middleware already handles payment verification
    # If we reach here, payment is verified or not required
    
    # 按 id 查询
    search_result = index.search(f"id={law_id}", {"limit": 1})
    logger.info(f"✅ Get law article: id={law_id}, found={len(search_result['hits']) > 0}")
    
    if not search_result["hits"]:
        raise HTTPException(status_code=404, detail="Law article not found")
    
    return {
        "success": True,
        "result": search_result["hits"][0]
    }

@app.get("/health")
def health():
    """健康检查"""
    return {
        "status": "ok", 
        "service": "legal-cn-api",
        "x402_enabled": x402_enabled
    }

@app.get("/status")
async def healthcheck():
    """Agentverse 健康检查端点"""
    return {
        "status": "OK - Agent is running",
        "service": "legal-cn-api",
        "agent_address": str(identity.address),
        "endpoint": AGENT_EXTERNAL_ENDPOINT,
        "x402_enabled": x402_enabled
    }

# Chat Protocol endpoint for Agentverse compatibility (original simple version - keep for backward compatibility)
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat/simple")
async def chat_simple(request: ChatRequest):
    """
    Simple Chat endpoint for backward compatibility
    Accept natural language search query and return results as formatted text
    """
    query = request.message.strip()
    
    # If it starts with "搜索" or "search", extract the keyword
    if query.lower().startswith("search "):
        query = query[7:].strip()
    elif query.startswith("搜索 "):
        query = query[2:].strip()
    
    search_result = index.search(query, {"limit": 5})
    
    if not search_result["hits"]:
        return ChatResponse(response=f"未找到包含关键词 '{query}' 的法律条文，请尝试其他关键词。")
    
    # Format as markdown
    output = f"🔍 搜索关键词: **{query}**\n找到 {search_result['estimatedTotalHits']} 条结果，显示前 5 条:\n\n"
    
    for i, hit in enumerate(search_result["hits"], 1):
        output += f"**{i}. {hit['law_title']} - 第{hit['article_no']}条**\n"
        output += f"`{hit['category']}` • {hit['content'][:200]}...\n\n"
    
    output += f"\n💎 完整 API 调用获取更多结果: `GET /api/v1/search?q={query}` (0.001 USDC)"
    
    return ChatResponse(response=output)

# Agentverse Chat Protocol compliant endpoint
@app.post("/chat")
async def handle_message(env: Envelope):
    """
    Agentverse Chat Protocol (ACP) compliant endpoint
    Receives Envelope with ChatMessage, performs search, returns ChatMessage response
    
    Free quota: {FREE_REQUESTS_PER_DAY} requests per day per agent address
    Supports pagination: reply "next page", "more", "下一页", "继续" for next 10 results
    """
    msg = cast(ChatMessage, parse_envelope(env, ChatMessage))
    query_text = msg.text().strip()
    
    if not query_text:
        send_message_to_agent(
            destination=env.sender,
            msg=ChatMessage([TextContent("Error: Empty query received. Please provide a search term.")]),
            sender=identity,
        )
        return
    
    logger.info(f"Received chat query from {env.sender}: {query_text[:100]}")
    
    # 检查免费额度
    if not check_and_increment_free_quota(env.sender):
        # 免费额度用完，提示付费
        remaining = get_remaining_free_quota(env.sender)
        response_text = (
            f"⚠️ 您今日的免费额度已用完 ({FREE_REQUESTS_PER_DAY}/{FREE_REQUESTS_PER_DAY})\n\n"
            "要继续使用，请通过 x402 付费 API 调用：\n"
            "`GET https://your-domain/api/v1/search?q=关键词`\n"
            "价格：0.001 USDC 每次请求\n\n"
            "Agentverse 上付费功能即将上线，敬请期待！"
        )
        send_message_to_agent(
            destination=env.sender,
            msg=ChatMessage([TextContent(response_text)]),
            sender=identity,
        )
        logger.warning(f"Free quota exhausted for sender: {env.sender}")
        return
    
    # 处理分页 - 识别翻页指令
    sender_key = str(env.sender)
    query_lower = query_text.lower()
    is_pagination = any(cmd in query_lower for cmd in ["next page", "more", "下一页", "继续", "更多", "下一页"])
    
    if is_pagination and sender_key in last_search_state:
        # 继续上一次搜索的下一页
        last_query, last_offset = last_search_state[sender_key]
        offset = last_offset + 10  # 每次10条
        current_query = last_query
    else:
        # 新搜索
        offset = 0
        current_query = query_text
        # 如果是翻页指令但没有历史记录，当作新搜索处理
        if is_pagination:
            current_query = query_text.replace("next page", "").replace("more", "").replace("下一页", "").replace("继续", "").replace("更多", "").strip()
            if not current_query:
                send_message_to_agent(
                    destination=env.sender,
                    msg=ChatMessage([TextContent("⚠️ 没有找到上一次搜索记录，请直接输入搜索关键词。")]),
                    sender=identity,
                )
                return
    
    # 执行搜索 - 每次10条
    page_size = 10
    search_result = index.search(current_query.strip(), {"limit": page_size, "offset": offset})
    
    # 保存搜索状态用于翻页
    last_search_state[sender_key] = (current_query, offset)
    
    # Format response
    remaining = get_remaining_free_quota(env.sender)
    total = search_result["estimatedTotalHits"]
    start_num = offset + 1
    end_num = offset + len(search_result["hits"])
    
    if not search_result["hits"]:
        if offset > 0:
            response_text = f"📖 关键词 '{current_query}'\n已经没有更多结果了。总共找到 {total} 条结果。"
        else:
            response_text = f"未找到包含关键词 '{current_query}' 的法律条文，请尝试其他关键词。"
    else:
        response_text = f"🔍 搜索关键词: **{current_query}**\n"
        if total > page_size:
            response_text += f"找到 {total} 条结果，显示第 {start_num}-{end_num} 条:\n\n"
        else:
            response_text += f"找到 {total} 条结果:\n\n"
        
        for i, hit in enumerate(search_result["hits"], start_num):
            content_preview = hit['content'][:300] + "..." if len(hit['content']) > 300 else hit['content']
            response_text += f"**{i}. {hit['law_title']} - 第{hit['article_no']}条**\n"
            response_text += f"`{hit['category']}`\n{content_preview}\n\n"
        
        if end_num < total:
            response_text += f"📄 还有 {total - end_num} 条结果。回复「下一页」查看更多。\n"
        
        response_text += f"\n💡 今日剩余免费额度: {remaining} / {FREE_REQUESTS_PER_DAY}"
        if remaining > 0:
            response_text += " 次"
        else:
            response_text += " 次"
    
    # Send response back using Agentverse Chat Protocol
    send_message_to_agent(
        destination=env.sender,
        msg=ChatMessage([TextContent(response_text)]),
        sender=identity,
    )
    
    logger.info(f"Response sent for query: {current_query[:50]}... offset={offset} hits={len(search_result['hits'])}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
