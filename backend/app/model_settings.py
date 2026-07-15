"""模型配置管理：支持运行时切换，无需重启"""
import json
from pathlib import Path
from app.config import BASE_DIR

SETTINGS_FILE = BASE_DIR / "data" / "model_settings.json"

# 阿里云百炼有 100万 tokens/月免费额度的模型列表
# 来源: https://help.aliyun.com/zh/model-studio/new-free-quota
FREE_MODELS = {
    "llm": [
        # ===== Qwen3.6 最新系列 =====
        {"value": "qwen3.6-flash", "label": "Qwen3.6-Flash (推荐)", "desc": "全系列最低单价，轻量极速"},
        {"value": "qwen3.6-plus", "label": "Qwen3.6-Plus", "desc": "首个Qwen3.6模型"},
        {"value": "qwen3.6-max-preview", "label": "Qwen3.6-Max-Preview", "desc": "旗舰预览版，最强效果"},
        # ===== Qwen3 系列 =====
        {"value": "qwen3-flash", "label": "Qwen3-Flash", "desc": "Qwen3快速版"},
        {"value": "qwen3-turbo", "label": "Qwen3-Turbo", "desc": "速度与效果平衡"},
        {"value": "qwen3-plus", "label": "Qwen3-Plus", "desc": "增强版，128K上下文"},
        {"value": "qwen3-max", "label": "Qwen3-Max", "desc": "Qwen3旗舰"},
        # ===== Qwen2.5 / 开源系列 =====
        {"value": "qwen-turbo", "label": "Qwen Turbo", "desc": "速度快，有免费额度"},
        {"value": "qwen-plus", "label": "Qwen Plus", "desc": "效果更好"},
        {"value": "qwen-max", "label": "Qwen Max", "desc": "最强效果"},
        {"value": "qwen3-8b", "label": "Qwen3-8B 开源", "desc": "开源8B"},
        {"value": "qwen2.5-7b-instruct", "label": "Qwen2.5-7B 开源", "desc": "开源7B"},
        # ===== 第三方模型 =====
        {"value": "deepseek-r1-distill-llama-70b", "label": "DeepSeek-R1 蒸馏 70B", "desc": "DeepSeek推理"},
        {"value": "llama-4-scout-17b-16e-instruct", "label": "Llama 4 Scout", "desc": "Meta轻量"},
        {"value": "llama-4-maverick-17b-128e-instruct", "label": "Llama 4 Maverick", "desc": "Meta旗舰"},
    ],
    "embedding": [
        {"value": "text-embedding-v1", "label": "文本向量 V1", "desc": "基础版1536维，免费推荐"},
        {"value": "text-embedding-v2", "label": "文本向量 V2", "desc": "增强版1536维"},
    ],
}

DEFAULT_SETTINGS = {
    "llm_model": "qwen3.6-flash",
    "embedding_model": "text-embedding-v1",
}


def load_model_settings() -> dict:
    """加载模型配置（文件不存在则创建默认）"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # 返回默认配置
    return DEFAULT_SETTINGS.copy()


def save_model_settings(settings: dict):
    """保存模型配置到文件"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_current_llm_model() -> str:
    """获取当前 LLM 模型名"""
    return load_model_settings().get("llm_model", DEFAULT_SETTINGS["llm_model"])


def get_current_embedding_model() -> str:
    """获取当前 Embedding 模型名"""
    return load_model_settings().get("embedding_model", DEFAULT_SETTINGS["embedding_model"])


def get_all_available_models() -> dict:
    """获取所有可用模型列表 + 当前选择"""
    current = load_model_settings()
    return {
        "llm": {
            "options": FREE_MODELS["llm"],
            "current": current.get("llm_model", DEFAULT_SETTINGS["llm_model"]),
        },
        "embedding": {
            "options": FREE_MODELS["embedding"],
            "current": current.get("embedding_model", DEFAULT_SETTINGS["embedding_model"]),
        },
    }


def switch_llm_model(model_name: str) -> dict:
    """切换 LLM 模型"""
    available = [m["value"] for m in FREE_MODELS["llm"]]
    if model_name not in available:
        raise ValueError(f"不支持的模型: {model_name}。可用: {available}")
    settings = load_model_settings()
    settings["llm_model"] = model_name
    save_model_settings(settings)
    return {"message": f"LLM 模型已切换为: {model_name}", "current": model_name}


def switch_embedding_model(model_name: str) -> dict:
    """切换 Embedding 模型"""
    available = [m["value"] for m in FREE_MODELS["embedding"]]
    if model_name not in available:
        raise ValueError(f"不支持的模型: {model_name}。可用: {available}")
    settings = load_model_settings()
    settings["embedding_model"] = model_name
    save_model_settings(settings)
    return {"message": f"Embedding 模型已切换为: {model_name}", "current": model_name}
