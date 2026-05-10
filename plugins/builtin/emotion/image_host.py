import asyncio
import hashlib
import json
import mimetypes
import random
import string
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

from .gallery import is_supported_image_file


class StarDotsProvider:
    BASE_URL = "https://api.stardots.io"
    CATEGORY_SEPARATOR = "@@CAT@@"
    DEFAULT_CATEGORY = "default"
    MIME_TYPES = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.key = config["key"]
        self.secret = config["secret"]
        self.space = config["space"]
        self.local_dir = Path(config.get("local_dir", ""))
        self.server_time_offset = 0
        self._sync_server_time()

    def _sync_server_time(self) -> None:
        try:
            with httpx.Client(timeout=10, verify=False) as client:
                response = client.get(f"{self.BASE_URL}/openapi/space/list")
                if response.status_code == 200:
                    server_ts = int(response.json().get("ts", 0)) // 1000
                    if server_ts:
                        self.server_time_offset = server_ts - int(time.time())
        except Exception:
            self.server_time_offset = 8 * 3600

    def _generate_headers(self) -> Dict[str, str]:
        timestamp = str(int(time.time() + self.server_time_offset))
        nonce = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        sign = hashlib.md5(f"{timestamp}|{self.secret}|{nonce}".encode()).hexdigest().upper()
        return {
            "x-stardots-timestamp": timestamp,
            "x-stardots-nonce": nonce,
            "x-stardots-key": self.key,
            "x-stardots-sign": sign,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("verify", False)
        response = httpx.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _encode_category(self, category: str) -> str:
        if not category or category == ".":
            return ""
        return category.replace("/", "@@DIR@@").replace("\\", "@@DIR@@")

    def _decode_category(self, encoded: str) -> str:
        if not encoded:
            return self.DEFAULT_CATEGORY
        return encoded.replace("@@DIR@@", "/")

    @staticmethod
    def _extract_image_size(image_info: Dict[str, Any]) -> int:
        for key in ("size", "fileSize", "file_size", "bytes", "length", "byteSize", "byte_size"):
            value = image_info.get(key)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return 0

    def upload_image(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        self._sync_server_time()
        headers = self._generate_headers()
        headers.pop("Content-Type", None)
        mime_type = self.MIME_TYPES.get(file_path.suffix.lower(), "image/jpeg")
        try:
            rel_path = file_path.relative_to(self.local_dir)
        except ValueError:
            rel_path = Path(file_path.name)
        category = str(rel_path.parent).replace("\\", "/")
        if category == ".":
            category = ""
        encoded_category = self._encode_category(category)
        remote_filename = f"{encoded_category}{self.CATEGORY_SEPARATOR}{rel_path.name}" if encoded_category else rel_path.name
        with file_path.open("rb") as file:
            files = {
                "file": (remote_filename, file, mime_type),
                "space": (None, self.space),
            }
            response = self._request("PUT", f"{self.BASE_URL}/openapi/file/upload", headers=headers, files=files, timeout=60)
        result = response.json()
        if not result.get("success"):
            raise RuntimeError(result.get("message", "StarDots upload failed"))
        data = result.get("data", {})
        return {"url": data.get("url", ""), "id": str(rel_path).replace("\\", "/"), "filename": rel_path.name, "category": category}

    def delete_image(self, image_id: str) -> bool:
        self._sync_server_time()
        response = self._request(
            "DELETE",
            f"{self.BASE_URL}/openapi/file/delete",
            headers=self._generate_headers(),
            json={"space": self.space, "filenameList": [image_id]},
        )
        return bool(response.json().get("success"))

    def get_image_list(self) -> List[Dict[str, Any]]:
        page = 1
        page_size = 100
        all_images: List[Dict[str, Any]] = []
        while True:
            self._sync_server_time()
            response = self._request(
                "GET",
                f"{self.BASE_URL}/openapi/file/list",
                headers=self._generate_headers(),
                params={"space": self.space, "page": page, "pageSize": page_size},
            )
            result = response.json()
            if not result.get("success"):
                raise RuntimeError(result.get("message", "StarDots list failed"))
            images = result.get("data", {}).get("list", [])
            if not images:
                return all_images
            for image in images:
                raw_filename = image.get("name", "")
                if self.CATEGORY_SEPARATOR in raw_filename:
                    encoded_category, filename = raw_filename.split(self.CATEGORY_SEPARATOR, 1)
                    category = self._decode_category(encoded_category)
                    file_id = f"{category}/{filename}" if category else filename
                else:
                    category = ""
                    filename = raw_filename
                    file_id = filename
                all_images.append(
                    {
                        "url": image.get("url", ""),
                        "id": file_id.replace("\\", "/"),
                        "filename": filename,
                        "category": category,
                        "size": self._extract_image_size(image),
                    },
                )
            if len(images) < page_size:
                return all_images
            page += 1

    def download_image(self, image_info: Dict[str, Any], save_path: Path) -> bool:
        category = str(image_info.get("category", ""))
        encoded_category = self._encode_category(category)
        filename = str(image_info.get("filename", ""))
        original_name = f"{encoded_category}{self.CATEGORY_SEPARATOR}{filename}" if category and category != self.DEFAULT_CATEGORY else filename
        self._sync_server_time()
        ticket_response = self._request(
            "POST",
            f"{self.BASE_URL}/openapi/file/ticket",
            headers=self._generate_headers(),
            json={"space": self.space, "filename": original_name},
        )
        ticket_result = ticket_response.json()
        if not ticket_result.get("success"):
            return False
        ticket = ticket_result.get("data", {}).get("ticket", "")
        download_url = f"https://i.stardots.io/{self.space}/{original_name}?ticket={ticket}"
        response = self._request("GET", download_url, timeout=60)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        return save_path.exists() and save_path.stat().st_size > 0


class CloudflareR2Provider:
    def __init__(self, config: Dict[str, str]):
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise RuntimeError("Cloudflare R2 需要安装 boto3 和 botocore") from exc
        self.ClientError = ClientError
        self.account_id = config["account_id"]
        self.access_key_id = config["access_key_id"]
        self.secret_access_key = config["secret_access_key"]
        self.bucket_name = config["bucket_name"]
        self.public_url = config.get("public_url")
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self.s3_client.head_bucket(Bucket=self.bucket_name)

    def upload_image(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        mime_type, _ = mimetypes.guess_type(str(file_path))
        s3_key = self._generate_s3_key(file_path)
        self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=file_path.read_bytes(), ContentType=mime_type or "image/jpeg")
        return {"url": self._get_public_url(s3_key), "id": s3_key, "filename": file_path.name, "category": self._get_category_from_path(file_path)}

    def delete_image(self, image_id: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=image_id)
            return True
        except Exception:
            return False

    def get_image_list(self) -> List[Dict[str, Any]]:
        all_images: List[Dict[str, Any]] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix="emotions/"):
            for obj in page.get("Contents", []):
                s3_key = obj.get("Key", "")
                if not s3_key or s3_key.endswith("/") or not s3_key.startswith("emotions/"):
                    continue
                category, filename = self._parse_s3_key(s3_key)
                all_images.append({"url": self._get_public_url(s3_key), "id": s3_key, "filename": filename, "category": category, "size": int(obj.get("Size", 0))})
        return all_images

    def download_image(self, image_info: Dict[str, Any], save_path: Path) -> bool:
        s3_key = str(image_info.get("id", ""))
        save_path.parent.mkdir(parents=True, exist_ok=True)
        self.s3_client.download_file(self.bucket_name, s3_key, str(save_path))
        return save_path.exists() and save_path.stat().st_size > 0

    @staticmethod
    def _get_category_from_path(file_path: Path) -> str:
        parent = file_path.parent
        if parent.name and parent.name != ".":
            return parent.name
        return ""

    def _generate_s3_key(self, file_path: Path) -> str:
        return f"emotions/{file_path.name}"

    @staticmethod
    def _parse_s3_key(s3_key: str) -> Tuple[str, str]:
        if s3_key.startswith("emotions/"):
            s3_key = s3_key[len("emotions/"):]
        filename = s3_key.split("/")[-1]
        category = "/".join(s3_key.split("/")[:-1]) if "/" in s3_key else ""
        return category, filename

    def _get_public_url(self, s3_key: str) -> str:
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{s3_key}"
        return f"https://{self.bucket_name}.{self.account_id}.r2.dev/{s3_key}"


class LocalImageHostSync:
    def __init__(self, provider_type: str, config: Dict[str, str], local_dir: Path):
        self.provider_type = provider_type
        self.config = config
        self.local_dir = local_dir
        self.tracker_path = local_dir / ".upload_tracker.json"
        self.provider = self._create_provider()

    def _create_provider(self):
        if self.provider_type == "stardots":
            return StarDotsProvider({**self.config, "local_dir": str(self.local_dir)})
        if self.provider_type == "cloudflare_r2":
            return CloudflareR2Provider(self.config)
        raise ValueError("图床未启用或 provider 不支持")

    def _scan_local_images(self) -> List[Dict[str, str]]:
        self.local_dir.mkdir(parents=True, exist_ok=True)
        images = []
        for file_path in self.local_dir.iterdir():
            if not is_supported_image_file(file_path):
                continue
            images.append(
                {
                    "path": str(file_path),
                    "id": file_path.name,
                    "filename": file_path.name,
                    "category": "",
                },
            )
        return images

    def _load_tracker(self) -> Dict[str, Any]:
        if not self.tracker_path.exists():
            return {}
        try:
            return json.loads(self.tracker_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_tracker(self, tracker: Dict[str, Any]) -> None:
        self.tracker_path.write_text(json.dumps(tracker, ensure_ascii=False, indent=2), encoding="utf-8")

    def _remote_id(self, image: Dict[str, Any]) -> str:
        remote_id = str(image.get("id", "")).replace("\\", "/")
        if self.provider_type == "cloudflare_r2" and remote_id.startswith("emotions/"):
            return remote_id[len("emotions/"):]
        return remote_id

    def check_status(self) -> Dict[str, Any]:
        local_images = self._scan_local_images()
        remote_images = self.provider.get_image_list()
        tracker = self._load_tracker()
        local_ids = {image["id"] for image in local_images}
        remote_ids = {self._remote_id(image) for image in remote_images}
        
        remote_total_size = 0
        for image in remote_images:
            size = int(image.get("size", image.get("file_size", 0)) or 0)
            if size <= 0:
                tid = self._remote_id(image)
                if tid in tracker:
                    size = int(tracker[tid].get("file_size", 0))
            remote_total_size += size

        local_total_size = sum(Path(image["path"]).stat().st_size for image in local_images if Path(image["path"]).exists())
        to_upload = [image for image in local_images if image["id"] not in remote_ids or image["id"] not in tracker]
        to_download = [image for image in remote_images if self._remote_id(image) not in local_ids]
        to_delete_remote = to_download.copy()
        to_delete_local = [image for image in local_images if image["id"] not in remote_ids]
        return {
            "provider": self.provider_type,
            "to_upload": to_upload,
            "to_download": to_download,
            "to_delete_remote": to_delete_remote,
            "to_delete_local": to_delete_local,
            "is_synced": not (to_upload or to_download or to_delete_remote or to_delete_local),
            "local_image_count": len(local_images),
            "remote_image_count": len(remote_images),
            "local_total_size": local_total_size,
            "remote_total_size": remote_total_size,
        }

    def upload_to_remote(self) -> Dict[str, Any]:
        status = self.check_status()
        tracker = self._load_tracker()
        uploaded = []
        failed = []
        for image in status["to_upload"]:
            file_path = Path(image["path"])
            try:
                result = self.provider.upload_image(file_path)
                tracker[image["id"]] = {
                    "filename": image["filename"],
                    "category": image["category"],
                    "remote_url": result.get("url", ""),
                    "upload_time": int(time.time()),
                    "file_size": file_path.stat().st_size if file_path.exists() else 0,
                }
                uploaded.append({**image, "url": result.get("url", "")})
            except Exception as e:
                failed.append({**image, "error": str(e)})
        self._save_tracker(tracker)
        return {"uploaded": uploaded, "failed": failed}

    def download_to_local(self) -> Dict[str, Any]:
        status = self.check_status()
        downloaded = []
        failed = []
        for image in status["to_download"]:
            filename = Path(str(image.get("filename", ""))).name
            if not filename:
                failed.append({**image, "error": "filename empty"})
                continue
            save_path = self.local_dir / filename
            try:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                if self.provider.download_image(image, save_path):
                    downloaded.append({**image, "path": str(save_path)})
                else:
                    failed.append({**image, "error": "download failed"})
            except Exception as e:
                failed.append({**image, "error": str(e)})
        return {"downloaded": downloaded, "failed": failed}

    def overwrite_to_remote(self) -> Dict[str, Any]:
        upload_result = self.upload_to_remote()
        status = self.check_status()
        deleted = []
        failed = []
        for image in status["to_delete_remote"]:
            try:
                if self.provider.delete_image(str(image.get("id", ""))):
                    deleted.append(image)
                else:
                    failed.append({**image, "error": "delete failed"})
            except Exception as e:
                failed.append({**image, "error": str(e)})
        return {**upload_result, "deleted_remote": deleted, "delete_failed": failed}

    def overwrite_from_remote(self) -> Dict[str, Any]:
        download_result = self.download_to_local()
        status = self.check_status()
        deleted = []
        failed = []
        for image in status["to_delete_local"]:
            file_path = Path(image["path"])
            try:
                file_path.unlink(missing_ok=True)
                deleted.append(image)
            except Exception as e:
                failed.append({**image, "error": str(e)})
        return {**download_result, "deleted_local": deleted, "delete_failed": failed}


class ImageHostService:
    def __init__(self, config: Any, gallery_dir: Path):
        self.config = config
        self.gallery_dir = gallery_dir
        self._sync_lock = asyncio.Lock()

    def build_config(self) -> Tuple[str, Dict[str, str]]:
        provider = self.config.IMAGE_HOST_PROVIDER.strip().lower()
        if provider in {"", "disabled", "none", "不使用"}:
            raise ValueError("图床未启用，请将图床提供商切换为 stardots 或 cloudflare_r2")
        if provider == "stardots":
            config = {
                "key": self.config.STARDOTS_KEY,
                "secret": self.config.STARDOTS_SECRET,
                "space": self.config.STARDOTS_SPACE,
            }
            missing = [key for key, value in config.items() if not value]
        elif provider == "cloudflare_r2":
            config = {
                "account_id": self.config.R2_ACCOUNT_ID,
                "access_key_id": self.config.R2_ACCESS_KEY_ID,
                "secret_access_key": self.config.R2_SECRET_ACCESS_KEY,
                "bucket_name": self.config.R2_BUCKET_NAME,
            }
            if self.config.R2_PUBLIC_URL:
                config["public_url"] = self.config.R2_PUBLIC_URL
            missing = [key for key in ("account_id", "access_key_id", "secret_access_key", "bucket_name") if not config.get(key)]
        else:
            raise ValueError("图床未启用，请将 IMAGE_HOST_PROVIDER 设置为 stardots 或 cloudflare_r2")
        if missing:
            raise ValueError(f"图床配置缺失: {', '.join(missing)}")
        return provider, config

    def create_sync(self) -> LocalImageHostSync:
        provider, config = self.build_config()
        return LocalImageHostSync(provider, config, self.gallery_dir)

    @staticmethod
    def format_size(size: int) -> str:
        value = float(size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024 or unit == "TB":
                return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size} B"

    def get_overview(self) -> Dict[str, Any]:
        provider = self.config.IMAGE_HOST_PROVIDER.strip().lower()
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        local_images = [path for path in self.gallery_dir.iterdir() if is_supported_image_file(path)]
        overview: Dict[str, Any] = {
            "provider": provider,
            "provider_name": {
                "disabled": "未启用",
                "stardots": "StarDots",
                "cloudflare_r2": "Cloudflare R2",
            }.get(provider, provider),
            "enabled": provider in {"stardots", "cloudflare_r2"},
            "remote_image_count": 0,
            "remote_total_size": 0,
            "remote_total_size_human": "0 B",
            "local_image_count": len(local_images),
            "local_total_size": sum(path.stat().st_size for path in local_images),
        }
        overview["local_total_size_human"] = self.format_size(int(overview["local_total_size"]))
        if not overview["enabled"]:
            overview.update(
                {
                    "is_synced": True,
                    "to_upload_count": 0,
                    "to_download_count": 0,
                    "status_message": "图床未启用，仅显示本地图库统计",
                },
            )
            return overview
        try:
            sync = self.create_sync()
            status = sync.check_status()
            overview.update(
                {
                    "remote_image_count": status.get("remote_image_count", 0),
                    "remote_total_size": status.get("remote_total_size", 0),
                    "remote_total_size_human": self.format_size(int(status.get("remote_total_size", 0))),
                    "local_image_count": status.get("local_image_count", overview["local_image_count"]),
                    "local_total_size": status.get("local_total_size", overview["local_total_size"]),
                    "local_total_size_human": self.format_size(int(status.get("local_total_size", overview["local_total_size"]))),
                    "is_synced": status.get("is_synced", False),
                    "to_upload_count": len(status.get("to_upload", [])),
                    "to_download_count": len(status.get("to_download", [])),
                    "status_message": "图床状态统计正常",
                },
            )
        except Exception as e:
            overview.update(
                {
                    "enabled": False,
                    "is_synced": False,
                    "to_upload_count": 0,
                    "to_download_count": 0,
                    "status_message": f"图床状态获取失败：{e}",
                    "error": str(e),
                },
            )
        return overview

    async def run_task(self, task: str) -> Dict[str, Any]:
        async with self._sync_lock:
            sync = self.create_sync()
            if task == "status":
                return await asyncio.to_thread(sync.check_status)
            if task == "upload":
                return await asyncio.to_thread(sync.upload_to_remote)
            if task == "download":
                return await asyncio.to_thread(sync.download_to_local)
            if task == "sync_all":
                upload_result = await asyncio.to_thread(sync.upload_to_remote)
                download_result = await asyncio.to_thread(sync.download_to_local)
                return {"upload": upload_result, "download": download_result}
            if task == "overwrite_to_remote":
                return await asyncio.to_thread(sync.overwrite_to_remote)
            if task == "overwrite_from_remote":
                return await asyncio.to_thread(sync.overwrite_from_remote)
            raise ValueError(f"未知同步任务: {task}")

    @staticmethod
    def summarize_result(result: Dict[str, Any]) -> str:
        return json.dumps(result, ensure_ascii=False, indent=2)
