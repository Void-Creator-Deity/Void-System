"""

Void System - Persona Chain (System AI Assistant)

-------------------------------------------------

系统精灵对话链，支持多轮对话、会话历史管理，以及可选的多模态（图片）输入。

"""

from langchain_community.chat_message_histories import ChatMessageHistory

from langchain_core.chat_history import BaseChatMessageHistory

from langchain_core.messages import AIMessage, SystemMessage

from langchain_core.output_parsers import StrOutputParser

from langchain_core.prompts import ChatPromptTemplate

from langchain_core.runnables import RunnableLambda

from langchain_core.runnables.config import RunnableConfig

from langchain_core.runnables.history import RunnableWithMessageHistory

from typing import Any, AsyncIterator, Dict, List, Optional



from services.ai_services.llm_factory import get_chat_llm

from services.ai_services.vision_messages import human_message_with_text_and_images

import uuid



# 存储会话历史（生产环境建议使用 Redis）

_store: Dict[str, ChatMessageHistory] = {}





def get_history(session_id: str) -> BaseChatMessageHistory:

    if session_id not in _store:

        _store[session_id] = ChatMessageHistory()

    return _store[session_id]





SYSTEM_PERSONA = (

    "你是系统精灵「VOID AI」，语气冷静、逻辑清晰、表达克制。"

    "你将根据用户的输入（可含图片）与历史对话，提供精准、可执行的回答。"
    "优先给出结论与下一步建议，不输出夸张叙事。"

)





def _extract_session_id(input_data: Dict[str, Any]) -> str:

    session_id: Optional[str] = None

    if isinstance(input_data, dict):

        if "session_id" in input_data:

            session_id = str(input_data["session_id"])

        elif "config" in input_data and isinstance(input_data["config"], dict):

            input_config = input_data["config"]

            if "configurable" in input_config and isinstance(input_config["configurable"], dict):

                session_id = input_config["configurable"].get("session_id")

    if session_id is None:

        session_id = f"default-{uuid.uuid4().hex[:8]}"

    return session_id





def _has_multimodal_input(input_data: Dict[str, Any]) -> bool:

    images = input_data.get("images") or []

    return bool(images)





async def _stream_multimodal(

    input_data: Dict[str, Any], config: RunnableConfig

) -> AsyncIterator[Any]:

    """带图片时走原生 message 流，不经过纯文本模板链。"""

    llm = get_chat_llm(temperature=0.5)

    session_id = _extract_session_id(input_data)

    history = get_history(session_id)

    text = (input_data.get("text") or "").strip() or "请根据图片作答。"

    images: List[str] = list(input_data.get("images") or [])



    user_msg = human_message_with_text_and_images(text, images)

    messages = [SystemMessage(content=SYSTEM_PERSONA)]

    for m in history.messages[-40:]:

        messages.append(m)

    messages.append(user_msg)



    full = ""

    async for chunk in llm.astream(messages):

        piece = ""

        if hasattr(chunk, "content") and chunk.content:

            c = chunk.content

            if isinstance(c, str):

                piece = c

            elif isinstance(c, list):

                for block in c:

                    if isinstance(block, dict) and block.get("type") == "text":

                        piece += block.get("text", "")

        if piece:

            full += piece

            yield piece



    history.add_message(user_msg)

    if full:

        history.add_message(AIMessage(content=full))





async def _stream_text_chain(

    base_chain: Any, input_data: Dict[str, Any], config: RunnableConfig

) -> AsyncIterator[Any]:

    """无图片时沿用 RunnableWithMessageHistory + 模板链。"""

    async for chunk in base_chain.astream(input_data, config=config):

        yield chunk





def load_persona_chain() -> RunnableLambda[Dict[str, Any], Any]:

    llm = get_chat_llm(temperature=0.5)

    prompt = ChatPromptTemplate.from_template(

        """

    你是系统精灵「VOID AI」，语气冷静、逻辑清晰、表达克制。
    你将根据用户输入与历史对话提供精准、可执行的回答。
    回答时优先给结论，再给必要解释与下一步建议。

    用户输入：{text}

    历史对话：{history}

    请以系统精灵的身份，提供专业、准确的回答。

    """

    )

    chain = prompt | llm | StrOutputParser()

    base_chain = RunnableWithMessageHistory(

        chain,

        get_history,

        input_messages_key="text",

        history_messages_key="history",

    )



    async def ensure_session_stream(

        input_data: Dict[str, Any], config_node: Optional[RunnableConfig] = None

    ):

        session_id = _extract_session_id(input_data)

        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}

        if _has_multimodal_input(input_data):

            async for chunk in _stream_multimodal(input_data, cfg):

                yield chunk

        else:

            async for chunk in _stream_text_chain(base_chain, input_data, cfg):

                yield chunk



    return RunnableLambda(ensure_session_stream)

