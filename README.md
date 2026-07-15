# 企业级 RAG 知识库问答系统

<div align="center">

**基于 LangChain + FastAPI 的全栈智能知识检索平台，融入 All-in-RAG 高级检索策略**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 项目简介

这是一个生产级的 RAG（Retrieval-Augmented Generation）知识库问答系统，支持用户上传文档（PDF/Word/Excel 等 8 种格式），通过自然语言提问获取带引用来源的智能回答。

**核心亮点**：融入 [All-in-RAG](https://github.com/datawhalechina/all-in-rag) 技术体系，实现了多查询分解、查询路由、父子文档检索等高级检索策略，显著提升检索质量和回答准确性。

---

## ✨ 核心功能

### 🎯 All-in-RAG 高级检索策略

#### 1. 多查询分解（Multi-Query Decomposition）
**参考**: All-in-RAG Chapter 4

将复合问题自动拆分为多个子问题，分别检索后合并结果。

**示例**：
- 用户问："iPhone 15 和 14 对比有什么提升？"
- 系统分解为：["iPhone 15 参数", "iPhone 14 参数", "iPhone 15 vs 14 对比"]
- 分别检索后合并去重，提升召回率

#### 2. 查询路由（Query Routing）
**参考**: All-in-RAG Chapter 4

根据问题类型自动选择最优检索策略：

| 问题类型 | 特征 | 检索策略 |
|---------|------|---------|
| 精确匹配 | 型号、人名、编号 | BM25 权重 0.8 |
| 语义搜索 | 概念、开放性问题 | 向量权重 0.8 |
| 对比分析 | "对比"、"区别"、"vs" | 均衡 0.5/0.5 |

#### 3. 父子文档检索（Parent Document Retriever）
**参考**: All-in-RAG C8 — Small-to-Big Retrieval

- **小块检索**（250 字符）：向量匹配更精确
- **大块生成**（1200 字符）：LLM 看到完整上下文，回答质量更高

**工作流程**：
```
用户上传文档 → 切分为父子块 → 子块存入向量库用于检索
                                    ↓
用户提问 → 检索命中子块 → 扩展为父块 → 喂给 LLM 生成回答
```

### 🔍 四级检索漏斗

```
用户提问
    ↓
[1] 智能查询改写（多查询分解 + 指代消解）
    ↓
[2] 混合检索（向量语义 + BM25 关键词 → 加权 RRF 融合）
    ↓
[3] LLM-as-Judge 相关性判断（过滤不相关文档）
    ↓
[4] Cross-Encoder 重排序（精排 Top-3）
    ↓
流式生成回答（带引用来源）
```

### 🛠️ 生产级特性

- ✅ **多格式文档支持**：PDF、Word、Excel、CSV、TXT、Markdown 等 8 种格式
- ✅ **流式输出**：SSE 实时推送回答，用户体验流畅
- ✅ **引用标注**：每个回答标注来源文档，支持点击预览
- ✅ **15 种大模型热切换**：运行时切换 LLM，无需重启
- ✅ **Embedding 版本校验**：防止换模型后向量不匹配
- ✅ **多层降级策略**：Cross-Encoder 不可用时自动 fallback
- ✅ **LLM 重试机制**：指数退避重试（最多 3 次）
- ✅ **流式错误恢复**：生成失败时友好提示
- ✅ **日志追踪**：loguru + request_id，线上问题可追溯
- ✅ **Rate Limiting**：登录 10/min，注册 5/min
- ✅ **BM25 持久化**：重启不用重建索引

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 登录注册 │  │ 对话界面 │  │ 管理后台 │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                            ↓
                    REST API (FastAPI)
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    后端 (Python)                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              RAG 检索管线                          │  │
│  │  查询改写 → 查询路由 → 混合检索 → Judge → Rerank  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ ChromaDB │  │  BM25    │  │ Reranker │              │
│  │ (向量库) │  │ (索引)   │  │ (精排)   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ SQLite   │  │ loguru   │  │  diskcache│             │
│  │ (元数据) │  │  (日志)  │  │  (缓存)  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                            ↓
              阿里云百炼 DashScope API
         (Qwen LLM + Text Embedding)
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 阿里云百炼 API Key（[申请地址](https://help.aliyun.com/zh/model-studio/get-api-key)）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/rag-knowledge-qa.git
cd rag-knowledge-qa
```

#### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY 和 JWT_SECRET_KEY
```

#### 3. 前端配置

```bash
cd ../frontend

# 安装依赖
npm install
```

#### 4. 启动服务

**方式一：一键启动（Windows）**

```bash
# 在项目根目录
scripts\start.bat
```

**方式二：手动启动**

```bash
# 终端 1：启动后端
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 2：启动前端
cd frontend
npm run dev
```

#### 5. 访问系统

- 前端界面：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs
- 默认管理员账号：`admin` / 启动时日志中显示的随机密码

---

## 📊 系统评估

使用 RAGAS 框架评估系统质量：

```bash
cd backend
python eval/evaluate.py
```

**评估指标**：
- **Faithfulness**（忠实度）：回答是否忠于检索文档
- **Answer Relevancy**（答案相关性）：回答是否切题
- **Context Precision**（上下文精确度）：检索文档中相关文档的占比
- **Context Recall**（上下文召回率）：应该召回的相关文档实际召回了多少

评估报告生成在 `backend/eval/evaluation_report.md`

---

## 📁 项目结构

```
LangChainRAG项目/
├── backend/
│   ├── app/
│   │   ├── auth/          # 认证模块（JWT + 用户管理）
│   │   ├── chat/          # 对话模块（会话 + 消息）
│   │   ├── kb/            # 知识库模块（文档管理）
│   │   │   ├── parent_splitter.py  # 父子文档分块
│   │   │   ├── splitter.py         # 通用分块
│   │   │   └── service.py          # 文档处理服务
│   │   ├── rag/           # RAG 检索模块
│   │   │   ├── query_rewriter.py   # 查询改写 + 多查询分解
│   │   │   ├── query_router.py     # 查询路由
│   │   │   ├── retriever.py        # 混合检索（RRF 融合）
│   │   │   ├── bm25_retriever.py   # BM25 关键词检索
│   │   │   ├── reranker.py         # Cross-Encoder 重排序
│   │   │   └── service.py          # RAG 服务（四级漏斗）
│   │   ├── admin/         # 管理后台模块
│   │   ├── logging.py     # 日志配置（loguru）
│   │   └── main.py        # FastAPI 入口
│   ├── eval/              # RAGAS 评估脚本
│   ├── requirements.txt   # Python 依赖
│   └── .env.example       # 环境变量模板
├── frontend/
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   ├── components/    # 通用组件
│   │   ├── stores/        # Zustand 状态管理
│   │   └── api/           # API 调用
│   ├── package.json       # Node.js 依赖
│   └── vite.config.ts     # Vite 配置
└── README.md
```

---

## 🔧 技术栈

| 层级 | 技术 |
|-----|------|
| 前端框架 | React 18 + TypeScript |
| UI 组件库 | Ant Design 5 |
| 状态管理 | Zustand |
| 后端框架 | FastAPI |
| AI 框架 | LangChain |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite + SQLAlchemy |
| LLM | 阿里云百炼（通义千问系列） |
| Embedding | DashScope Text Embedding |
| Reranker | BAAI/bge-reranker-large |
| 日志 | loguru |
| 评估 | RAGAS |

---

## 📝 使用示例

### 1. 上传文档

1. 登录管理后台（admin 账号）
2. 进入"知识库管理"页面
3. 上传 PDF/Word/Excel 等文档
4. 等待文档处理完成（状态变为"就绪"）

### 2. 智能问答

1. 普通用户登录后进入对话界面
2. 输入问题，如："这个产品的保修期多久？"
3. 系统自动：
   - 分解问题（如需要）
   - 选择检索策略
   - 检索相关文档
   - 生成带引用的回答
4. 点击引用来源可预览原文

### 3. 模型切换

管理员可在"模型设置"页面：
- 切换 LLM 模型（15 种可选）
- 切换 Embedding 模型（2 种可选）
- 查看 Embedding 版本是否匹配

---

## 🎓 学习资源

本项目参考了以下优秀资源：

- [All-in-RAG](https://github.com/datawhalechina/all-in-rag) - RAG 技术全栈指南
- [LangChain 官方文档](https://python.langchain.com/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 📧 联系方式

如有问题，欢迎通过 GitHub Issues 交流。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star 支持！**

</div>
