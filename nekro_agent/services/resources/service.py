import re
from collections import Counter
from typing import Iterable

from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.models.db_workspace_resource import DBWorkspaceResource
from nekro_agent.models.db_workspace_resource_binding import DBWorkspaceResourceBinding
from nekro_agent.schemas.errors import ConflictError, NotFoundError, ValidationError
from nekro_agent.schemas.workspace_resource import (
    BoundWorkspaceInfo,
    ResourceField,
    ResourceTemplate,
    WorkspaceResourceBinding,
    WorkspaceResourceConflict,
    WorkspaceResourceCreate,
    WorkspaceResourceDetail,
    WorkspaceResourceSummary,
    WorkspaceResourceUpdate,
)
from nekro_agent.services.resources.crypto import decrypt_secret_payload, encrypt_secret_payload
from nekro_agent.services.resources.registry import get_resource_template


class WorkspaceResourceService:
    _RESOURCE_KEY_RE = re.compile(r"[^a-z0-9]+")
    _ENV_NAME_RE = re.compile(r"[^A-Z0-9]+")

    def _slugify(self, value: str, *, upper: bool = False) -> str:
        normalized = value.strip().lower()
        normalized = self._RESOURCE_KEY_RE.sub("-", normalized).strip("-")
        if not normalized:
            normalized = "resource"
        if upper:
            env = self._ENV_NAME_RE.sub("_", normalized.upper()).strip("_")
            return env or "RESOURCE"
        return normalized

    def _ensure_unique_resource_key(self, name: str, existing_keys: Iterable[str]) -> str:
        base = self._slugify(name)
        existing = set(existing_keys)
        if base not in existing:
            return base
        idx = 2
        while f"{base}-{idx}" in existing:
            idx += 1
        return f"{base}-{idx}"

    def _normalize_field(self, field: ResourceField, index: int, existing_keys: set[str]) -> ResourceField:
        field = field.model_copy(deep=True)
        field.label = field.label.strip()
        if not field.label:
            raise ValidationError(reason="资源字段名称不能为空")
        if not field.field_key:
            field.field_key = self._slugify(field.label).replace("-", "_")
        field.field_key = self._slugify(field.field_key).replace("-", "_")
        if not field.field_key:
            field.field_key = f"field_{index + 1}"
        original_key = field.field_key
        suffix = 2
        while field.field_key in existing_keys:
            field.field_key = f"{original_key}_{suffix}"
            suffix += 1
        existing_keys.add(field.field_key)
        field.order = index * 10 + 10 if field.order <= 0 else field.order
        field.fixed_aliases = [alias.strip().upper() for alias in field.fixed_aliases if alias.strip()]
        return field

    def _sorted_fields(self, fields: list[ResourceField]) -> list[ResourceField]:
        return sorted(fields, key=lambda item: (item.order, item.label))

    def _split_payload(self, fields: list[ResourceField]) -> tuple[dict[str, str], dict[str, str]]:
        public_payload: dict[str, str] = {}
        secret_payload: dict[str, str] = {}
        for field in fields:
            if field.value:
                if field.secret:
                    secret_payload[field.field_key] = field.value
                else:
                    public_payload[field.field_key] = field.value
        return public_payload, secret_payload

    def _merge_field_values(self, fields: list[ResourceField], public_payload: dict[str, str], secret_payload: dict[str, str]) -> list[ResourceField]:
        result: list[ResourceField] = []
        for field in self._sorted_fields(fields):
            field = field.model_copy(deep=True)
            if field.secret:
                field.value = secret_payload.get(field.field_key, "")
            else:
                field.value = public_payload.get(field.field_key, "")
            result.append(field)
        return result

    async def _build_summary(self, resource: DBWorkspaceResource) -> WorkspaceResourceSummary:
        fields = [ResourceField.model_validate(item) for item in (resource.schema_json or [])]
        bindings = await DBWorkspaceResourceBinding.filter(resource_id=resource.id).all()
        workspace_ids = [item.workspace_id for item in bindings]
        workspaces = await DBWorkspace.filter(id__in=workspace_ids).all() if workspace_ids else []
        workspace_map = {item.id: item for item in workspaces}
        fixed_aliases = sorted({alias for field in fields for alias in field.fixed_aliases})
        return WorkspaceResourceSummary(
            id=resource.id,
            resource_key=resource.resource_key,
            name=resource.name,
            template_key=resource.template_key,
            resource_note=resource.resource_note,
            resource_tags=list(resource.resource_tags_json or []),
            resource_prompt=resource.resource_prompt,
            field_count=len(fields),
            fixed_aliases=fixed_aliases,
            enabled=resource.enabled,
            bound_workspace_count=len(bindings),
            bound_workspaces=[
                BoundWorkspaceInfo(id=workspace_id, name=workspace_map[workspace_id].name)
                for workspace_id in workspace_ids
                if workspace_id in workspace_map
            ],
            create_time=resource.create_time.isoformat(),
            update_time=resource.update_time.isoformat(),
        )

    async def _build_detail(self, resource: DBWorkspaceResource) -> WorkspaceResourceDetail:
        summary = await self._build_summary(resource)
        fields = [ResourceField.model_validate(item) for item in (resource.schema_json or [])]
        secret_payload = decrypt_secret_payload(resource.secret_payload_encrypted)
        merged_fields = self._merge_field_values(fields, dict(resource.public_payload or {}), secret_payload)
        return WorkspaceResourceDetail(**summary.model_dump(), fields=merged_fields)

    async def list_resources(self) -> list[WorkspaceResourceSummary]:
        resources = await DBWorkspaceResource.all().order_by("name", "id")
        return [await self._build_summary(item) for item in resources]

    async def get_resource_or_404(self, resource_id: int) -> DBWorkspaceResource:
        resource = await DBWorkspaceResource.get_or_none(id=resource_id)
        if resource is None:
            raise NotFoundError(resource=f"工作区资源 {resource_id}")
        return resource

    async def get_resource_detail(self, resource_id: int) -> WorkspaceResourceDetail:
        resource = await self.get_resource_or_404(resource_id)
        return await self._build_detail(resource)

    def build_from_template(self, template: ResourceTemplate) -> WorkspaceResourceCreate:
        return WorkspaceResourceCreate(
            name=template.name,
            template_key=template.key,
            resource_note=template.resource_note,
            resource_tags=list(template.resource_tags),
            resource_prompt=template.resource_prompt,
            fields=[field.model_copy(deep=True) for field in template.fields],
            enabled=True,
        )

    async def create_resource(self, body: WorkspaceResourceCreate) -> WorkspaceResourceDetail:
        existing_keys = await DBWorkspaceResource.all().values_list("resource_key", flat=True)
        resource_key = self._ensure_unique_resource_key(body.name, existing_keys)
        fields = self._prepare_fields(body.fields, template_key=body.template_key)
        public_payload, secret_payload = self._split_payload(fields)
        resource = await DBWorkspaceResource.create(
            resource_key=resource_key,
            name=body.name.strip(),
            template_key=body.template_key,
            resource_note=body.resource_note.strip(),
            resource_tags_json=body.resource_tags,
            resource_prompt=body.resource_prompt.strip(),
            schema_json=[field.model_dump(exclude={"value"}) for field in fields],
            public_payload=public_payload,
            secret_payload_encrypted=encrypt_secret_payload(secret_payload),
            enabled=body.enabled,
        )
        return await self._build_detail(resource)

    async def update_resource(self, resource_id: int, body: WorkspaceResourceUpdate) -> WorkspaceResourceDetail:
        resource = await self.get_resource_or_404(resource_id)
        fields = self._prepare_fields(body.fields, template_key=body.template_key)
        public_payload, secret_payload = self._split_payload(fields)
        resource.name = body.name.strip()
        resource.template_key = body.template_key
        resource.resource_note = body.resource_note.strip()
        resource.resource_tags_json = body.resource_tags
        resource.resource_prompt = body.resource_prompt.strip()
        resource.schema_json = [field.model_dump(exclude={"value"}) for field in fields]
        resource.public_payload = public_payload
        resource.secret_payload_encrypted = encrypt_secret_payload(secret_payload)
        resource.enabled = body.enabled
        await resource.save()
        await self.refresh_related_workspace_caches(resource.id)
        return await self._build_detail(resource)

    async def delete_resource(self, resource_id: int, *, remove_bindings: bool = False) -> None:
        resource = await self.get_resource_or_404(resource_id)
        bindings = await DBWorkspaceResourceBinding.filter(resource_id=resource_id).all()
        if bindings and not remove_bindings:
            raise ValidationError(reason=f"该资源仍被 {len(bindings)} 个工作区引用，无法删除")
        workspace_ids = [binding.workspace_id for binding in bindings]
        for binding in bindings:
            await binding.delete()
        await resource.delete()
        for workspace_id in workspace_ids:
            await self.refresh_workspace_cache(workspace_id)

    def _prepare_fields(self, fields: list[ResourceField], *, template_key: str | None) -> list[ResourceField]:
        if not fields and template_key:
            template = get_resource_template(template_key)
            if template is not None:
                fields = [field.model_copy(deep=True) for field in template.fields]
        if not fields:
            raise ValidationError(reason="资源至少需要一个字段")
        existing_keys: set[str] = set()
        normalized = [self._normalize_field(field, index, existing_keys) for index, field in enumerate(self._sorted_fields(fields))]
        return normalized

    def _build_env_name(self, resource_key: str, field_key: str) -> str:
        return f"NEKRO_RESOURCE_{self._slugify(resource_key, upper=True)}_{self._slugify(field_key, upper=True)}"

    async def check_bind_conflicts(self, workspace_id: int, resource_id: int) -> list[WorkspaceResourceConflict]:
        target = await self.get_resource_or_404(resource_id)
        target_fields = [ResourceField.model_validate(item) for item in (target.schema_json or [])]
        target_aliases = {alias for field in target_fields for alias in field.fixed_aliases}
        if not target_aliases:
            return []
        bindings = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id, enabled=True).all()
        if not bindings:
            return []
        resource_ids = [item.resource_id for item in bindings if item.resource_id != resource_id]
        existing_resources = await DBWorkspaceResource.filter(id__in=resource_ids, enabled=True).all()
        conflicts: list[WorkspaceResourceConflict] = []
        for resource in existing_resources:
            fields = [ResourceField.model_validate(item) for item in (resource.schema_json or [])]
            aliases = {alias for field in fields for alias in field.fixed_aliases}
            for alias in sorted(target_aliases & aliases):
                conflicts.append(
                    WorkspaceResourceConflict(
                        env_name=alias,
                        existing_resource_id=resource.id,
                        existing_resource_name=resource.name,
                        target_resource_id=target.id,
                        target_resource_name=target.name,
                    )
                )
        return conflicts

    async def bind_resource(self, workspace_id: int, resource_id: int, *, note: str = "") -> WorkspaceResourceBinding:
        workspace = await DBWorkspace.get_or_none(id=workspace_id)
        if workspace is None:
            raise NotFoundError(resource=f"工作区 {workspace_id}")
        resource = await self.get_resource_or_404(resource_id)
        conflicts = await self.check_bind_conflicts(workspace_id, resource_id)
        if conflicts:
            first = conflicts[0]
            raise ValidationError(
                reason=(
                    f"注入环境变量 {first.env_name} 与资源“{first.existing_resource_name}”冲突，"
                    "请不要在同一工作区绑定这两条资源"
                )
            )
        existing = await DBWorkspaceResourceBinding.get_or_none(workspace_id=workspace_id, resource_id=resource_id)
        if existing is not None:
            raise ConflictError(resource=f"工作区资源绑定 {workspace_id}/{resource_id}")
        current_max = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id).order_by("-sort_order").first()
        sort_order = (current_max.sort_order if current_max else 0) + 10
        binding = await DBWorkspaceResourceBinding.create(
            workspace_id=workspace_id,
            resource_id=resource_id,
            enabled=resource.enabled,
            sort_order=sort_order,
            note=note.strip(),
        )
        await self.refresh_workspace_cache(workspace_id)
        return await self._build_binding(binding, resource=resource)

    async def _build_binding(self, binding: DBWorkspaceResourceBinding, *, resource: DBWorkspaceResource | None = None) -> WorkspaceResourceBinding:
        resource = resource or await self.get_resource_or_404(binding.resource_id)
        return WorkspaceResourceBinding(
            binding_id=binding.id,
            resource_id=resource.id,
            enabled=binding.enabled,
            sort_order=binding.sort_order,
            note=binding.note,
            resource=await self._build_summary(resource),
        )

    async def list_workspace_bindings(self, workspace_id: int) -> list[WorkspaceResourceBinding]:
        bindings = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id).order_by("sort_order", "id")
        if not bindings:
            return []
        resources = await DBWorkspaceResource.filter(id__in=[item.resource_id for item in bindings]).all()
        resource_map = {item.id: item for item in resources}
        return [await self._build_binding(binding, resource=resource_map[binding.resource_id]) for binding in bindings if binding.resource_id in resource_map]

    async def unbind_resource(self, workspace_id: int, resource_id: int) -> None:
        binding = await DBWorkspaceResourceBinding.get_or_none(workspace_id=workspace_id, resource_id=resource_id)
        if binding is None:
            raise NotFoundError(resource=f"工作区资源绑定 {workspace_id}/{resource_id}")
        await binding.delete()
        await self.refresh_workspace_cache(workspace_id)

    async def reorder_bindings(self, workspace_id: int, binding_ids: list[int]) -> None:
        bindings = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id, id__in=binding_ids).all()
        binding_map = {item.id: item for item in bindings}
        if len(binding_map) != len(binding_ids):
            raise ValidationError(reason="资源排序数据不完整")
        for index, binding_id in enumerate(binding_ids, start=1):
            binding = binding_map[binding_id]
            binding.sort_order = index * 10
            await binding.save(update_fields=["sort_order", "update_time"])
        await self.refresh_workspace_cache(workspace_id)

    async def resolve_workspace_resources_to_env(self, workspace_id: int) -> dict[str, str]:
        bindings = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id, enabled=True).order_by("sort_order", "id")
        if not bindings:
            return {}
        resources = await DBWorkspaceResource.filter(id__in=[item.resource_id for item in bindings], enabled=True).all()
        resource_map = {item.id: item for item in resources}
        env_vars: dict[str, str] = {}
        alias_counter: Counter[str] = Counter()
        for binding in bindings:
            resource = resource_map.get(binding.resource_id)
            if resource is None:
                continue
            fields = [ResourceField.model_validate(item) for item in (resource.schema_json or [])]
            secret_payload = decrypt_secret_payload(resource.secret_payload_encrypted)
            public_payload = dict(resource.public_payload or {})
            for field in fields:
                if field.export_mode != "env":
                    continue
                value = secret_payload.get(field.field_key, "") if field.secret else public_payload.get(field.field_key, "")
                if not value:
                    continue
                env_name = self._build_env_name(resource.resource_key, field.field_key)
                env_vars[env_name] = value
                for alias in field.fixed_aliases:
                    alias_counter[alias] += 1
                    if alias in env_vars and env_vars[alias] != value:
                        raise ValidationError(reason=f"工作区资源注入环境变量 {alias} 冲突")
                    env_vars[alias] = value
        duplicated = [alias for alias, count in alias_counter.items() if count > 1]
        if duplicated:
            raise ValidationError(reason=f"工作区资源注入环境变量冲突: {', '.join(sorted(duplicated))}")
        return env_vars

    async def _build_workspace_prompt_section(self, workspace_id: int) -> tuple[str, str]:
        bindings = await self.list_workspace_bindings(workspace_id)
        if not bindings:
            return "", "（当前工作区未绑定任何工作区资源）"
        summary_lines = []
        prompt_lines = ["## 可用工作区资源", ""]
        for item in bindings:
            resource = item.resource
            summary_lines.append(f"- {resource.name}: {resource.resource_note or '已挂载工作区资源'}")
            detail = await self.get_resource_detail(resource.id)
            prompt_lines.append(f"### 资源：{detail.name}")
            for field in detail.fields:
                if field.export_mode != "env":
                    continue
                env_name = self._build_env_name(detail.resource_key, field.field_key)
                env_names = [*field.fixed_aliases, env_name] if field.fixed_aliases else [env_name]
                env_text = "、".join(f"`{name}`" for name in env_names)
                if field.secret:
                    prompt_lines.append(f"- {field.label}：已注入环境变量 {env_text}")
                else:
                    value_text = f"`{field.value}`" if field.value else "（未填写）"
                    prompt_lines.append(f"- {field.label}：{value_text}")
                    prompt_lines.append(f"  已注入环境变量：{env_text}")
            if detail.resource_prompt:
                prompt_lines.append(f"- 使用方式：{detail.resource_prompt}")
            prompt_lines.append("")
        return "\n".join(prompt_lines).strip(), "\n".join(summary_lines)

    async def refresh_workspace_cache(self, workspace_id: int) -> None:
        workspace = await DBWorkspace.get_or_none(id=workspace_id)
        if workspace is None:
            return
        prompt_text, summary_text = await self._build_workspace_prompt_section(workspace_id)
        metadata = dict(workspace.metadata or {})
        metadata["resource_prompt_cache"] = prompt_text
        metadata["resource_summary_cache"] = summary_text
        metadata["resource_count_cache"] = await DBWorkspaceResourceBinding.filter(workspace_id=workspace_id).count()
        workspace.metadata = metadata
        await workspace.save(update_fields=["metadata", "update_time"])
        from nekro_agent.services.workspace.manager import WorkspaceService

        WorkspaceService.update_claude_md(workspace)

    async def refresh_related_workspace_caches(self, resource_id: int) -> None:
        workspace_ids = await DBWorkspaceResourceBinding.filter(resource_id=resource_id).values_list("workspace_id", flat=True)
        for workspace_id in workspace_ids:
            await self.refresh_workspace_cache(int(workspace_id))


workspace_resource_service = WorkspaceResourceService()
