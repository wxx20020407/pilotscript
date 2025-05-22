import gradio as gr
from dataclasses import dataclass
from typing import List, Any, TypeVar, Optional, Callable


@dataclass
class UIBoundData:
    pass


UI_Data = TypeVar("UI_Data", bound=UIBoundData)


@dataclass
class CustomUI:
    def __init__(self, bound_data: UI_Data):
        super().__init__()
        self.components = {}
        self.bound_data = bound_data

    def register(self,
                 comp_name: str,
                 component: gr.components.Component,
                 get_bound_data_fn: Optional[Callable[[UI_Data], Any]] = None) -> gr.components.Component:
        """注册组件并指定更新属性方法
        :param comp_name: 组件唯一名称
        :param component: Gradio组件实例
        :param get_bound_data_fn: 组件绑定数据获取方法
        """
        self.components[comp_name] = (component, get_bound_data_fn)

        return component

    def get_component(self, comp_name: str):
        return self.components[comp_name][0]

    def get_components(self, comp_names: List[str]):
        return [self.get_component(n) for n in comp_names]

    def generate_updates(
            self,
            update_components: List[str]) -> List[gr.Component]:
        """生成Gradio组件的update字典
        :param update_components: 需要更新属性的组件名称集合
        """
        updates = []
        for comp_name in update_components:
            comp, bound_fn = self.components.get(comp_name)
            data = bound_fn(self.bound_data) if self.bound_data and bound_fn else None
            updates.append(self._create_update(comp, data))
        return updates

    @staticmethod
    def _create_update(component: gr.components.Component, data: Any) -> Optional[gr.Component]:
        """创建单个组件的update字典"""
        if isinstance(component, gr.components.Dropdown):
            return gr.Dropdown(choices=data if data is not None else [], value='')
        # TODO: 实现更多组件更新字段绑定
        else:
            return type(component)(value=data)
