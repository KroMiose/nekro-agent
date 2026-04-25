from copy import deepcopy

from nekro_agent.schemas.workspace_resource import ResourceField, ResourceTemplate


def _field(
    *,
    field_key: str,
    label: str,
    description: str,
    value_kind: str,
    order: int,
    secret: bool = False,
    fixed_aliases: list[str] | None = None,
) -> ResourceField:
    return ResourceField(
        field_key=field_key,
        label=label,
        description=description,
        value_kind=value_kind,  # type: ignore[arg-type]
        order=order,
        secret=secret,
        fixed_aliases=fixed_aliases or [],
    )


_TEMPLATES: list[ResourceTemplate] = [
    ResourceTemplate(
        key="server_ssh_key",
        name="SSH 密钥连接",
        summary="适用于使用用户名 + 私钥登录远程服务器的场景。",
        resource_note="适用于部署、巡检、日志排查等需要通过 SSH 密钥访问服务器的任务。",
        resource_tags=["ssh", "ops", "deploy"],
        resource_prompt="需要访问远程服务器执行巡检、部署或日志排查时，直接使用已注入的主机、用户名与私钥环境变量即可。",
        fields=[
            _field(field_key="host", label="主机地址", description="服务器地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="SSH 端口，通常为 22", value_kind="port", order=20),
            _field(field_key="username", label="用户名", description="SSH 登录用户名", value_kind="username", order=30),
            _field(field_key="private_key", label="私钥", description="SSH 私钥内容", value_kind="private_key", order=40, secret=True),
            _field(field_key="passphrase", label="口令短语", description="如私钥存在口令短语可填写", value_kind="password", order=50, secret=True),
        ],
    ),
    ResourceTemplate(
        key="server_ssh_password",
        name="SSH 密码连接",
        summary="适用于使用用户名 + 密码登录远程服务器的场景。",
        resource_note="适用于通过 SSH 密码方式访问服务器的常规运维任务。",
        resource_tags=["ssh", "ops", "deploy"],
        resource_prompt="需要通过 SSH 密码方式访问服务器时，直接使用已注入的主机、用户名和密码环境变量即可。",
        fields=[
            _field(field_key="host", label="主机地址", description="服务器地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="SSH 端口，通常为 22", value_kind="port", order=20),
            _field(field_key="username", label="用户名", description="SSH 登录用户名", value_kind="username", order=30),
            _field(field_key="password", label="密码", description="SSH 登录密码", value_kind="password", order=40, secret=True),
        ],
    ),
    ResourceTemplate(
        key="server_root_password",
        name="Root 密码连接",
        summary="适用于使用 root 账号密码直接访问服务器的场景。",
        resource_note="适用于临时抢修、初始化环境或遗留环境运维。",
        resource_tags=["ssh", "ops", "admin"],
        resource_prompt="仅在明确需要 root 权限执行系统级操作时使用该资源；除非任务明确要求，否则应避免破坏性操作。",
        fields=[
            _field(field_key="host", label="主机地址", description="服务器地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="SSH 端口，通常为 22", value_kind="port", order=20),
            _field(field_key="password", label="Root 密码", description="root 登录密码", value_kind="password", order=30, secret=True),
        ],
    ),
    ResourceTemplate(
        key="postgres_connection",
        name="PostgreSQL 连接",
        summary="适用于连接 PostgreSQL 数据库进行排查或维护的场景。",
        resource_note="可用于读取配置、执行只读 SQL、检查连接状态或导出结构。",
        resource_tags=["database", "postgres", "sql"],
        resource_prompt="需要连接 PostgreSQL 排查问题时，直接使用已注入的连接参数；除非任务明确要求，否则不要执行破坏性写操作。",
        fields=[
            _field(field_key="host", label="主机地址", description="数据库地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="数据库端口，通常为 5432", value_kind="port", order=20),
            _field(field_key="database", label="数据库名", description="要连接的数据库名称", value_kind="database", order=30),
            _field(field_key="username", label="用户名", description="数据库用户名", value_kind="username", order=40),
            _field(field_key="password", label="密码", description="数据库密码", value_kind="password", order=50, secret=True),
        ],
    ),
    ResourceTemplate(
        key="mysql_connection",
        name="MySQL 连接",
        summary="适用于连接 MySQL 数据库进行排查或维护的场景。",
        resource_note="可用于读取配置、执行只读 SQL、检查连接状态或导出结构。",
        resource_tags=["database", "mysql", "sql"],
        resource_prompt="需要连接 MySQL 排查问题时，直接使用已注入的连接参数；除非任务明确要求，否则不要执行破坏性写操作。",
        fields=[
            _field(field_key="host", label="主机地址", description="数据库地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="数据库端口，通常为 3306", value_kind="port", order=20),
            _field(field_key="database", label="数据库名", description="要连接的数据库名称", value_kind="database", order=30),
            _field(field_key="username", label="用户名", description="数据库用户名", value_kind="username", order=40),
            _field(field_key="password", label="密码", description="数据库密码", value_kind="password", order=50, secret=True),
        ],
    ),
    ResourceTemplate(
        key="redis_connection",
        name="Redis 连接",
        summary="适用于连接 Redis 进行检查或运维的场景。",
        resource_note="可用于检查缓存状态、键空间或配置。",
        resource_tags=["database", "redis", "cache"],
        resource_prompt="需要检查 Redis 状态或配置时，直接使用已注入的连接参数；除非明确要求，不要清空或删除关键数据。",
        fields=[
            _field(field_key="host", label="主机地址", description="Redis 地址或域名", value_kind="host", order=10),
            _field(field_key="port", label="端口", description="Redis 端口，通常为 6379", value_kind="port", order=20),
            _field(field_key="password", label="密码", description="Redis 访问密码", value_kind="password", order=30, secret=True),
            _field(field_key="database", label="数据库序号", description="Redis DB 编号", value_kind="text", order=40),
        ],
    ),
    ResourceTemplate(
        key="github_cli_credential",
        name="GitHub CLI 凭证",
        summary="适用于 gh CLI、GitHub 仓库操作、PR 和 Actions 排查。",
        resource_note="该模板为 GitHub CLI 和常见 GitHub API 访问场景提供兼容令牌。",
        resource_tags=["github", "git", "gh_cli"],
        resource_prompt="执行 gh 命令、查看 GitHub Actions、创建 PR 或读取仓库信息时，可直接使用当前账号，无需额外导出认证变量。",
        fields=[
            _field(
                field_key="token",
                label="访问令牌",
                description="GitHub 访问令牌",
                value_kind="password",
                order=10,
                secret=True,
                fixed_aliases=["GH_TOKEN", "GITHUB_TOKEN"],
            ),
            _field(field_key="username", label="账号名称", description="该令牌对应的 GitHub 账号名称", value_kind="username", order=20),
        ],
    ),
    ResourceTemplate(
        key="generic_token_credential",
        name="通用令牌凭证",
        summary="适用于仅需单个令牌即可访问外部服务的场景。",
        resource_note="适用于自定义 API、第三方平台或令牌型凭证管理。",
        resource_tags=["token", "api"],
        resource_prompt="调用仅需单个访问令牌的外部服务时，直接使用已注入的认证环境变量即可。",
        fields=[
            _field(field_key="token", label="访问令牌", description="服务访问令牌", value_kind="password", order=10, secret=True),
            _field(field_key="base_url", label="服务地址", description="服务基础地址，可选", value_kind="text", order=20),
        ],
    ),
    ResourceTemplate(
        key="username_password_credential",
        name="账号密码凭证",
        summary="适用于通过用户名和密码访问外部系统的场景。",
        resource_note="适用于遗留系统、后台管理平台或普通账户凭证。",
        resource_tags=["account", "login"],
        resource_prompt="登录外部系统且通过用户名密码认证时，直接使用已注入的账号与密码环境变量即可。",
        fields=[
            _field(field_key="username", label="账号", description="登录账号", value_kind="username", order=10),
            _field(field_key="password", label="密码", description="登录密码", value_kind="password", order=20, secret=True),
            _field(field_key="base_url", label="服务地址", description="登录入口地址，可选", value_kind="text", order=30),
        ],
    ),
]


def get_resource_templates() -> list[ResourceTemplate]:
    return [deepcopy(item) for item in _TEMPLATES]


def get_resource_template(template_key: str) -> ResourceTemplate | None:
    for item in _TEMPLATES:
        if item.key == template_key:
            return deepcopy(item)
    return None
