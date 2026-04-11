import base64
import hashlib
import json
import struct
import xml.etree.ElementTree as ET

from Crypto.Cipher import AES


class WxWorkCorpAppCrypt:
    """企业微信自建应用回调加解密工具。"""

    def __init__(self, token: str, encoding_aes_key: str, receive_id: str):
        self.token = token.strip()
        self.receive_id = receive_id.strip()
        self.aes_key = base64.b64decode(encoding_aes_key.strip() + "=")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        signature = self._generate_signature(timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")
        return self._decrypt(echostr, receive_id=self.receive_id)

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, body_text: str) -> str:
        encrypt_data = self._extract_encrypt_field(body_text)
        signature = self._generate_signature(timestamp, nonce, encrypt_data)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")
        return self._decrypt(encrypt_data, receive_id=self.receive_id)

    def _extract_encrypt_field(self, body_text: str) -> str:
        root = ET.fromstring(body_text)
        encrypt_element = root.find("Encrypt")
        if encrypt_element is None or not encrypt_element.text:
            raise ValueError("回调消息缺少 Encrypt 字段")
        return encrypt_element.text

    def _generate_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        sort_list = sorted([self.token, str(timestamp), nonce, encrypt])
        signature_str = "".join(sort_list)
        return hashlib.sha1(signature_str.encode("utf-8")).hexdigest()

    def _decrypt(self, encrypt_text: str, receive_id: str) -> str:
        cipher_text = base64.b64decode(encrypt_text)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain_text = cipher.decrypt(cipher_text)
        plain_text = self._pkcs7_unpad(plain_text)

        content = plain_text[16:]
        msg_len = struct.unpack(">I", content[:4])[0]
        msg_content = content[4 : 4 + msg_len]
        from_receive_id = content[4 + msg_len :].decode("utf-8")

        if receive_id and from_receive_id != receive_id:
            raise ValueError(f"ReceiveID 不匹配: {from_receive_id} != {receive_id}")

        return msg_content.decode("utf-8")

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        padding_len = data[-1]
        return data[:-padding_len]


class WxWorkAIBotCrypt:
    """企业微信 AI Bot Webhook 加解密工具。"""

    def __init__(self, token: str, encoding_aes_key: str):
        self.token = token.strip()
        self.aes_key = base64.b64decode(encoding_aes_key.strip() + "=")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        signature = self._generate_signature(timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")
        return self._decrypt(echostr)

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, body_text: str) -> dict[str, object]:
        encrypt_data = self._extract_encrypt_field(body_text)
        signature = self._generate_signature(timestamp, nonce, encrypt_data)
        if signature != msg_signature:
            raise ValueError(f"签名验证失败: {signature} != {msg_signature}")

        decrypted_text = self._decrypt(encrypt_data)
        try:
            payload = json.loads(decrypted_text)
        except json.JSONDecodeError:
            return {"_raw_text": decrypted_text}

        if isinstance(payload, dict):
            return payload
        return {"_json_value": payload}

    def _extract_encrypt_field(self, body_text: str) -> str:
        stripped = body_text.strip()
        if stripped.startswith("{"):
            body = json.loads(stripped)
            encrypt_data = body.get("encrypt")
            if isinstance(encrypt_data, str) and encrypt_data:
                return encrypt_data
            raise ValueError("回调消息缺少 encrypt 字段")

        root = ET.fromstring(body_text)
        encrypt_element = root.find("Encrypt")
        if encrypt_element is None or not encrypt_element.text:
            raise ValueError("回调消息缺少 Encrypt 字段")
        return encrypt_element.text

    def _generate_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        sort_list = sorted([self.token, str(timestamp), nonce, encrypt])
        signature_str = "".join(sort_list)
        return hashlib.sha1(signature_str.encode("utf-8")).hexdigest()

    def _decrypt(self, encrypt_text: str) -> str:
        cipher_text = base64.b64decode(encrypt_text)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain_text = cipher.decrypt(cipher_text)
        plain_text = self._pkcs7_unpad(plain_text)

        content = plain_text[16:]
        msg_len = struct.unpack(">I", content[:4])[0]
        msg_content = content[4 : 4 + msg_len]
        return msg_content.decode("utf-8")

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        padding_len = data[-1]
        return data[:-padding_len]
