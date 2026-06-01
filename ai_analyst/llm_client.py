"""
AI 分析引擎 - LLM 客户端封装
统一支持 OpenAI / Anthropic / 通义千问 / 文心一言
"""
import os
from typing import Optional, Literal
from loguru import logger

LLMProvider = Literal["openai", "anthropic", "qwen", "wenxin"]


class LLMClient:
    """统一 LLM 客户端"""

    def __init__(
        self,
        provider: LLMProvider = "openai",
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv(self._key_env(provider))
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._init_client()

    def _key_env(self, provider: LLMProvider) -> str:
        mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "qwen": "QWEN_API_KEY",
            "wenxin": "WENXIN_API_KEY",
        }
        return mapping[provider]

    def _init_client(self):
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        elif self.provider == "qwen":
            # 通义千问兼容 OpenAI 接口
            from openai import OpenAI
            base = self.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=base,
            )
        elif self.provider == "wenxin":
            # 文心一言使用独立 SDK
            try:
                from qianfan import ChatCompletion
                self.client = ChatCompletion()
                self._wenxin_ak = self.api_key
                self._wenxin_sk = os.getenv("WENXIN_SECRET_KEY", "")
            except ImportError:
                logger.warning("未安装 qianfan-sdk，文心一言不可用")
                self.client = None
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发起一次对话，返回模型回复文本"""
        if self.provider == "openai" or self.provider == "qwen":
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content

        elif self.provider == "anthropic":
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return resp.content[0].text

        elif self.provider == "wenxin":
            if self.client is None:
                raise RuntimeError("文心一言客户端未初始化，请安装 qianfan-sdk")
            resp = self.client.do(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                ak=self._wenxin_ak,
                sk=self._wenxin_sk,
            )
            return resp["result"]

        raise RuntimeError(f"未知 provider: {self.provider}")
