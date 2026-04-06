import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_CUT_ROOT = REPO_ROOT.parent / "aicut2602"
ONLINE_VERSION_ROOT = AI_CUT_ROOT / "libs" / "cut_breakpoints" / "online_version"
TEST_ROOT = REPO_ROOT / "tests" / "test_cujiian"
OUTPUT_ROOT = TEST_ROOT / "output"
FAKE_TOS_ROOT = TEST_ROOT / "fake_tos"


if str(ONLINE_VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(ONLINE_VERSION_ROOT))

# ---------- 真实 TOS 客户端（延迟导入） ----------
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "tos-cn-shanghai.volces.com")
TOS_REGION = os.getenv("TOS_REGION", "cn-shanghai")
TOS_BUCKET = os.getenv("TOS_BUCKET", "autocut-malin")
TOS_AK = os.getenv("TOS_ACCESS_KEY")
TOS_SK = os.getenv("TOS_SECRET_KEY")

_tos_client = None


def _get_tos_client():
    global _tos_client
    if _tos_client is None:
        import tos
        if not TOS_AK or not TOS_SK:
            raise RuntimeError("TOS_ACCESS_KEY / TOS_SECRET_KEY 未设置")
        _tos_client = tos.TosClientV2(TOS_AK, TOS_SK, TOS_ENDPOINT, TOS_REGION)
    return _tos_client


def real_upload(local_path: str, object_key: str) -> str:
    """真实 TOS 上传"""
    client = _get_tos_client()
    client.put_object_from_file(TOS_BUCKET, object_key, local_path)
    return f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{object_key}"


def real_download(url_or_tos_key: str, local_path: str) -> str:
    """真实 TOS 下载。支持 https://... 和纯 object_key"""
    dst = Path(local_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    client = _get_tos_client()

    # 从 URL 中提取 object_key
    prefix = f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/"
    if url_or_tos_key.startswith(prefix):
        object_key = url_or_tos_key[len(prefix):]
    elif url_or_tos_key.startswith("http"):
        object_key = "/".join(url_or_tos_key.split("/", 4)[4:])
    else:
        object_key = url_or_tos_key

    client.get_object_to_file(TOS_BUCKET, object_key, local_path)
    return str(dst)

# ---------- fake TOS (本地模拟) ----------


def load_config(config_path: str) -> dict:
    path = Path(config_path).resolve()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def get_case_dir(task_id: str) -> Path:
    case_dir = OUTPUT_ROOT / task_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_file_exists(path_str: str, label: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"{label} 不存在: {path}")
    return path


def fake_upload(local_path: str, object_key: str) -> str:
    src = Path(local_path)
    dst = FAKE_TOS_ROOT / object_key
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"fake-tos://{object_key}"


def fake_download(url_or_path: str, local_path: str) -> str:
    dst = Path(local_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if url_or_path.startswith("fake-tos://"):
        object_key = url_or_path[len("fake-tos://"):]
        src = FAKE_TOS_ROOT / object_key
    else:
        src = Path(url_or_path)

    if not src.exists():
        raise FileNotFoundError(f"下载源不存在: {src}")

    shutil.copy2(src, dst)
    return str(dst)


def get_analyze_result_path(task_id: str) -> Path:
    return get_case_dir(task_id) / "analyze_result.json"


def get_preview_result_path(task_id: str) -> Path:
    return get_case_dir(task_id) / "preview_result.json"


def get_finalize_original_result_path(task_id: str) -> Path:
    return get_case_dir(task_id) / "finalize_original_result.json"


def get_finalize_vertical_result_path(task_id: str) -> Path:
    return get_case_dir(task_id) / "finalize_vertical_result.json"


def get_groundtruth_result_path(task_id: str) -> Path:
    return get_case_dir(task_id) / "groundtruth_result.json"
