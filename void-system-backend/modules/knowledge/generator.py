"""Grounded generation adapter for the Knowledge Engine."""
from __future__ import annotations

from typing import Optional

from core.runtime_settings import RuntimeSettings


class LangChainGroundedGenerator:
    """Generate only from evidence selected by Knowledge Engine retrieval.

    Inputs: question plus already-reviewed evidence text. Output: model answer.
    Called by: GroundedKnowledgeResponder. It deliberately has no vector store,
    document parser, or conversation-history access.
    """

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from services.ai_services.llm_factory import get_chat_llm

        prompt = ChatPromptTemplate.from_template("""你是个人知识工作区的回答助手。请严格依据证据回答，不得补造事实。

规则：
1. 对关键结论使用 [S1]、[S2] 形式标注证据。
2. 证据不足时明确说明缺少什么，不要用常识填空。
3. 合并重复信息，指出证据间的冲突或不确定性。
4. 先给直接结论，再给必要说明，语言自然清晰。

证据：
{evidence}

问题：{question}
""")
        self._chain = prompt | get_chat_llm(temperature=0.2, settings=settings) | StrOutputParser()

    async def generate(self, question: str, evidence: str) -> str:
        return str(await self._chain.ainvoke({"question": question, "evidence": evidence}))
