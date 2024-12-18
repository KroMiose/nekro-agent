from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Type, TypedDict, TypeVar, overload

from ..exceptions import NoSuchParameterError, StoreNotSetError
from ..scene import BaseScene, ModelResponse
from ..store import BaseStore

_BaseComponentParamsType = TypeVar(
    "_BaseComponentParamsType",
    bound="BaseComponentParams",
)


class BaseComponentParams:
    """组件参数基类"""

    _param_map: Dict[
        str,
        Tuple[str, BaseStore],
    ]  # 组件参数的映射，key 为参数名，value 为参数的来源 store 及 store 上的键

    def __init__(self):
        self._param_map = {}

    def bind(
        self: _BaseComponentParamsType,
        param_key: str,
        store_key: str,
        src_store: BaseStore,
    ) -> _BaseComponentParamsType:
        """把组件参数绑定到 store 上的键

        Args:
            param_key (str): 组件参数的键
            store_key (str): store 上的键
            src_store (BaseStore): 组件参数的来源 store. Defaults to None.

        Raises:
            NoSuchParameterError: 组件参数或 store 上没有该参数

        Returns:
            BaseComponentParams: 组件参数实例
        """
        if not hasattr(src_store, store_key):
            raise NoSuchParameterError(f"store `{src_store}` has no key `{store_key}`")
        self._param_map[param_key] = (store_key, src_store)
        return self

    def __getattribute__(self, name: str) -> Any:
        """获取组件参数的值

        优先从绑定 store 上的键获取参数值，如果没有绑定，则从组件实例属性获取参数值

        Args:
            name (str): 组件参数的键
        """
        if name in ["_param_map", "_scene", "_params"]:
            return super().__getattribute__(name)
        if name in self._param_map:
            store_key, src_store = self._param_map[name]
            return src_store.get(store_key)
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """设置组件参数的值

        优先设置绑定 store 上的键的值，如果没有绑定，则设置组件实例属性的值

        Args:
            name (str): 组件参数的键
            value (Any): 组件参数的值
        """
        if name in ["_param_map", "_scene", "_params"]:
            super().__setattr__(name, value)
        elif name in self._param_map:
            store_key, src_store = self._param_map[name]
            src_store.set(store_key, value)
        else:
            super().__setattr__(name, value)


_BaseComponentType = TypeVar("_BaseComponentType", bound="BaseComponent")


class BaseComponent(ABC):

    _scene: BaseScene  # 组件所在的场景

    class Params(BaseComponentParams):
        pass

    def __init__(self, scene: BaseScene):
        self._param_map = {}
        self._scene = scene
        self._params = self.Params()

    @property
    def scene(self) -> BaseScene:
        """组件所在的场景"""
        return self._scene

    @property
    def params(self) -> "Params":
        """组件参数"""
        return self._params

    def bind(
        self: _BaseComponentType,
        param_key: str,
        store_key: str,
        src_store: Optional[BaseStore] = None,
    ) -> _BaseComponentType:
        """把组件的参数引用绑定到 store 上的键

        Args:
            param_key (str): 组件参数的键
            store_key (str): store 上的键
            src_store (Optional[BaseStore], optional): 组件参数的来源 store. Defaults to None.

        Raises:
            StoreNotSetError: 场景没有设置 store

        Returns:
            BaseComponent: 组件实例
        """
        _store = src_store if src_store else self._scene.store
        if _store is None:
            raise StoreNotSetError
        self._params.bind(param_key, store_key, _store)
        return self

    def batch_bind(
        self,
        src_store: Optional[BaseStore] = None,
        **kwargs,
    ):
        """批量绑定组件参数

        Args:
            **kwargs (Dict[str, str]): 组件参数的键和 store 上的键映射

        Returns:
            BaseComponent: 组件实例
        """
        _store = src_store if src_store else self._scene.store
        for param_key, store_key in kwargs.items():
            self.bind(param_key, store_key, _store)
        return self

    def setup(self: _BaseComponentType, *args, **kwargs) -> _BaseComponentType:  # noqa: ARG002
        """组件初始化"""
        return self

    @abstractmethod
    async def render(self, *args, **kwargs) -> str:
        """渲染组件"""

    @classmethod
    def resolve(
        cls: Type[_BaseComponentType],
        model_response: ModelResponse,
        use_data: Any = None,
    ) -> _BaseComponentType:
        """从 ModelResponse 创建组件实例"""
        cmp = cls(model_response.scene)
        cmp.setup()
        try:
            return cmp.resolve_from_text(response_text=model_response.response_text)
        except NotImplementedError:
            return cmp.resolve_from_data(data=use_data)

    def resolve_from_text(
        self: _BaseComponentType,
        response_text: str,
    ) -> _BaseComponentType:
        """从响应文本创建组件实例 (子类按需实现)"""
        raise NotImplementedError

    def resolve_from_data(self: _BaseComponentType, data: Any) -> _BaseComponentType:
        """自定义从任意数据创建组件实例的逻辑 (子类按需实现)"""
        raise NotImplementedError
