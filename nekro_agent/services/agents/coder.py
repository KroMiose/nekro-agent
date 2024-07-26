from typing import List

from miose_toolkit_llm import (
    BaseScene,
    BaseStore,
    ModelResponse,
    Runner,
)
from miose_toolkit_llm.clients.chat_openai import OpenAIChatClient
from miose_toolkit_llm.components import (
    BaseComponent,  # 基础组件
    JsonResolverComponent,  # JSON 解析组件
    TextComponent,  # 文本提示词组件
    VecFunctionComponent,  # 支持向量数据库检索的方法组件
    VecHistoryComponent,  # 支持向量数据库检索的消息记录组件
)
from miose_toolkit_llm.creators.openai import (
    AiMessage,
    OpenAIPromptCreator,
    SystemMessage,
    UserMessage,
)
from miose_toolkit_llm.exceptions import (
    ComponentRuntimeError,
    ResolveError,
    SceneRuntimeError,
)
from miose_toolkit_llm.tools.tokenizers import TikTokenizer
from miose_toolkit_llm.tools.vector_dbs import ChomaVecDb


async def main():
    # 1. 构造一个应用场景

    class Scene(BaseScene):
        """场景类"""

        class Store(BaseStore):
            """场景数据源类"""

            history_key = "history"
            character = "艾丽娅"

    scene = Scene()
    store = scene.store  # 可获取场景数据源

    # 2. 准备场景组件
    vec_histories = VecHistoryComponent(scene=scene).setup(use=ChomaVecDb)  # 使用向量数据库检索的消息记录组件

    class ActionResponse(JsonResolverComponent):
        """自定义动作响应器"""

        reaction: str = ""
        options: List[str] = []

    class CustomResponseResolver(JsonResolverComponent):
        """自定义结果解析器"""

        action_response: ActionResponse = ActionResponse(scene=scene)

    # custom_component = CustomComponent()  # 自定义组件 (需要继承 BaseComponent，实现 render_prompt 方法)

    # 3. 构造 OpenAI 提示词
    prompt_creator = OpenAIPromptCreator(
        SystemMessage(
            "你是",
            "你的响应结果应该符合以下格式：",
            CustomResponseResolver.example(),  # 生成一个解析结果示例
            sep="\n\n",  # 自定义构建 prompt 的分隔符 默认为 "\n"
        ),
        UserMessage(
            vec_histories.bind_collection_name(collection_name="history_key"),
            TextComponent(
                "我想扮演一位 {character}",
                src_store=store,  # 指定渲染数据源，否则使用场景数据源
            ),
        ),
        # 生成使用的参数
        temperature=0.3,
        max_tokens=1000,
        presence_penalty=0.3,
        frequency_penalty=0.5,
    )

    scene.attach_runner(  # 为场景绑定 LLM 执行器
        Runner(
            client=OpenAIChatClient(model="gpt-3.5-turbo"),  # 指定聊天客户端
            tokenizer=TikTokenizer(model="gpt-3.5-turbo"),  # 指定分词器
            prompt_creator=prompt_creator,
        ),
    )

    # 4. 获取结果与解析
    try:
        mr: ModelResponse = await scene.run()
        _ = mr.response_text  # 原始结果文本 (按需获取)
    except SceneRuntimeError as e:
        print(e)
        raise

    try:
        resolved_response: CustomResponseResolver = CustomResponseResolver.resolve(
            model_response=mr,
        )  # 使用指定解析器解析结果
    except ResolveError as e:
        print(e)
        raise

    _ = resolved_response.action_response.reaction  # 结果:

    # 5. 反馈与保存数据 (可选)
    mr.save(
        prompt_file="temp/chat_prompt.txt",
        response_file="temp/chat_response.json",
    )  # 保存响应提示词和结果到文件 (可选)
    mr.feedback(rate=5)  # 反馈生成质量到数据平台 (可选)
    assert True  # 断言成功
