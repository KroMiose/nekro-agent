"""命令参数解析器 - 支持位置参数和 K-V 参数混合模式"""

import inspect
import shlex
from typing import Any, Callable, Optional, get_type_hints

from nekro_agent.services.command.schemas import _UNSET, Arg


class _ParamInfo:
    """解析后的参数元信息"""

    def __init__(
        self,
        name: str,
        annotation: type,
        arg_meta: Optional[Arg],
        default: Any,
    ):
        self.name = name
        self.annotation = annotation
        self.arg_meta = arg_meta
        self.default = default

    @property
    def is_positional(self) -> bool:
        return self.arg_meta.positional if self.arg_meta else False

    @property
    def is_greedy(self) -> bool:
        return self.arg_meta.greedy if self.arg_meta else False

    @property
    def is_required(self) -> bool:
        return self.default is _UNSET


class ArgumentParser:
    """命令参数解析器 - 支持位置参数和 K-V 参数混合模式"""

    @classmethod
    def parse(cls, func: Callable, raw_args: str) -> dict[str, Any]:
        """从函数签名 + 原始参数字符串 -> 解析后的 kwargs

        解析规则：
        1. 扫描函数签名，提取参数列表及 Arg 元数据
        2. 对 raw_args 进行词法分析（支持引号/转义）
        3. 识别 K-V 对 (key:value 或 key:"value") 和位置值
        4. K-V 参数直接按 key 填充
        5. 位置值按 positional=True 参数的声明顺序填充
        6. greedy=True 的参数吃掉剩余所有文本
        7. 执行类型转换和约束校验
        """
        params = cls._extract_params(func)
        if not params:
            return {}

        raw_args = raw_args.strip()
        if not raw_args:
            # 无参数输入，检查是否所有参数都有默认值
            result = {}
            for p in params:
                if p.is_required:
                    raise ValueError(f"缺少必填参数: {p.name}" + (f" ({p.arg_meta.description})" if p.arg_meta else ""))
                result[p.name] = p.default
            return result

        # 检查是否有 greedy 参数
        greedy_param = next((p for p in params if p.is_greedy), None)

        # 如果只有一个参数且是 greedy 或 positional，直接将整个 raw_args 作为值
        if len(params) == 1 and (params[0].is_greedy or params[0].is_positional):
            return {params[0].name: cls._convert_type(raw_args, params[0])}

        # 词法分析
        tokens = cls._tokenize(raw_args)

        # 分离 K-V 对和位置值
        kv_args: dict[str, str] = {}
        positional_values: list[str] = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            # 检查是否为 K-V 格式: key:value 或 key:"value"
            kv = cls._try_parse_kv(token)
            if kv:
                key, value = kv
                # 验证 key 是已知参数
                if any(p.name == key for p in params):
                    kv_args[key] = value
                else:
                    # 未知 key，视为位置参数
                    positional_values.append(token)
            else:
                # 如果这是最后的 token 且有 greedy 参数未填充
                if greedy_param and greedy_param.name not in kv_args:
                    # 将剩余所有原始文本作为 greedy 参数的值
                    remaining = " ".join(tokens[i:])
                    kv_args[greedy_param.name] = remaining
                    break
                positional_values.append(token)
            i += 1

        # 填充结果
        result: dict[str, Any] = {}

        # 1. 先填充 K-V 指定的参数
        for key, value in kv_args.items():
            param = next((p for p in params if p.name == key), None)
            if param:
                result[key] = cls._convert_type(value, param)

        # 2. 按位置填充 positional 参数
        positional_params = [p for p in params if p.is_positional and p.name not in result]
        for idx, param in enumerate(positional_params):
            if idx < len(positional_values):
                result[param.name] = cls._convert_type(positional_values[idx], param)

        # 3. 填充默认值
        for p in params:
            if p.name not in result:
                if p.is_required:
                    raise ValueError(f"缺少必填参数: {p.name}" + (f" ({p.arg_meta.description})" if p.arg_meta else ""))
                result[p.name] = p.default

        return result

    @classmethod
    def extract_params_schema(cls, func: Callable) -> Optional[dict]:
        """从函数签名自动生成 JSON Schema (用于 Agent Tool-Use)"""
        params = cls._extract_params(func)
        if not params:
            return None

        properties: dict[str, Any] = {}
        required: list[str] = []

        for p in params:
            prop: dict[str, Any] = {}

            # 类型映射
            prop["type"] = cls._type_to_json_schema(p.annotation)

            if p.arg_meta:
                if p.arg_meta.description:
                    prop["description"] = p.arg_meta.description
                if p.arg_meta.choices:
                    prop["enum"] = p.arg_meta.choices
                if p.arg_meta.prompt_hint:
                    prop["x-prompt-hint"] = p.arg_meta.prompt_hint

            if p.default is not _UNSET:
                prop["default"] = p.default
            else:
                required.append(p.name)

            properties[p.name] = prop

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    @classmethod
    def _extract_params(cls, func: Callable) -> list[_ParamInfo]:
        """从函数签名提取参数信息列表（跳过 self 和 context）"""
        sig = inspect.signature(func)
        hints = {}
        try:
            hints = get_type_hints(func, include_extras=True)
        except Exception:
            pass

        params: list[_ParamInfo] = []
        for name, param in sig.parameters.items():
            # 跳过 self、context 和 **kwargs
            if name in ("self", "context") or param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            annotation = hints.get(name, str)

            # 检查是否有 Annotated 中的 Arg
            arg_meta = None
            actual_type = annotation

            # 处理 Annotated[type, Arg(...)]
            if hasattr(annotation, "__metadata__"):
                actual_type = annotation.__args__[0]
                for meta in annotation.__metadata__:
                    if isinstance(meta, Arg):
                        arg_meta = meta
                        break

            # 检查默认值是否为 Arg 实例
            default = _UNSET
            if param.default is not inspect.Parameter.empty:
                if isinstance(param.default, Arg):
                    arg_meta = param.default
                    default = param.default.default
                else:
                    default = param.default

            # 如果从 Annotated 中提取了 Arg 但默认值不是 Arg，保留原始默认值
            if (
                arg_meta
                and default is _UNSET
                and param.default is not inspect.Parameter.empty
                and not isinstance(param.default, Arg)
            ):
                default = param.default

            params.append(
                _ParamInfo(
                    name=name,
                    annotation=actual_type,
                    arg_meta=arg_meta,
                    default=default,
                )
            )

        return params

    @classmethod
    def _tokenize(cls, raw_args: str) -> list[str]:
        """词法分析：支持引号和转义"""
        try:
            return shlex.split(raw_args)
        except ValueError:
            # 引号不匹配等情况，退回到空格分割
            return raw_args.split()

    @classmethod
    def _try_parse_kv(cls, token: str) -> Optional[tuple[str, str]]:
        """尝试解析 K-V 格式 (key:value)"""
        if ":" not in token:
            return None

        colon_idx = token.index(":")
        key = token[:colon_idx]
        value = token[colon_idx + 1 :]

        # key 必须是合法标识符
        if not key.isidentifier():
            return None

        # 去除 value 外层引号
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]

        return key, value

    @classmethod
    def _convert_type(cls, value: str, param: _ParamInfo) -> Any:
        """类型转换和约束校验"""
        target_type = param.annotation

        # bool 特殊处理
        if target_type is bool:
            return value.lower() in ("true", "1", "yes", "on")

        # int
        if target_type is int:
            try:
                result = int(value)
            except ValueError:
                raise ValueError(f"参数 {param.name} 需要整数类型") from None
            if param.arg_meta and param.arg_meta.range:
                min_val, max_val = param.arg_meta.range
                if not (min_val <= result <= max_val):
                    raise ValueError(f"参数 {param.name} 的值需在 {min_val}-{max_val} 之间")
            return result

        # float
        if target_type is float:
            try:
                result = float(value)
            except ValueError:
                raise ValueError(f"参数 {param.name} 需要数值类型") from None
            if param.arg_meta and param.arg_meta.range:
                min_val, max_val = param.arg_meta.range
                if not (min_val <= result <= max_val):
                    raise ValueError(f"参数 {param.name} 的值需在 {min_val}-{max_val} 之间")
            return result

        # choices 校验
        if param.arg_meta and param.arg_meta.choices and value not in param.arg_meta.choices:
            raise ValueError(f"参数 {param.name} 的值必须是 {param.arg_meta.choices} 之一")

        # str（默认）
        return value

    @classmethod
    def _type_to_json_schema(cls, annotation: type) -> str:
        """Python 类型 -> JSON Schema 类型"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
        }
        return type_map.get(annotation, "string")
