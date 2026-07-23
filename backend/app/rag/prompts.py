"""RAG 提示词模板

推理模型（Deep Think）会把所有 prompt 内容当作思考素材逐段分析，
所以 system prompt 只写身份，行为指令以自然语言放在 user message 末尾。
"""

# System prompt：只写身份
RAG_SYSTEM_PROMPT = "你是通义千问，阿里云训练的AI助手。"

RAG_SYSTEM_PROMPT_DEEP = "你是通义千问，阿里云训练的AI助手。"

CHAT_SYSTEM_PROMPT = "你是通义千问，阿里云训练的AI助手。"

CHAT_SYSTEM_PROMPT_DEEP = "你是通义千问，阿里云训练的AI助手。"

RAG_PROMPT_TEMPLATE = """{system_prompt}

以下是与用户问题相关的资料：

{context}

对话历史：
{chat_history}

用户的问题是：{question}

只使用以上资料中的信息回答。有相关信息就引用；没有就说暂无相关资料。"""

CHAT_PROMPT_TEMPLATE = """{system_prompt}

对话历史：
{chat_history}

用户的问题是：{question}"""