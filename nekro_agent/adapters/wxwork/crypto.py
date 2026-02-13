
"""
企业微信智能机器人消息加密解密工具

参考文档：https://developer.work.weixin.qq.com/document/path/101033
"""

import base64
import hashlib
import json
import struct

from Crypto.Cipher import AES

from nekro_agent.core.logger import get_sub_logger


logger = get_sub_logger("adapter.wxwork")
class WxWorkBotCrypt:
    """企业微信智能机器人加解密类"""

    def __init__(self, token: str, encoding_aes_key: str):
        """初始化加解密工具

        Args:
            token: 企业微信后台配置的 Token
            encoding_aes_key: 企业微信后台配置的 EncodingAESKey（43位字符）
        """
        self.token = token

        # EncodingAESKey 是 43 位字符，补齐 '=' 后进行 base64 解码得到 32 字节的 AES 密钥
        self.aes_key = base64.b64decode(encoding_aes_key + "=")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证 URL 有效性（GET 请求）

        Args:
            msg_signature: 企业微信加密签名
            timestamp: 时间戳
            nonce: 随机数
            echostr: 加密的随机字符串

        Returns:
            解密后的 echostr 明文（msg 字段内容），用于返回给企业微信

        Raises:
            ValueError: 签名验证失败或解密失败
        """
        # 1. 验证签名
        signature = self._generate_signature(timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")

        # 2. 解密 echostr，获取其中的 msg 字段
        return self._decrypt(echostr, receive_id="")

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypt_data: str) -> dict:
        """解密消息（POST 请求）

        Args:
            msg_signature: 企业微信加密签名
            timestamp: 时间戳
            nonce: 随机数
            encrypt_data: 加密的消息内容（来自 JSON 的 encrypt 字段）

        Returns:
            解密后的消息 JSON 对象

        Raises:
            ValueError: 签名验证失败或解密失败
        """
        # 1. 验证签名
        signature = self._generate_signature(timestamp, nonce, encrypt_data)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")

        # 2. 解密消息（智能机器人场景 receive_id 传空字符串）
        decrypted_text = self._decrypt(encrypt_data, receive_id="")

        # 3. 解析 JSON
        try:
            return json.loads(decrypted_text)
        except json.JSONDecodeError as e:
            logger.exception(f"解析解密后的消息 JSON 失败: {e}")
            raise ValueError(f"消息不是有效的 JSON 格式: {decrypted_text[:200]}") from e

    def encrypt_message(self, reply_data: dict, nonce: str, timestamp: str) -> dict:
        """加密消息用于回复（POST 响应）

        Args:
            reply_data: 要回复的消息数据（dict 格式，会转换为 JSON）
            nonce: 随机数（使用回调 URL 中的 nonce）
            timestamp: 时间戳（秒级）

        Returns:
            加密后的完整响应对象（包含 encrypt、msgsignature、timestamp、nonce）
        """
        # 1. 将 reply_data 转换为 JSON 字符串
        reply_json = json.dumps(reply_data, ensure_ascii=False)

        # 2. 加密消息（智能机器人场景 receive_id 传空字符串）
        encrypted = self._encrypt(reply_json, receive_id="")

        # 3. 生成签名
        signature = self._generate_signature(timestamp, nonce, encrypted)

        # 4. 构造回复对象
        return {
            "encrypt": encrypted,
            "msgsignature": signature,
            "timestamp": int(timestamp),
            "nonce": nonce,
        }

    def _generate_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        """生成签名

        对 token、timestamp、nonce、encrypt 进行字典序排序后拼接，
        然后进行 SHA1 加密得到签名
        """
        sort_list = sorted([self.token, str(timestamp), nonce, encrypt])
        signature_str = "".join(sort_list)
        return hashlib.sha1(signature_str.encode("utf-8")).hexdigest()

    def _encrypt(self, text: str, receive_id: str) -> str:
        """加密文本

        加密格式：random(16B) + msg_len(4B) + msg + receive_id

        Args:
            text: 要加密的明文消息
            receive_id: 接收者 ID（智能机器人场景传空字符串）
        """
        # 1. 生成 16 字节随机字符串
        import os

        random_bytes = os.urandom(16)

        # 2. 消息体长度（4字节网络字节序）
        msg_bytes = text.encode("utf-8")
        msg_len_bytes = struct.pack(">I", len(msg_bytes))

        # 3. 拼接: random + msg_len + msg + receive_id
        receive_id_bytes = receive_id.encode("utf-8")
        plain_text = random_bytes + msg_len_bytes + msg_bytes + receive_id_bytes

        # 4. 使用 PKCS7 填充
        plain_text = self._pkcs7_pad(plain_text)

        # 5. AES 加密（CBC 模式，IV 为 AES Key 的前 16 字节）
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        encrypted_bytes = cipher.encrypt(plain_text)

        # 6. Base64 编码
        return base64.b64encode(encrypted_bytes).decode("utf-8")

    def _decrypt(self, encrypt_text: str, receive_id: str) -> str:
        """解密文本

        Args:
            encrypt_text: 加密的文本
            receive_id: 接收者 ID（智能机器人场景传空字符串）

        Returns:
            解密后的原始消息内容（msg 字段）
        """
        # 1. Base64 解码
        cipher_text = base64.b64decode(encrypt_text)

        # 2. AES 解密（CBC 模式，IV 为 AES Key 的前 16 字节）
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain_text = cipher.decrypt(cipher_text)

        # 3. 去除 PKCS7 填充
        plain_text = self._pkcs7_unpad(plain_text)

        # 4. 解析格式: random(16B) + msg_len(4B) + msg + receive_id
        # 跳过前 16 字节的随机字符串
        content = plain_text[16:]

        # 读取消息长度（4字节网络字节序）
        msg_len = struct.unpack(">I", content[:4])[0]

        # 提取消息内容
        msg_content = content[4 : 4 + msg_len]

        # 提取并验证 receive_id（可选）
        from_receive_id = content[4 + msg_len :].decode("utf-8")
        if receive_id and from_receive_id != receive_id:
            logger.warning(f"ReceiveID 不匹配: {from_receive_id} != {receive_id}")

        return msg_content.decode("utf-8")

    @staticmethod
    def _pkcs7_pad(data: bytes) -> bytes:
        """PKCS7 填充"""
        block_size = 32  # AES 块大小为 32 字节
        padding_len = block_size - len(data) % block_size
        padding = bytes([padding_len] * padding_len)
        return data + padding

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        """去除 PKCS7 填充"""
        padding_len = data[-1]
        return data[:-padding_len]
