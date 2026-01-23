# Agent 架构深度解析 - 所有函数细节与设计思路

> 本文档详细解析每个核心模块的设计思路、函数职责、数据流向

---

## 目录

1. [Orchestrator - 对话控制器](#1-orchestrator)
2. [Spec Manager - 意图管理器](#2-spec-manager)
3. [Compiler - 编译器](#3-compiler)
4. [Planner - 任务规划器](#4-planner)
5. [Executor - 执行器](#5-executor)
6. [Validator - 验证器](#6-validator)
7. [Builder - 构建器](#7-builder)
8. [Error Fixer - 错误修复器](#8-error-fixer)

---

## 1. Orchestrator

**文件**: `backend/agents/core/orchestrator.py`

### 📌 整体思路

**核心职责**: 将人类自然语言转换为结构化的SpecDelta

**设计原则**:
- 这是系统唯一理解自然语言的地方
- 所有下游模块接收的都是结构化数据
- 当意图模糊时，生成clarifying_questions而不是猜测

**数据流**:
```
用户prompt → LLM解析 → ParsedItem[] → SpecDelta[] → OrchestratorResponse
```

---

### 🔧 核心类与数据结构

#### 1. `OrchestratorResponse`
```python
class OrchestratorResponse(BaseModel):
    deltas: List[SpecDelta]           # 要应用的spec变更
    clarifying_questions: List[str]   # 需要用户澄清的问题
    reasoning: str                     # AI推理过程
    requires_user_input: bool          # 是否需要等待用户回答
```

**设计意图**:
- 允许系统在不确定时"停下来问"
- 避免错误猜测导致的错误积累

#### 2. `ConversationContext`
```python
class ConversationContext(BaseModel):
    user_prompts: List[str]           # 历史prompt
    decisions_made: List[str]         # 已做的决策
    ambiguities_resolved: List[str]   # 已解决的歧义
```

**设计意图**:
- 支持多轮对话
- 允许引用上下文（"make it rarer"中的"it"）
- **⚠️ 当前未使用，是待实现功能**

#### 3. `ParsedItem`（新增）
```python
class ParsedItem(BaseModel):
    type: str                         # item/block/tool
    name: str                         # 显示名称
    description: str                  # 描述
    rarity: str                       # 稀有度
    creative_tab: str                 # 创造模式标签
    special_ability: Optional[str]    # 特殊能力
    texture_description: Optional[str] # 纹理描述
    ambiguous_rarity: bool            # 稀有度是否模糊
    tool_type: Optional[str]          # 工具类型
```

#### 4. `ItemIntentParse`（重构后）
```python
class ItemIntentParse(BaseModel):
    items: List[ParsedItem]           # 支持多个item
    inferred_mod_name: str            # 推断的mod名称
```

**重要变更**:
- 从单个item改为items列表
- 支持"add a sword and shield"这种多物品请求

#### 5. `ModificationIntentParse`（新增）
```python
class ModificationIntentParse(BaseModel):
    operation: str                    # modify_property/add_item/remove_item等
    target: Optional[str]             # 修改目标（"first item"/"ruby sword"）
    target_index: Optional[int]       # 目标索引
    target_type: Optional[str]        # items/blocks/tools
    property_name: Optional[str]      # 要修改的属性
    property_value: Optional[Any]     # 新值
    new_item: Optional[ParsedItem]    # 新增的item（add操作）
    reasoning: str                    # 推理过程
```

---

### 🎯 核心函数详解

#### `__init__()`
```python
def __init__(self):
    self.llm = ChatGoogleGenerativeAI(
        google_api_key=GEMINI_API_KEY,
        model=AI_MODEL,
        temperature=AI_TEMPERATURE,
        max_retries=AI_MAX_RETRIES,
        request_timeout=AI_REQUEST_TIMEOUT,
        transport="rest"
    )
```

**职责**: 初始化LLM客户端

**关键设计**:
- `transport="rest"`: 使用REST而非gRPC，避免代理问题
- `temperature`: 控制创造性（太高会产生不一致结果）
- `max_retries`: LLM失败自动重试

---

#### `_format_reason(user_prompt: str, max_len: int = 100) -> str`
```python
@staticmethod
def _format_reason(user_prompt: str, max_len: int = 100) -> str:
    if len(user_prompt) <= max_len:
        return f"User requested: {user_prompt}"
    return f"User requested: {user_prompt[:max_len]}..."
```

**职责**: 统一格式化reason字段

**为什么需要**:
- 避免reason字段过长导致日志混乱
- 统一格式便于日志分析

**使用场景**:
```python
SpecDelta(
    operation="add",
    path="items[0]",
    value=item_spec.dict(),
    reason=self._format_reason(user_prompt)  # 使用统一格式
)
```

---

#### `process_prompt()` - 主入口函数

```python
def process_prompt(
    self,
    user_prompt: str,
    current_spec: Optional[ModSpec] = None,
    context: Optional[ConversationContext] = None,
    author_name: Optional[str] = None,
    mod_name_override: Optional[str] = None
) -> OrchestratorResponse:
```

**职责**: 根据当前状态选择处理路径

**决策逻辑**:
```python
if current_spec is None:
    # 首次创建 → 走初始化路径
    return self._handle_initial_prompt(...)
else:
    # 已有spec → 走修改路径
    return self._handle_iterative_prompt(...)
```

**设计意图**:
- 初始创建和迭代修改是两种完全不同的场景
- 初始创建：从零构建完整spec
- 迭代修改：基于现有spec做局部调整

**调用示例**:
```python
# 首次创建
response = orchestrator.process_prompt(
    user_prompt="Create a ruby sword",
    current_spec=None  # 没有spec
)

# 迭代修改
response = orchestrator.process_prompt(
    user_prompt="Make it epic rarity",
    current_spec=existing_spec  # 已有spec
)
```

---

#### `_handle_initial_prompt()` - 初始创建处理

```python
def _handle_initial_prompt(
    self,
    user_prompt: str,
    author_name: Optional[str],
    mod_name_override: Optional[str],
    context: ConversationContext
) -> OrchestratorResponse:
```

**职责**: 从零创建mod的初始spec

**核心流程**:

**Step 1**: 解析用户意图
```python
parsed = self._parse_item_intent(user_prompt)
# 返回: {"items": [ParsedItem1, ParsedItem2, ...], "inferred_mod_name": "..."}
```

**Step 2**: 创建mod元数据delta
```python
mod_name = mod_name_override or parsed.get("inferred_mod_name", "Custom Mod")
deltas.append(SpecDelta(
    operation="add",
    path="mod_name",
    value=mod_name,
    reason="User requested mod creation"
))
```

**Step 3**: 循环处理所有items
```python
items_list = parsed.get("items", [])
item_idx = 0
block_idx = 0
tool_idx = 0

for parsed_item in items_list:
    item_type = parsed_item.get("type", "item")

    if item_type == "item":
        item_spec = self._create_item_spec(parsed_item)
        deltas.append(SpecDelta(
            operation="add",
            path=f"items[{item_idx}]",  # 使用递增索引
            value=item_spec.dict(),
            reason=self._format_reason(user_prompt)
        ))
        item_idx += 1
```

**关键设计**:
- 为items/blocks/tools分别维护独立计数器
- 路径使用`items[0]`, `items[1]`而非`items[-1]`（明确位置）
- 每个item生成独立的delta（可单独回滚）

**Step 4**: 检查模糊性
```python
if parsed_item.get("ambiguous_rarity"):
    clarifying_questions.append(
        f"What rarity should {item_name} be? (COMMON, UNCOMMON, RARE, EPIC)"
    )
```

**返回值**:
```python
return OrchestratorResponse(
    deltas=deltas,                              # 所有变更
    clarifying_questions=clarifying_questions,  # 需要澄清的问题
    reasoning="...",                            # 推理过程
    requires_user_input=len(clarifying_questions) > 0  # 是否需要等待
)
```

---

#### `_handle_iterative_prompt()` - 迭代修改处理

```python
def _handle_iterative_prompt(
    self,
    user_prompt: str,
    current_spec: ModSpec,
    context: ConversationContext
) -> OrchestratorResponse:
```

**职责**: 基于现有spec进行修改

**核心流程**:

**Step 1**: 解析修改意图
```python
intent = self._parse_modification_intent(user_prompt, current_spec)
# 返回: {
#   "operation": "modify_property",
#   "path": "items[0].rarity",
#   "value": "EPIC"
# }
```

**Step 2**: 根据operation类型生成delta
```python
if operation == "modify_property":
    deltas.append(SpecDelta(
        operation="update",  # 注意是update不是add
        path=intent.get("path"),
        value=intent.get("value"),
        reason=self._format_reason(user_prompt)
    ))

elif operation == "add_item":
    new_item = self._create_item_spec(intent)
    deltas.append(SpecDelta(
        operation="add",
        path=f"items[{len(current_spec.items)}]",  # 追加到末尾
        value=new_item.dict(),
        reason=self._format_reason(user_prompt)
    ))
```

**关键设计**:
- `modify_property`: 使用`update`操作 + 精确路径
- `add_item`: 使用`add`操作 + 末尾索引
- 所有路径都是绝对路径，不依赖上下文

---

#### `_parse_item_intent()` - LLM意图解析

```python
def _parse_item_intent(self, prompt: str) -> Dict[str, Any]:
```

**职责**: 用LLM解析创建意图

**核心流程**:

**Step 1**: 构建LLM prompt
```python
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """You are a Minecraft mod design assistant. Parse the user's request and extract:
- What type of things they want (item, block, tool) - can be MULTIPLE items
- The name/description for each item
- Any properties mentioned (rarity, abilities, etc.)
- Inferred creative tab for each
- Suggested mod name

IMPORTANT: If the user asks for multiple items (e.g., "a sword and shield", "ruby ore and ruby ingot"),
return ALL of them in the items list. Be generous in interpretation. If unclear, make reasonable assumptions.
{format_instructions}"""),
    ("user", "{prompt}")
])
```

**关键设计**:
- 明确告诉LLM可以返回多个items
- 要求"generous interpretation"（宽容解释）
- 提供具体例子避免LLM误解

**Step 2**: 调用LLM
```python
chain = prompt_template | self.llm | parser

try:
    result = chain.invoke({
        "prompt": prompt,
        "format_instructions": parser.get_format_instructions()
    })
    return result.dict()
```

**Step 3**: Fallback处理
```python
except Exception as e:
    print(f"Warning: LLM parsing failed, using fallback. Error: {e}")
    return {
        "items": [{
            "type": "item",
            "name": prompt[:30] + "...",
            "description": prompt,
            "rarity": "COMMON",
            "creative_tab": "MISC",
            # ... 其他安全默认值
        }],
        "inferred_mod_name": "Custom Mod"
    }
```

**为什么需要fallback**:
1. LLM API可能失败（网络/配额）
2. LLM可能返回无效JSON
3. 保证系统永不崩溃

**fallback策略**:
- 使用prompt前30字符作为名称
- 所有属性使用最保守默认值
- 至少能生成一个可用item

---

#### `_parse_modification_intent()` - 修改意图解析

```python
def _parse_modification_intent(self, prompt: str, current_spec: ModSpec) -> Dict[str, Any]:
```

**职责**: 用LLM解析修改意图

**核心流程**:

**Step 1**: 构建spec上下文
```python
spec_context = f"""Current mod specification:
- Mod name: {current_spec.mod_name}
- Items: {len(current_spec.items)} items ({', '.join([item.item_name for item in current_spec.items[:3]])}{...})
- Blocks: {len(current_spec.blocks)} blocks (...)
- Tools: {len(current_spec.tools)} tools (...)"""
```

**为什么需要上下文**:
- 帮助LLM理解"first item"指的是哪个
- 帮助LLM理解"make it rarer"中的"it"
- 提供当前状态避免冲突

**Step 2**: 调用LLM
```python
result = chain.invoke({
    "spec_context": spec_context,
    "prompt": prompt,
    "format_instructions": parser.get_format_instructions()
})
parsed = result.dict()
```

**LLM返回示例**:
```json
{
  "operation": "modify_property",
  "target": "first item",
  "target_index": 0,
  "target_type": "items",
  "property_name": "rarity",
  "property_value": "EPIC",
  "reasoning": "User wants to increase rarity to epic"
}
```

**Step 3**: 转换为内部格式
```python
intent = {"operation": parsed["operation"]}

if parsed["operation"] == "modify_property":
    target_type = parsed.get("target_type", "items")
    target_index = parsed.get("target_index", 0)
    property_name = parsed.get("property_name", "rarity")

    intent["path"] = f"{target_type}[{target_index}].{property_name}"
    intent["value"] = parsed.get("property_value")
```

**关键转换**:
- LLM返回的是语义化描述（"first item"）
- 转换为精确路径（`items[0].rarity`）

**Step 4**: Fallback heuristics
```python
except Exception as e:
    # LLM失败时使用简单规则
    if "rare" in prompt_lower or "epic" in prompt_lower:
        return {
            "operation": "modify_property",
            "path": "items[0].rarity",
            "value": "EPIC" if "epic" in prompt_lower else "RARE"
        }
```

---

#### `_create_item_spec()` / `_create_block_spec()` / `_create_tool_spec()`

```python
def _create_item_spec(self, parsed: Dict[str, Any]) -> ItemSpec:
    return ItemSpec(
        item_name=parsed.get("name", "Custom Item"),
        description=parsed.get("description", "A custom item"),
        rarity=Rarity(parsed.get("rarity", "COMMON")),
        creative_tab=normalize_creative_tab(parsed.get("creative_tab", "MISC"), CreativeTab.MISC),
        special_ability=parsed.get("special_ability"),
        texture_description=parsed.get("texture_description")
    )
```

**职责**: 将LLM解析结果转换为类型安全的Spec对象

**关键设计**:
1. **类型转换**: `"COMMON"` → `Rarity.COMMON`
2. **归一化**: `normalize_creative_tab()` 处理legacy值
3. **默认值**: 所有字段都有安全默认值
4. **不包含技术细节**: 无item_id、java_class_name等（那是Compiler的活）

---

### 🎨 设计亮点

#### 1. **双路径架构**
```
Initial Prompt (无spec) → 创建完整mod
   ↓
   使用_parse_item_intent

Iterative Prompt (有spec) → 局部修改
   ↓
   使用_parse_modification_intent
```

**好处**:
- 逻辑清晰分离
- 避免if-else嵌套
- 易于测试和维护

#### 2. **LLM + Fallback双保险**
```
try:
    LLM解析（智能但可能失败）
except:
    规则解析（简单但稳定）
```

**好处**:
- 生产环境稳定性
- API配额耗尽时降级运行

#### 3. **多物品支持**
```python
items: List[ParsedItem]  # 不是单个ParsedItem
```

**实现方式**:
- LLM prompt明确说"can be MULTIPLE"
- 循环处理每个item
- 独立计数器避免索引冲突

---

### ⚠️ 当前限制

1. **Context未使用**
```python
context: Optional[ConversationContext] = None  # 传了但不用
```
**影响**: 无法处理"make it rarer"（需要知道"it"是什么）

2. **修改意图覆盖不全**
```python
elif operation == "add_item":
    # 实现了
elif operation == "remove_item":
    # ❌ 未实现
```

3. **无状态机管理**
- 没有跟踪对话状态（等待回答/处理中）
- clarifying_questions发出后无回调机制

---

## 2. Spec Manager

**文件**: `backend/agents/core/spec_manager.py`

### 📌 整体思路

**核心职责**: 维护唯一的、版本化的用户意图真相（Single Source of Truth）

**设计原则**:
- Spec是给人看的，允许不完整
- 所有变更通过delta应用（git-like）
- 可审计、可回滚、可diff

**数据结构**:
```
workspace/
  spec/
    mod_spec.json          # 当前版本（工作副本）
    history/
      v1.json              # 初始版本
      v2.json              # 第二版本
      v3.json              # 当前版本快照
```

**关键概念**:
- **Spec**: 用户意图（"我要一个发光的红宝石块"）
- **Delta**: 变更请求（"把blocks[0].luminance改成15"）
- **Version**: 每次应用delta后的快照

---

### 🔧 核心类与数据结构

#### 1. `SpecVersion`
```python
class SpecVersion(BaseModel):
    version: str                      # 版本号 "v1", "v2"
    spec: ModSpec                     # 该版本的完整spec
    timestamp: datetime               # 创建时间
    spec_hash: str                    # spec的SHA256（前16字符）
    delta_applied: Optional[SpecDelta] # 导致此版本的delta
    notes: Optional[str]              # 版本说明
```

**用途**:
- 保存在`history/v*.json`
- 支持回滚到任意历史版本
- 审计追踪

#### 2. `SpecManager` 成员变量
```python
self.workspace_dir: Path              # 工作目录根
self.spec_dir: Path                   # spec存储目录
self.current_spec_path: Path          # mod_spec.json路径
self.history_dir: Path                # history/目录
self._current_spec: Optional[ModSpec] # 内存中的当前spec
self._version_counter: int            # 版本计数器
```

---

### 🎯 核心函数详解

#### `__init__(workspace_dir, spec_dir)`

```python
def __init__(self, workspace_dir: Optional[Path] = None, spec_dir: Optional[Path] = None):
    if workspace_dir is None and spec_dir is None:
        raise ValueError("workspace_dir or spec_dir must be provided")

    self.workspace_dir = Path(workspace_dir) if workspace_dir else None
    self.spec_dir = Path(spec_dir) if spec_dir else Path(workspace_dir) / "spec"
    self.spec_dir.mkdir(parents=True, exist_ok=True)

    self.current_spec_path = self.spec_dir / "mod_spec.json"
    self.history_dir = self.spec_dir / "history"
    self.history_dir.mkdir(exist_ok=True)

    self._current_spec = None
    self._version_counter = self._load_version_counter()
```

**关键设计**:
1. **灵活初始化**: 可以只传workspace_dir或单独传spec_dir
2. **自动创建目录**: `mkdir(parents=True, exist_ok=True)`
3. **延迟加载**: `_current_spec = None`，第一次访问时才load

---

#### `initialize_spec(initial_spec: ModSpec) -> str`

```python
def initialize_spec(self, initial_spec: ModSpec) -> str:
    self._current_spec = initial_spec
    if not self._current_spec.version:
        self._current_spec.version = "1.0.0"
    version_id = self._save_version(None, "Initial specification")
    return version_id
```

**职责**: 初始化一个全新的spec

**调用时机**:
```python
# pipeline.py:131
if existing_spec is None:
    base_spec = ModSpec(mod_name="New Mod")
    self.spec_manager.initialize_spec(base_spec)
```

**流程**:
1. 设置内存中的current_spec
2. 如果没有version，设为"1.0.0"
3. 保存为v1版本
4. 返回版本ID（如"v1"）

---

#### `apply_delta(delta: SpecDelta) -> ModSpec`

**这是最核心的函数！**

```python
def apply_delta(self, delta: SpecDelta) -> ModSpec:
    # Step 1: 确保current spec已加载
    if self._current_spec is None:
        self.load_current_spec()

    # Step 2: 根据delta类型选择处理方式
    if delta.is_structured():
        # Structured delta: 使用path + operation
        if self._current_spec is None:
            raise ValueError("No current spec loaded. Initialize first.")
        new_spec = self._apply_structured_delta(self._current_spec, delta)
        new_spec.version = self._next_version(delta, self._current_spec.version)
        notes = f"{delta.operation or 'update'} at {delta.path or 'root'}"
    else:
        # Semantic delta: 使用create/update + fields
        new_spec = self._apply_semantic_delta(delta)
        notes = f"{(delta.delta_type or 'update').capitalize()} delta"

    # Step 3: 保存新版本
    self._current_spec = new_spec
    self._save_version(delta, notes)

    return self._current_spec
```

**职责**: 应用一个delta到当前spec

**两种delta类型**:

1. **Structured Delta** (新方式，Orchestrator使用)
```python
SpecDelta(
    operation="add",           # add/update/remove
    path="items[0].rarity",    # JSON path
    value="EPIC"               # 新值
)
```

2. **Semantic Delta** (旧方式，测试使用)
```python
SpecDelta(
    delta_type="update",       # create/update
    items_to_add=[item1, item2]
)
```

**关键流程**:
```
apply_delta
  ↓
检查delta类型 → is_structured()?
  ↓                    ↓
  YES                  NO
  ↓                    ↓
_apply_structured_delta  _apply_semantic_delta
  ↓                    ↓
更新version ←————————┘
  ↓
_save_version
  ↓
返回新spec
```

---

#### `_apply_structured_delta(spec: ModSpec, delta: SpecDelta) -> ModSpec`

**职责**: 应用基于path的delta

**核心逻辑**:

**Step 1**: 解析path
```python
path_parts = self._parse_path(delta.path)
# "items[0].rarity" → ["items", "0", "rarity"]
```

**Step 2**: 根据operation执行操作

**Operation: ADD**
```python
if delta.operation == "add":
    value = delta.value
    if path_parts and path_parts[-1] == "creative_tab":
        value = normalize_creative_tab(delta.value).value

    # 特殊处理数组（items/blocks/tools）
    if len(path_parts) >= 2 and path_parts[0] in ("items", "blocks", "tools"):
        array_name = path_parts[0]
        if len(path_parts) == 2 and path_parts[1].isdigit():
            idx = int(path_parts[1])
            if idx == len(spec_dict[array_name]):
                # 索引正好等于长度 → 追加到末尾
                spec_dict[array_name].append(value)
            else:
                # 索引不对 → 使用_set_nested_value（会填充中间空位）
                self._set_nested_value(spec_dict, path_parts, value)
        else:
            # 路径更深（items[0].property）→ 设置嵌套值
            self._set_nested_value(spec_dict, path_parts, value)
    else:
        # 非数组字段 → 直接设置
        self._set_nested_value(spec_dict, path_parts, value)
```

**设计意图**:
- `items[3]` 且当前只有3个item → 追加（append）
- `items[5]` 且当前只有3个item → 填充None到4,5然后设置
- `items[0].rarity` → 修改现有item的属性

**Operation: UPDATE**
```python
elif delta.operation == "update":
    # 必须存在才能update
    if not self._path_exists(spec_dict, path_parts):
        raise ValueError(f"Cannot update non-existent path: {delta.path}")

    value = delta.value
    if path_parts and path_parts[-1] == "creative_tab":
        value = normalize_creative_tab(delta.value).value
    self._set_nested_value(spec_dict, path_parts, value)
```

**设计意图**:
- **add**: 可以创建新路径（追加）
- **update**: 只能修改现有路径
- 明确的语义避免误操作

**Operation: REMOVE**
```python
elif delta.operation == "remove":
    self._remove_nested_value(spec_dict, path_parts)
```

**Step 3**: 构建新ModSpec
```python
return ModSpec(**spec_dict)
```

---

#### `_parse_path(path: str) -> List[str]`

```python
def _parse_path(self, path: str) -> List[str]:
    # 将 [N] 转换为 .N
    path = re.sub(r'\[(\d+)\]', r'.\1', path)
    return path.split('.')
```

**示例**:
```python
"mod_name"                         → ["mod_name"]
"items[0].rarity"                  → ["items", "0", "rarity"]
"blocks[1].properties.hardness"    → ["blocks", "1", "properties", "hardness"]
```

**为什么这样做**:
- 统一处理：数组索引和对象key都是path部分
- 简化逻辑：split('.')一次性搞定

---

#### `_path_exists(data: Dict, path_parts: List[str]) -> bool`

```python
def _path_exists(self, data: Dict, path_parts: List[str]) -> bool:
    try:
        current = data
        for part in path_parts:
            if part.isdigit():
                idx = int(part)
                if isinstance(current, list):
                    if idx >= len(current):
                        return False
                    current = current[idx]
                else:
                    return False
            else:
                if part not in current:
                    return False
                current = current[part]
        return True
    except (KeyError, IndexError, TypeError):
        return False
```

**职责**: 检查路径是否存在

**示例**:
```python
data = {"items": [{"rarity": "COMMON"}]}

_path_exists(data, ["items", "0", "rarity"])  # True
_path_exists(data, ["items", "1", "rarity"])  # False (索引越界)
_path_exists(data, ["blocks", "0"])           # False (没有blocks)
```

---

#### `_set_nested_value(data: Dict, path_parts: List[str], value: Any)`

**这是最复杂的函数之一！**

```python
def _set_nested_value(self, data: Dict, path_parts: List[str], value: Any):
    current = data

    # 遍历到倒数第二个part
    for i, part in enumerate(path_parts[:-1]):
        if part.isdigit():
            # 数组索引
            idx = int(part)
            if isinstance(current, list):
                # 扩展列表到足够长度
                next_part = path_parts[i + 1] if i + 1 < len(path_parts) else None
                while len(current) <= idx:
                    if next_part and next_part.isdigit():
                        current.append([])  # 下一层是数组
                    else:
                        current.append({})  # 下一层是对象
                current = current[idx]
        else:
            # 对象key
            if part not in current:
                # 创建中间结构
                next_part = path_parts[i + 1]
                current[part] = [] if next_part.isdigit() else {}
            current = current[part]

    # 设置最终值
    final_key = path_parts[-1]
    if final_key.isdigit():
        idx = int(final_key)
        if isinstance(current, list):
            while len(current) <= idx:
                current.append(None)
            current[idx] = value
        else:
            current[idx] = value
    else:
        current[final_key] = value
```

**核心能力**:
- 自动创建中间路径
- 自动扩展数组
- 智能判断创建数组还是对象

**示例**:

```python
data = {}

# 设置 items[0].rarity = "EPIC"
_set_nested_value(data, ["items", "0", "rarity"], "EPIC")

# 结果:
{
  "items": [
    {"rarity": "EPIC"}
  ]
}

# 设置 items[2].name = "Ruby"（中间有空位）
_set_nested_value(data, ["items", "2", "name"], "Ruby")

# 结果:
{
  "items": [
    {"rarity": "EPIC"},
    {},                    # 自动填充的空对象
    {"name": "Ruby"}
  ]
}
```

**关键设计**:
- **向前看（lookahead）**: 通过`next_part`判断应该创建[]还是{}
- **自动填充**: 确保索引范围内所有元素都存在
- **幂等性**: 多次设置同一路径结果一致

---

#### `_remove_nested_value(data: Dict, path_parts: List[str])`

```python
def _remove_nested_value(self, data: Dict, path_parts: List[str]):
    current = data
    for part in path_parts[:-1]:
        if part.isdigit():
            current = current[int(part)]
        else:
            current = current[part]

    final_key = path_parts[-1]
    if final_key.isdigit():
        del current[int(final_key)]
    else:
        del current[final_key]
```

**职责**: 删除指定路径的值

**注意**:
- 不检查路径是否存在（调用者保证）
- 删除数组元素会改变后续索引

---

#### `_save_version(delta: Optional[SpecDelta], notes: str) -> str`

```python
def _save_version(self, delta: Optional[SpecDelta], notes: str) -> str:
    self._version_counter += 1
    version_id = f"v{self._version_counter}"
    timestamp = datetime.utcnow()

    if self._current_spec is None:
        raise ValueError("No current spec to save")

    spec_dict = self._current_spec.model_dump()

    # 保存当前版本到mod_spec.json
    self.current_spec_path.write_text(json.dumps(spec_dict, indent=2))

    # 保存历史版本
    spec_hash = self._hash_spec(spec_dict)
    history_entry = {
        "version": version_id,
        "timestamp": timestamp.isoformat(),
        "spec_hash": spec_hash,
        "notes": notes,
        "delta": delta.model_dump(exclude_none=True) if delta else None,
        "spec": spec_dict
    }

    history_file = self.history_dir / f"{version_id}.json"
    history_file.write_text(json.dumps(history_entry, indent=2))

    return version_id
```

**职责**: 保存spec版本快照

**保存内容**:
1. **工作副本**: `spec/mod_spec.json`（始终最新）
2. **历史快照**: `spec/history/v{N}.json`（不可变）

**历史文件内容**:
```json
{
  "version": "v3",
  "timestamp": "2026-01-08T12:34:56",
  "spec_hash": "a1b2c3d4e5f6g7h8",
  "notes": "add at items[0]",
  "delta": {
    "operation": "add",
    "path": "items[0]",
    "value": {...}
  },
  "spec": {
    "mod_name": "Ruby Mod",
    "items": [...]
  }
}
```

**设计优势**:
- 完整审计追踪
- 可以diff任意两个版本
- 可以回滚到任意历史点

---

#### `rollback_to_version(version_id: str) -> ModSpec`

```python
def rollback_to_version(self, version_id: str) -> ModSpec:
    version_file = self.history_dir / f"{version_id}.json"
    if not version_file.exists():
        raise FileNotFoundError(f"Version {version_id} not found")

    with open(version_file, 'r') as f:
        version_data = json.load(f)

    self._current_spec = ModSpec(**version_data["spec"])
    self._save_version(None, f"Rollback to {version_id}")

    return self._current_spec
```

**职责**: 回滚到历史版本

**流程**:
1. 加载历史版本的spec
2. 设为当前spec
3. 保存为新版本（rollback本身也是一个版本）

**示例**:
```
v1: 初始spec
v2: 添加ruby sword
v3: 修改rarity为EPIC
v4: 回滚到v2（此时ruby sword是COMMON）
```

---

### 🎨 设计亮点

#### 1. **Git-like版本管理**
```
每次apply_delta → 创建新版本快照
类似: git commit
```

**好处**:
- 完整历史追踪
- 可审计
- 可回滚

#### 2. **双模式delta支持**
```
Structured: operation + path + value  (新方式，精确)
Semantic:   delta_type + fields       (旧方式，批量)
```

**为什么保留两种**:
- Structured: Orchestrator使用，精确控制
- Semantic: 测试使用，批量设置方便

#### 3. **智能路径处理**
```python
_set_nested_value() 能处理:
- 深层嵌套: items[0].properties.hardness
- 自动创建中间结构
- 自动扩展数组
```

**避免了大量样板代码**

#### 4. **Add vs Update语义**
```python
add:    可以创建新路径，追加数组元素
update: 只能修改已有路径，否则抛错
```

**避免误操作**:
- 想修改但typo路径 → update会失败
- 想添加但重复 → add会检测

---

### ⚠️ 当前限制

1. **数组删除问题**
```python
_remove_nested_value(data, ["items", "1"])
# 删除items[1]后，原items[2]变成items[1]
# 所有后续delta的索引都失效了！
```

**解决方案**:
- 使用ID而非索引（`items[id="ruby_sword"]`）
- 或标记删除而非真删除

2. **冲突检测缺失**
```python
# 无法检测两个delta是否冲突
delta1: items[0].rarity = "EPIC"
delta2: items[0].rarity = "RARE"
```

3. **大spec性能**
```python
# 每次都完整序列化整个spec
_save_version() → json.dumps(entire_spec)
```

**优化**: 可以只保存delta，需要时重放

---

## 3. Compiler

**文件**: `backend/agents/core/compiler.py`

### 📌 整体思路

**核心职责**: 将"模糊的人类意图"（Spec）编译成"绝对确定的机器蓝图"（IR）

**设计原则**:
- **Spec可以缺字段，IR必须完整**
- **所有默认值在此决定**
- **所有ID生成在此发生**
- **下游Generator零决策**

**编译过程**:
```
ModSpec (人类意图)
  ↓
补全默认值
  ↓
生成registry ID
  ↓
生成Java类名
  ↓
创建asset manifest
  ↓
ModIR (机器蓝图)
```

**关键概念**:
- **Compilation = 消除所有模糊性**
- **IR = 可以直接机械执行的指令集**

---

### 🔧 核心数据结构

#### ModSpec vs ModIR 对比

**ModSpec（人类友好）**:
```python
ModSpec(
    mod_name="Ruby Mod",               # 人类可读名称
    items=[
        ItemSpec(
            item_name="Ruby Sword",    # 显示名称
            rarity=Rarity.EPIC,        # 枚举
            # 缺失: item_id, java_class_name, texture_path...
        )
    ]
)
```

**ModIR（机器友好）**:
```python
ModIR(
    mod_id="ruby_mod",                 # 生成的技术ID
    mod_name="Ruby Mod",
    base_package="com.example.ruby_mod",  # Java包名
    main_class_name="RubyModMod",      # 主类名

    items=[
        IRItem(
            item_id="ruby_mod:ruby_sword",      # 完整registry ID
            display_name="Ruby Sword",
            rarity="EPIC",                      # 字符串化
            java_class_name="RubySwordItem",    # Java类名
            java_package="com.example.ruby_mod.items",
            registration_id="RUBY_SWORD",       # 注册常量名

            texture_asset=IRAsset(              # 纹理资产
                asset_type="texture",
                file_path="assets/ruby_mod/textures/item/ruby_sword.png",
                texture_generation_prompt="Ruby Sword: A powerful sword made of ruby"
            ),
            model_asset=IRAsset(...),           # 模型资产
            lang_asset=IRAsset(...)             # 语言文件
        )
    ],

    # 所有版本信息（从config读取）
    minecraft_version="1.20.1",
    fabric_loader_version="0.15.0",
    fabric_api_version="0.92.0",
    yarn_mappings="1.20.1+build.10",
    java_version="17",

    # 编译元信息
    compilation_timestamp="2026-01-08T12:34:56",
    compiled_from_spec_version="v3"
)
```

**关键差异**:
1. Spec: 可选字段多，人类友好
2. IR: 无可选字段，机器可直接执行

---

### 🎯 核心函数详解

#### `compile(spec: ModSpec, spec_version: str = "1") -> ModIR`

**这是整个系统最重要的函数之一！**

```python
def compile(self, spec: ModSpec, spec_version: str = "1") -> ModIR:
    # Step 1: 生成mod_id
    mod_id = spec.mod_id or self._generate_mod_id(spec.mod_name)
    # "Ruby Mod" → "ruby_mod"

    # Step 2: 生成base package
    base_package = self._generate_base_package(mod_id)
    # "ruby_mod" → "com.example.ruby_mod"

    # Step 3: 编译所有items/blocks/tools
    ir_items = [self._compile_item(item, mod_id, base_package) for item in spec.items]
    ir_blocks = [self._compile_block(block, mod_id, base_package) for block in spec.blocks]
    ir_tools = [self._compile_tool(tool, mod_id, base_package) for tool in spec.tools]

    # Step 4: 生成recipes
    ir_recipes = []
    for tool in ir_tools:
        recipe = self._generate_tool_recipe(tool, mod_id)
        ir_recipes.append(recipe)

    # Step 5: 收集所有assets
    assets = []
    for item in ir_items:
        assets.extend([item.texture_asset, item.model_asset, item.lang_asset])
    for block in ir_blocks:
        assets.extend([
            block.texture_asset,
            block.blockstate_asset,
            block.model_asset,
            block.item_model_asset,
            block.loot_table_asset,
            block.lang_asset
        ])
    # ... tools同理

    # Step 6: 创建完整IR
    ir = ModIR(
        mod_id=mod_id,
        mod_name=spec.mod_name,
        version=spec.version or "1.0.0",
        author=spec.author or "Unknown",
        description=spec.description or f"A mod that adds {spec.mod_name}",

        # 版本信息（从config读取）
        minecraft_version=spec.minecraft_version or MINECRAFT_VERSION,
        fabric_loader_version=spec.fabric_loader_version or FABRIC_LOADER_VERSION,
        fabric_api_version=spec.fabric_api_version or FABRIC_API_VERSION,
        yarn_mappings=YARN_MAPPINGS,
        java_version=JAVA_VERSION,
        resource_pack_format=RESOURCE_PACK_FORMAT,

        # Java结构
        base_package=base_package,
        main_class_name=self._generate_main_class_name(spec.mod_name),

        # 内容
        items=ir_items,
        blocks=ir_blocks,
        tools=ir_tools,
        recipes=ir_recipes,
        assets=assets,

        # Gradle配置
        gradle_properties=self._generate_gradle_properties(spec, mod_id),

        # 溯源
        compiled_from_spec_version=spec_version,
        compilation_timestamp=datetime.utcnow().isoformat()
    )

    # Step 7: 验证IR
    self._validate_ir(ir)

    return ir
```

**核心流程图**:
```
ModSpec
  ↓
生成mod_id/package
  ↓
编译items → IRItem[]
编译blocks → IRBlock[]
编译tools → IRTool[]
  ↓
生成recipes → IRRecipe[]
  ↓
收集assets → IRAsset[]
  ↓
组装ModIR
  ↓
验证完整性
  ↓
返回ModIR
```

---

#### `_compile_item(item: ItemSpec, mod_id: str, base_package: str) -> IRItem`

**职责**: 编译单个item

**详细流程**:

**Step 1**: 生成item_id
```python
item_id = item.item_id or self._generate_registry_id(item.item_name)
# "Ruby Sword" → "ruby_sword"

full_item_id = f"{mod_id}:{item_id}"
# "ruby_mod:ruby_sword"（Minecraft registry ID格式）
```

**Step 2**: 生成Java标识符
```python
java_class_name = self._to_pascal_case(item_id) + "Item"
# "ruby_sword" → "RubySwordItem"

registration_id = self._to_screaming_snake_case(item_id)
# "ruby_sword" → "RUBY_SWORD"（用于public static final）
```

**Step 3**: 创建texture asset
```python
texture_asset = IRAsset(
    asset_type="texture",
    file_path=f"assets/{mod_id}/textures/item/{item_id}.png",
    # "assets/ruby_mod/textures/item/ruby_sword.png"

    texture_generation_prompt=self._create_texture_prompt(
        item.item_name,           # "Ruby Sword"
        item.description,         # "A powerful sword"
        item.texture_description  # "Red metallic with gems"
    ),
    # "Ruby Sword: A powerful sword. Visual style: Red metallic with gems"

    texture_reference_ids=item.texture_references or []
    # 参考纹理ID（用于图像生成）
)
```

**Step 4**: 创建model asset
```python
model_asset = IRAsset(
    asset_type="model",
    file_path=f"assets/{mod_id}/models/item/{item_id}.json",
    json_content={
        "parent": "item/generated",    # Minecraft内置父模型
        "textures": {
            "layer0": f"{mod_id}:item/{item_id}"
            # 引用上面的texture
        }
    }
)
```

**Minecraft模型机制**:
- `parent: item/generated`: 继承vanilla item模型
- `layer0`: 第一层纹理（可以有layer1, layer2...）

**Step 5**: 创建lang asset
```python
lang_asset = IRAsset(
    asset_type="lang",
    file_path=f"assets/{mod_id}/lang/en_us.json",
    lang_entries={
        f"item.{mod_id}.{item_id}": item.item_name,
        # "item.ruby_mod.ruby_sword": "Ruby Sword"

        f"item.{mod_id}.{item_id}.tooltip": item.description
        # "item.ruby_mod.ruby_sword.tooltip": "A powerful sword"
    }
)
```

**Step 6**: 组装IRItem
```python
return IRItem(
    item_id=full_item_id,                          # registry ID
    display_name=item.item_name,                   # 显示名
    description=item.description,                  # 描述
    max_stack_size=item.max_stack_size or 64,     # 堆叠数（默认64）
    rarity=item.rarity.value if item.rarity else "COMMON",  # 枚举→字符串
    fireproof=item.fireproof or False,             # 是否防火
    creative_tab=item.creative_tab.value if item.creative_tab else "MISC",
    special_ability=item.special_ability or "",    # 特殊能力

    # Assets
    texture_asset=texture_asset,
    model_asset=model_asset,
    lang_asset=lang_asset,

    # Java代码生成信息
    java_class_name=java_class_name,              # "RubySwordItem"
    java_package=f"{base_package}.items",         # "com.example.ruby_mod.items"
    registration_id=registration_id                # "RUBY_SWORD"
)
```

**关键设计**:
- **所有可选字段都有默认值**（max_stack_size=64, fireproof=False）
- **枚举转字符串**（rarity.value）
- **三种asset完整定义**（texture/model/lang）

---

#### `_compile_block(block: BlockSpec, ...) -> IRBlock`

**职责**: 编译单个block

**与item的区别**:

1. **更多assets**:
```python
blockstate_asset    # blockstate定义
model_asset         # 方块模型
item_model_asset    # 物品形式的模型
loot_table_asset    # 掉落物
```

2. **物理属性**:
```python
material=block.material.value if block.material else "STONE",
hardness=block.hardness or 3.0,
resistance=block.resistance or 3.0,
luminance=block.luminance or 0,
requires_tool=block.requires_tool if block.requires_tool is not None else True,
sound_group=block.sound_group.value if block.sound_group else "STONE"
```

3. **Blockstate asset内容**:
```python
blockstate_asset = IRAsset(
    asset_type="blockstate",
    file_path=f"assets/{mod_id}/blockstates/{block_id}.json",
    json_content={
        "variants": {
            "": {"model": f"{mod_id}:block/{block_id}"}
            # 空字符串 = 无变体（简单方块）
        }
    }
)
```

**Minecraft blockstate机制**:
- `variants`: 不同状态使用不同模型
- `""`: 默认状态
- 复杂方块可以有`facing=north`, `powered=true`等变体

4. **Loot table asset**:
```python
loot_table_asset = IRAsset(
    asset_type="loot_table",
    file_path=f"data/{mod_id}/loot_tables/blocks/{block_id}.json",
    json_content={
        "type": "minecraft:block",
        "pools": [{
            "rolls": 1,
            "entries": [{
                "type": "minecraft:item",
                "name": drop_item_id    # 默认掉落自己
            }],
            "conditions": [{
                "condition": "minecraft:survives_explosion"
                # 爆炸后有概率掉落
            }]
        }]
    }
)
```

**设计亮点**:
- 支持自定义掉落物（drop_item_id）
- 默认行为合理（掉落自己）
- 支持爆炸条件

---

#### `_compile_tool(tool: ToolSpec, ...) -> IRTool`

**职责**: 编译单个tool

**关键差异**:

1. **Tool tier defaults**:
```python
tier_defaults = self._get_tool_tier_defaults(tool.material_tier or "IRON")
# {
#   "durability": 250,
#   "mining_speed": 6.0,
#   "attack_damage": 4.0
# }

return IRTool(
    durability=tool.durability or tier_defaults["durability"],
    mining_speed=tool.mining_speed or tier_defaults["mining_speed"],
    attack_damage=tool.attack_damage or tier_defaults["attack_damage"]
)
```

**tier表**:
```python
"WOOD":      {durability: 59,   speed: 2.0,  damage: 2.0}
"STONE":     {durability: 131,  speed: 4.0,  damage: 3.0}
"IRON":      {durability: 250,  speed: 6.0,  damage: 4.0}
"DIAMOND":   {durability: 1561, speed: 8.0,  damage: 5.0}
"NETHERITE": {durability: 2031, speed: 9.0,  damage: 6.0}
```

2. **Handheld模型**:
```python
model_asset = IRAsset(
    json_content={
        "parent": "item/handheld",    # 不是item/generated
        "textures": {
            "layer0": f"{mod_id}:item/{tool_id}"
        }
    }
)
```

**item/handheld vs item/generated**:
- `handheld`: 工具在手中的角度（45度）
- `generated`: 普通物品（平面）

---

#### `_generate_tool_recipe(tool: IRTool, mod_id: str) -> IRRecipe`

**职责**: 为工具生成合成配方

**模式表**:
```python
patterns = {
    "PICKAXE": (["###", " S ", " S "], {"#": "material", "S": "minecraft:stick"}),
    #  # # #
    #    S
    #    S

    "AXE": (["##", "#S", " S"], {"#": "material", "S": "minecraft:stick"}),
    #  # #
    #  # S
    #    S

    "SWORD": (["#", "#", "S"], ...),
    "SHOVEL": (["#", "S", "S"], ...),
    "HOE": (["##", " S", " S"], ...)
}
```

**返回**:
```python
return IRRecipe(
    recipe_id=f"{mod_id}:{tool_id}_recipe",
    recipe_type="crafting_shaped",     # 有形合成
    result_item_id=tool.tool_id,
    result_count=1,
    pattern=pattern,
    keys={
        "#": "minecraft:iron_ingot",   # TODO: 应该从tool.material读取
        "S": "minecraft:stick"
    }
)
```

**⚠️ 当前限制**:
```python
# TODO: Get crafting ingredient from tool spec
keys["#"] = "minecraft:iron_ingot"  # 硬编码！
```

**应该改为**:
```python
material_items = {
    "WOOD": "minecraft:planks",
    "STONE": "minecraft:cobblestone",
    "IRON": "minecraft:iron_ingot",
    "DIAMOND": "minecraft:diamond"
}
keys["#"] = material_items[tool.material_tier]
```

---

#### 辅助函数详解

#### `_generate_mod_id(mod_name: str) -> str`
```python
def _generate_mod_id(self, mod_name: str) -> str:
    mod_id = mod_name.lower()
    mod_id = re.sub(r'[^a-z0-9_]', '_', mod_id)  # 只保留字母数字下划线
    mod_id = re.sub(r'_+', '_', mod_id).strip('_')  # 多个下划线合并
    return mod_id
```

**示例**:
```python
"Ruby Mod"           → "ruby_mod"
"Super-Cool Mod!"    → "super_cool_mod"
"123 Test"           → "123_test"
"___ABC___"          → "abc"
```

---

#### `_to_pascal_case(s: str) -> str`
```python
def _to_pascal_case(self, s: str) -> str:
    words = re.split(r'[_\s]+', s)
    return ''.join(word.capitalize() for word in words)
```

**示例**:
```python
"ruby_sword"         → "RubySword"
"frost lantern"      → "FrostLantern"
"super_cool_block"   → "SuperCoolBlock"
```

---

#### `_to_screaming_snake_case(s: str) -> str`
```python
def _to_screaming_snake_case(self, s: str) -> str:
    return s.upper().replace(' ', '_')
```

**示例**:
```python
"ruby_sword"         → "RUBY_SWORD"
"frost lantern"      → "FROST_LANTERN"
```

**用途**: Java常量名
```java
public static final Item RUBY_SWORD = ...;
```

---

#### `_create_texture_prompt(name, description, hint) -> str`
```python
def _create_texture_prompt(self, name: str, description: str, hint: str = None) -> str:
    base = f"{name}: {description}"
    if hint:
        base += f". Visual style: {hint}"
    return base
```

**示例**:
```python
_create_texture_prompt(
    "Ruby Sword",
    "A powerful sword made of ruby",
    "Red metallic with glowing gems"
)
# → "Ruby Sword: A powerful sword made of ruby. Visual style: Red metallic with glowing gems"
```

**用途**: 传给AI图像生成工具

---

#### `_validate_ir(ir: ModIR)`
```python
def _validate_ir(self, ir: ModIR):
    # 检查必需字段
    if not ir.mod_id:
        raise CompilationError("mod_id is required")
    if not ir.base_package:
        raise CompilationError("base_package is required")

    # 检查registry ID唯一性
    all_ids = set()
    for item in ir.items:
        if item.item_id in all_ids:
            raise CompilationError(f"Duplicate registry ID: {item.item_id}")
        all_ids.add(item.item_id)

    # 可以添加更多检查...

    print(f"✓ IR validation passed: {len(ir.items)} items, ...")
```

**职责**: 确保IR完整且无冲突

**当前检查**:
- ✅ 必需字段存在
- ✅ registry ID唯一性

**可添加的检查**:
- ❌ 所有asset路径合法
- ❌ 所有Java包名合法
- ❌ recipe引用的item存在

---

### 🎨 设计亮点

#### 1. **完整性保证**
```
Spec可以缺字段 → Compiler补全 → IR必定完整
```

**机制**:
- 所有`or`表达式提供默认值
- tier表提供合理默认值
- config文件提供版本信息

#### 2. **确定性**
```
相同Spec → 相同IR（可重复构建）
```

**机制**:
- 无随机数
- 无时间戳（除了provenance）
- 纯函数式转换

#### 3. **溯源完整**
```python
ModIR(
    compiled_from_spec_version="v3",
    compilation_timestamp="..."
)
```

**用途**:
- 调试："这个IR是从哪个spec编译的？"
- 审计："什么时候编译的？"

#### 4. **Asset集中管理**
```python
assets = []
for item in ir_items:
    assets.extend([item.texture_asset, ...])
# IR中有完整的asset清单
```

**好处**:
- 一个地方列出所有需要生成的文件
- Planner可以并行化texture生成
- Validator可以检查完整性

---

### ⚠️ 当前限制

1. **硬编码的recipe材料**
```python
keys["#"] = "minecraft:iron_ingot"  # 应该根据tool.material_tier动态选择
```

2. **简单的blockstate**
```python
"variants": {"": {...}}  # 只支持无变体方块
```

**复杂方块需要**:
```python
"variants": {
    "facing=north,powered=false": {...},
    "facing=north,powered=true": {...},
    ...
}
```

3. **固定的parent模型**
```python
"parent": "block/cube_all"  # 所有方块都是全方向同纹理
```

**应支持**:
- `block/cube_column`: 柱状（顶部底部不同）
- `block/orientable`: 有方向的方块
- 自定义模型

4. **缺少依赖分析**
- 如果recipe引用不存在的item，Compiler不报错
- 应该在validation阶段检查所有引用

---

## 4. Planner

**文件**: `backend/agents/core/planner.py`

### 📌 整体思路

**核心职责**: 将IR分解为可执行的任务DAG（有向无环图）

**设计原则**:
- Planner是"dumb"的：机械分解，无智能决策
- 所有任务必须有明确依赖关系
- 支持并行执行
- 任务粒度适中（不能太细也不能太粗）

**DAG结构**:
```
      setup_workspace
           ↓
    ┌──────┴──────┐
    ↓             ↓
texture_gen   code_gen
(并行)           ↓
    ↓        assets_gen
    └──────┬──────┘
           ↓
      build_mod
```

---

### 🔧 核心数据结构

#### `Task`
```python
class Task(BaseModel):
    task_id: str                      # "task_001"
    description: str                  # 人类可读描述
    task_type: str                    # setup/generate_texture/build...
    dependencies: List[str] = []      # 依赖的task_id列表
    tool_calls: List[ToolCall] = []   # 要调用的工具
    inputs: Dict[str, Any] = {}       # 输入数据
    expected_outputs: Dict[str, Any] = {}  # 期望输出
    parallelizable: bool = False      # 是否可并行
    priority: int = 50                # 优先级（越高越先）
    status: TaskStatus = TaskStatus.PENDING
```

#### `ToolCall`
```python
class ToolCall(BaseModel):
    tool_name: str                    # 工具名称
    parameters: Dict[str, Any] = {}   # 工具参数
```

#### `TaskDAG`
```python
class TaskDAG(BaseModel):
    tasks: List[Task]                 # 所有任务
    entry_tasks: List[str]            # 入口任务ID（无依赖）
    final_tasks: List[str]            # 最终任务ID
    total_tasks: int                  # 任务总数
    completed_task_ids: List[str] = []
    failed_task_ids: List[str] = []
    created_from_ir_id: str           # 从哪个IR创建
    created_at: datetime
```

---

### 🎯 核心函数详解

#### `plan(ir: ModIR, workspace_root: Path) -> TaskDAG`

**职责**: 创建完整执行计划

**核心流程**:

```python
def plan(self, ir: ModIR, workspace_root: Optional[Path] = None) -> TaskDAG:
    workspace_root = Path(workspace_root) if workspace_root else Path("generated")
    mod_workspace = workspace_root / ir.mod_id

    tasks = []
    self.task_counter = 0

    # Phase 1: Setup workspace
    setup_task = self._create_setup_task(ir, workspace_root, mod_workspace)
    tasks.append(setup_task)

    # Phase 2: Generate textures (parallel)
    texture_tasks = self._create_texture_generation_tasks(ir)
    tasks.extend(texture_tasks)

    # Phase 3: Generate Java code (depends on setup)
    code_task = self._create_code_generation_task(ir, setup_task.task_id, mod_workspace)
    tasks.append(code_task)

    # Phase 4: Generate assets (depends on textures)
    assets_task = self._create_assets_generation_task(
        ir,
        [t.task_id for t in texture_tasks],  # 依赖所有texture任务
        mod_workspace
    )
    tasks.append(assets_task)

    # Phase 5: Generate build config (depends on setup)
    config_tasks = self._create_build_config_tasks(ir, setup_task.task_id, mod_workspace)
    tasks.extend(config_tasks)

    # Phase 6: Setup Gradle wrapper
    gradle_wrapper_task = self._create_gradle_wrapper_task(ir, setup_task.task_id, mod_workspace)
    tasks.append(gradle_wrapper_task)

    # Phase 7: Build mod (depends on everything)
    all_task_ids = [t.task_id for t in tasks]
    build_task = self._create_build_task(ir, all_task_ids, mod_workspace)
    tasks.append(build_task)

    # Create DAG
    dag = TaskDAG(
        tasks=tasks,
        entry_tasks=[setup_task.task_id],     # 只有setup是入口
        final_tasks=[build_task.task_id],     # 只有build是最终
        total_tasks=len(tasks),
        created_from_ir_id=ir.mod_id,
        created_at=datetime.utcnow()
    )

    print(f"✓ Planned {len(tasks)} tasks for {ir.mod_id}")
    return dag
```

**Phase详解**:

**Phase 1: Setup**
```
创建目录结构:
mod_workspace/
  src/
    main/
      java/
        com/example/mod_id/
      resources/
        assets/mod_id/
        data/mod_id/
```

**Phase 2: Textures (并行)**
```
为每个item/block/tool生成纹理
可以并行：texture之间无依赖
```

**Phase 3: Code**
```
生成所有Java文件
依赖setup（需要目录）
```

**Phase 4: Assets**
```
生成JSON文件（model/blockstate/recipe/lang）
依赖textures（model引用texture路径）
```

**Phase 5: Config**
```
生成:
- build.gradle
- fabric.mod.json
- mixins.json
依赖setup
```

**Phase 6: Gradle Wrapper**
```
下载并设置Gradle wrapper
```

**Phase 7: Build**
```
./gradlew build
依赖所有前序任务
```

---

#### `_create_setup_task(...) -> Task`

```python
def _create_setup_task(self, ir: ModIR, workspace_root: Path, mod_workspace: Path) -> Task:
    return Task(
        task_id=self._next_task_id(),        # "task_001"
        description="Setup mod workspace structure",
        task_type="setup",
        tool_calls=[
            ToolCall(
                tool_name="setup_workspace",
                parameters={
                    "workspace_dir": str(workspace_root),
                    "mod_id": ir.mod_id,
                    "package_name": ir.base_package
                }
            )
        ],
        inputs={},
        expected_outputs={"workspace_path": str(mod_workspace)},
        parallelizable=False,                # 必须串行
        priority=100                         # 最高优先级
    )
```

**关键设计**:
- `priority=100`: 确保最先执行
- `parallelizable=False`: 不能与其他setup并行
- `expected_outputs`: 声明创建了什么（用于验证）

---

#### `_create_texture_generation_tasks(ir) -> List[Task]`

```python
def _create_texture_generation_tasks(self, ir: ModIR) -> List[Task]:
    tasks = []

    # 收集所有需要纹理的实体
    entities = []
    for item in ir.items:
        entities.append(("item", item.display_name, item.item_id, item.description))
    for block in ir.blocks:
        entities.append(("block", block.display_name, block.block_id, block.description))
    for tool in ir.tools:
        entities.append(("tool", tool.display_name, tool.tool_id, tool.description))

    for entity_type, name, entity_id, description in entities:
        task = Task(
            task_id=self._next_task_id(),
            description=f"Generate texture for {name}",
            task_type="generate_texture",
            tool_calls=[
                ToolCall(
                    tool_name="generate_texture",
                    parameters={
                        "item_name": name,
                        "description": description,
                        "variant_count": 3          # 生成3个候选
                    }
                )
            ],
            inputs={"entity_id": entity_id, "entity_type": entity_type},
            expected_outputs={"texture_variants": []},
            parallelizable=True,                    # 关键！
            priority=80
        )
        tasks.append(task)

    return tasks
```

**关键设计**:
- `parallelizable=True`: 所有纹理生成可并行
- `variant_count=3`: 生成多个候选供用户选择
- `inputs`包含entity_id：后续任务知道这是哪个entity的纹理

**并行化收益**:
```
串行: 10个纹理 × 30秒/个 = 300秒
并行: 10个纹理 / 10并发 × 30秒 = 30秒
```

---

#### `_create_code_generation_task(...) -> Task`

```python
def _create_code_generation_task(self, ir: ModIR, depends_on: str, mod_workspace: Path) -> Task:
    items_data = [item.model_dump() for item in ir.items]
    blocks_data = [block.model_dump() for block in ir.blocks]
    tools_data = [tool.model_dump() for tool in ir.tools]

    return Task(
        task_id=self._next_task_id(),
        description=f"Generate Java code for {ir.mod_name}",
        task_type="generate_code",
        dependencies=[depends_on],              # 依赖setup任务
        tool_calls=[
            ToolCall(
                tool_name="generate_java_code",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "package_name": ir.base_package,
                    "mod_id": ir.mod_id,
                    "main_class_name": ir.main_class_name,
                    "items": items_data,       # 完整的IRItem数据
                    "blocks": blocks_data,
                    "tools": tools_data
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"main_class_path": "src/main/java/..."},
        priority=70
    )
```

**关键设计**:
- `dependencies=[depends_on]`: 明确依赖关系
- 传递完整IR数据：Generator有足够信息
- 单个任务生成所有代码：避免文件冲突

---

#### `_create_assets_generation_task(...) -> Task`

```python
def _create_assets_generation_task(self, ir: ModIR, depends_on: List[str], mod_workspace: Path) -> Task:
    return Task(
        task_id=self._next_task_id(),
        description=f"Generate assets for {ir.mod_name}",
        task_type="generate_assets",
        dependencies=depends_on,                # 依赖所有texture任务！
        tool_calls=[
            ToolCall(
                tool_name="generate_assets",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "mod_id": ir.mod_id,
                    "items": items_data,
                    "blocks": blocks_data,
                    "tools": tools_data,
                    "textures": {}              # 将由texture任务填充
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"assets_path": "src/main/resources/assets"},
        priority=60
    )
```

**依赖关系**:
```
texture_task_1 ─┐
texture_task_2 ─┼→ assets_task
texture_task_3 ─┘
```

**关键问题**: textures参数如何传递？

**当前方案**:
```python
textures={}  # 空的，需要Executor填充
```

**⚠️ 这是一个架构缺陷！**

**理想方案**:
```python
# Executor应该:
1. 执行texture任务，获得texture_path
2. 将texture_path写入共享存储
3. assets任务从共享存储读取
```

---

#### `_create_build_config_tasks(...) -> List[Task]`

```python
def _create_build_config_tasks(self, ir: ModIR, depends_on: str, mod_workspace: Path) -> List[Task]:
    tasks = []

    # Task 1: build.gradle
    gradle_task = Task(
        task_id=self._next_task_id(),
        description="Generate Gradle build files",
        task_type="generate_config",
        dependencies=[depends_on],
        tool_calls=[
            ToolCall(
                tool_name="generate_gradle_files",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "mod_id": ir.mod_id,
                    "mod_name": ir.mod_name,
                    "version": ir.version,
                    "minecraft_version": ir.minecraft_version,
                    "dependencies": []
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"build_gradle": "build.gradle"},
        priority=60
    )
    tasks.append(gradle_task)

    # Task 2: fabric.mod.json
    fabric_json_task = Task(
        task_id=self._next_task_id(),
        description="Generate fabric.mod.json",
        task_type="generate_config",
        dependencies=[depends_on],
        tool_calls=[
            ToolCall(
                tool_name="generate_fabric_mod_json",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "mod_id": ir.mod_id,
                    "mod_name": ir.mod_name,
                    "version": ir.version,
                    "description": ir.description,
                    "authors": [ir.author] if ir.author else [],
                    "license": "MIT",
                    "package_name": ir.base_package,
                    "main_class_name": ir.main_class_name
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"fabric_mod_json": "src/main/resources/fabric.mod.json"},
        priority=60
    )
    tasks.append(fabric_json_task)

    # Task 3: mixins.json
    mixins_task = Task(
        task_id=self._next_task_id(),
        description="Generate mixins.json",
        task_type="generate_config",
        dependencies=[depends_on],
        tool_calls=[
            ToolCall(
                tool_name="generate_mixins_json",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "mod_id": ir.mod_id,
                    "package_name": ir.base_package
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"mixins_json": f"src/main/resources/{ir.mod_id}.mixins.json"},
        priority=60
    )
    tasks.append(mixins_task)

    return tasks
```

**为什么分3个任务**:
1. 每个文件独立生成
2. 可以单独测试
3. 可以单独重试（如果失败）

**为什么不并行**:
- 都依赖setup
- 但之间无依赖
- **其实可以并行！** （当前未标记parallelizable）

---

#### `_create_build_task(...) -> Task`

```python
def _create_build_task(self, ir: ModIR, depends_on: List[str], mod_workspace: Path) -> Task:
    return Task(
        task_id=self._next_task_id(),
        description="Build mod with Gradle",
        task_type="build",
        dependencies=depends_on,                # 依赖所有任务！
        tool_calls=[
            ToolCall(
                tool_name="build_mod",
                parameters={
                    "workspace_path": str(mod_workspace),
                    "mod_id": ir.mod_id
                }
            )
        ],
        inputs={"ir": ir.model_dump()},
        expected_outputs={"jar_file": f"build/libs/{ir.mod_id}-{ir.version}.jar"},
        priority=10                             # 最低优先级
    )
```

**关键设计**:
- `dependencies=depends_on`: 包含所有前序任务ID
- `priority=10`: 最后执行
- `expected_outputs`: 声明生成的JAR路径

---

### 🎨 设计亮点

#### 1. **DAG依赖管理**
```
Task通过dependencies声明依赖
Executor通过get_ready_tasks()获取可执行任务
```

**好处**:
- 声明式依赖（而非命令式控制流）
- 自动并行化（Executor处理）
- 易于可视化

#### 2. **Phase分层清晰**
```
Setup → (Textures || Code) → Assets → Config → Build
```

**每个Phase职责单一**

#### 3. **Task粒度适中**
```
粗粒度: 一个任务生成所有文件（难以并行、难以重试）
细粒度: 每个文件一个任务（任务爆炸）
适中:   每个类型一个任务（当前方案）
```

#### 4. **Priority支持**
```python
setup:     priority=100  # 必须最先
textures:  priority=80   # 优先生成
code:      priority=70
build:     priority=10   # 必须最后
```

**用途**: 当多个任务都ready时，优先执行高优先级

---

### ⚠️ 当前限制

1. **任务间数据传递不足**
```python
textures={}  # 空的！texture任务的输出如何传给assets任务？
```

**需要**:
- 共享存储（如Redis）
- 或Executor维护outputs字典

2. **未充分并行化**
```python
config_tasks都有相同dependencies
但未标记parallelizable=True
```

**可并行的任务**:
- 所有texture任务
- 所有config任务（build.gradle/fabric.mod.json/mixins.json）

3. **缺少条件任务**
```python
# 例如：只有当有blocks时才生成loot tables
if len(ir.blocks) > 0:
    loot_table_task = ...
```

4. **缺少动态任务**
```python
# 例如：根据item数量动态调整并发数
if len(ir.items) > 100:
    # 分批生成
```

---

## 5. Executor

**文件**: `backend/agents/core/executor.py`

### 📌 整体思路

**核心职责**: 严格按照DAG顺序执行任务，调用工具

**设计原则**:
- Executor是"机器人"：零智能，只执行
- 按依赖关系执行，不按顺序
- 调用工具，不解释参数
- 记录一切，不做决策

**执行流程**:
```
while 未完成所有任务:
    获取ready任务（依赖都满足）
    执行任务
    标记完成
    记录日志
```

---

### 🔧 核心数据结构

#### `Executor` 成员变量
```python
self.workspace_dir: Path                      # 工作目录
self.tool_registry: Dict[str, Callable]       # 工具名 → 工具函数
self.execution_log: List[str]                 # 执行日志
```

**tool_registry结构**:
```python
{
    "setup_workspace": setup_workspace_func,
    "generate_texture": generate_texture_func,
    "generate_java_code": generate_java_code_func,
    ...
}
```

---

### 🎯 核心函数详解

#### `execute(dag: TaskDAG, progress_callback) -> Dict[str, Any]`

**这是核心执行循环！**

```python
def execute(
    self,
    dag: TaskDAG,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    def log(msg: str):
        self.execution_log.append(msg)
        if progress_callback:
            progress_callback(msg)
        print(f"[Executor] {msg}")

    log(f"Starting execution of {dag.total_tasks} tasks")

    # 主执行循环
    while len(dag.completed_task_ids) < dag.total_tasks:
        # 获取ready任务
        ready_tasks = dag.get_ready_tasks()

        if not ready_tasks:
            # 检查是否卡住了
            if len(dag.failed_task_ids) > 0:
                raise ExecutionError(f"Execution failed: {len(dag.failed_task_ids)} tasks failed")
            else:
                raise ExecutionError("Execution deadlock: no ready tasks but not all completed")

        # 执行ready任务
        for task in ready_tasks:
            try:
                log(f"Executing: {task.description}")
                self._execute_task(task)
                dag.mark_completed(task.task_id)
                log(f"✓ Completed: {task.description}")
            except Exception as e:
                error_msg = f"Task failed: {task.description} - {str(e)}"
                log(f"✗ {error_msg}")
                dag.mark_failed(task.task_id, str(e))
                raise ExecutionError(error_msg) from e

    log(f"✓ Execution complete: {len(dag.completed_task_ids)}/{dag.total_tasks} tasks succeeded")

    return {
        "status": "success",
        "completed_tasks": len(dag.completed_task_ids),
        "total_tasks": dag.total_tasks,
        "execution_log": self.execution_log
    }
```

**核心逻辑**:

**Step 1**: 获取ready任务
```python
ready_tasks = dag.get_ready_tasks()
# 返回所有依赖都已完成的任务
```

**DAG.get_ready_tasks()逻辑**:
```python
def get_ready_tasks(self) -> List[Task]:
    ready = []
    for task in self.tasks:
        if task.status != TaskStatus.PENDING:
            continue  # 已执行或执行中

        # 检查所有依赖是否完成
        if all(dep_id in self.completed_task_ids for dep_id in task.dependencies):
            ready.append(task)

    # 按priority排序
    return sorted(ready, key=lambda t: t.priority, reverse=True)
```

**Step 2**: 检查死锁
```python
if not ready_tasks:
    if len(dag.failed_task_ids) > 0:
        # 有失败任务 → 合理
        raise ExecutionError(...)
    else:
        # 没有ready任务，但有pending任务 → 死锁！
        # 可能原因: 循环依赖
        raise ExecutionError("Execution deadlock")
```

**Step 3**: 执行任务
```python
for task in ready_tasks:
    try:
        self._execute_task(task)
        dag.mark_completed(task.task_id)
    except Exception as e:
        dag.mark_failed(task.task_id, str(e))
        raise  # 失败则中止整个执行
```

**关键设计**:
- **Fail-fast**: 任何任务失败立即中止
- **日志完整**: 每个步骤都记录
- **状态同步**: DAG状态实时更新

---

#### `_execute_task(task: Task)`

```python
def _execute_task(self, task: Task):
    task.status = TaskStatus.RUNNING

    # 执行所有tool calls
    for tool_call in task.tool_calls:
        self._execute_tool_call(tool_call, task.inputs)

    task.status = TaskStatus.COMPLETED
```

**职责**: 执行单个任务的所有tool calls

**为什么一个task可以有多个tool calls**:

**示例1**: 生成+验证
```python
Task(
    tool_calls=[
        ToolCall(tool_name="generate_java_code", ...),
        ToolCall(tool_name="format_java_code", ...)  # 格式化生成的代码
    ]
)
```

**示例2**: 配置+初始化
```python
Task(
    tool_calls=[
        ToolCall(tool_name="download_gradle", ...),
        ToolCall(tool_name="setup_gradle_wrapper", ...)
    ]
)
```

**当前实现**: 大多数任务只有1个tool call

---

#### `_execute_tool_call(tool_call: ToolCall, task_inputs: Dict)`

**这是最复杂的函数！**

```python
def _execute_tool_call(self, tool_call: ToolCall, task_inputs: Dict[str, Any]):
    tool_name = tool_call.tool_name

    # 检查工具是否存在
    if tool_name not in self.tool_registry:
        raise ExecutionError(f"Tool not found: {tool_name}")

    tool_func = self.tool_registry[tool_name]

    # 合并参数
    params = {**task_inputs, **tool_call.parameters}

    # 从IR context提取常用参数
    ir_context = task_inputs.get("ir")
    if ir_context:
        params.setdefault("mod_id", ir_context.get("mod_id"))
        params.setdefault("package_name", ir_context.get("base_package"))

    # 过滤参数（只传工具需要的）
    allowed_params = getattr(tool_func, "__tool_inputs__", None)
    if allowed_params:
        params = {k: v for k, v in params.items() if k in allowed_params}

        # 检查必需参数
        if "mod_id" in allowed_params and "mod_id" not in params:
            if ir_context and ir_context.get("mod_id"):
                params["mod_id"] = ir_context["mod_id"]
            else:
                raise ExecutionError(f"Missing required mod_id for tool {tool_name}")

    # 调用工具
    try:
        result = tool_func(**params)
        return result
    except Exception as e:
        raise ExecutionError(f"Tool {tool_name} failed: {str(e)}") from e
```

**核心流程**:

**Step 1**: 查找工具
```python
tool_func = self.tool_registry[tool_name]
```

**Step 2**: 合并参数
```python
params = {**task_inputs, **tool_call.parameters}
# task_inputs优先级低，tool_call.parameters优先级高
```

**示例**:
```python
task_inputs = {"ir": {...}, "workspace_path": "/path1"}
tool_call.parameters = {"workspace_path": "/path2", "mod_id": "ruby_mod"}

params = {"ir": {...}, "workspace_path": "/path2", "mod_id": "ruby_mod"}
#                       ^^^^^^^^^^^^^^^ 被覆盖
```

**Step 3**: 从IR提取常用参数
```python
ir_context = task_inputs.get("ir")
if ir_context:
    params.setdefault("mod_id", ir_context.get("mod_id"))
    params.setdefault("package_name", ir_context.get("base_package"))
```

**为什么需要**:
- 很多工具都需要mod_id
- 避免每个tool_call都写一遍

**Step 4**: 过滤参数
```python
allowed_params = getattr(tool_func, "__tool_inputs__", None)
if allowed_params:
    params = {k: v for k, v in params.items() if k in allowed_params}
```

**__tool_inputs__是什么**:

**工具定义时标记**:
```python
def setup_workspace(workspace_dir: str, mod_id: str, package_name: str):
    ...

setup_workspace.__tool_inputs__ = ["workspace_dir", "mod_id", "package_name"]
```

**为什么需要过滤**:
- params可能包含很多无关字段（如整个ir）
- 直接传会导致`unexpected keyword argument`错误

**Step 5**: 检查必需参数
```python
if "mod_id" in allowed_params and "mod_id" not in params:
    # mod_id是必需的但缺失
    if ir_context and ir_context.get("mod_id"):
        params["mod_id"] = ir_context["mod_id"]  # 从IR提取
    else:
        raise ExecutionError("Missing required mod_id")
```

**Step 6**: 调用工具
```python
try:
    result = tool_func(**params)
    return result
except Exception as e:
    raise ExecutionError(f"Tool {tool_name} failed: {str(e)}") from e
```

**关键设计**:
- 工具函数抛异常 → Executor包装成ExecutionError
- 保留原始异常（`from e`）用于调试

---

### 🎨 设计亮点

#### 1. **声明式执行**
```
Executor不知道任务顺序
Executor只知道依赖关系
→ 自动推导执行顺序
```

**好处**:
- DAG可以动态修改
- 易于并行化（未来）

#### 2. **工具注册机制**
```python
tool_registry = {
    "setup_workspace": func1,
    "generate_texture": func2
}
```

**好处**:
- 可插拔工具
- 易于测试（mock工具）
- 易于扩展

#### 3. **智能参数传递**
```
tool_call.parameters  （显式参数）
  ↓
合并 task.inputs      （任务上下文）
  ↓
提取 ir_context       （IR字段）
  ↓
过滤 allowed_params   （工具需要的）
  ↓
调用工具
```

**避免了大量样板代码**

#### 4. **完整日志**
```python
log(f"Executing: {task.description}")
log(f"✓ Completed: ...")
log(f"✗ {error_msg}")
```

**用途**:
- 调试
- 进度展示
- 审计

---

### ⚠️ 当前限制

#### 1. **串行执行**
```python
for task in ready_tasks:
    self._execute_task(task)  # 一个接一个执行
```

**问题**:
- `parallelizable=True`的任务没有真正并行
- 10个texture任务串行执行，浪费时间

**解决方案**:
```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(self._execute_task, task) for task in ready_tasks]
    for future in futures:
        future.result()  # 等待完成
```

#### 2. **Fail-fast策略**
```python
except Exception as e:
    raise  # 立即中止
```

**问题**:
- 一个texture生成失败 → 整个pipeline停止
- 其他99个texture都浪费了

**可选策略**:
- **Fail-soft**: 记录失败但继续
- **Retry**: 自动重试N次
- **Fallback**: 使用默认纹理

#### 3. **无任务输出管理**
```python
result = tool_func(**params)
return result  # 返回值丢失！
```

**问题**:
- texture任务生成texture_path
- 但assets任务无法获取这个路径

**解决方案**:
```python
# 维护输出字典
self.task_outputs[task.task_id] = result

# 后续任务可以引用
params["texture_path"] = self.task_outputs["task_002"]["texture_path"]
```

#### 4. **无checkpoint**
```python
# 执行到一半崩溃 → 从头开始
```

**解决方案**:
```python
# 每完成一个任务保存状态
dag.save_checkpoint()

# 重启时恢复
dag = TaskDAG.load_checkpoint()
executor.execute(dag)  # 从中断处继续
```

---

## 总结

我已经创建了完整的架构深度解析文档。由于篇幅限制，这里先完成了前5个模块（Orchestrator、Spec Manager、Compiler、Planner、Executor）。

**每个模块包含**:
1. 整体设计思路
2. 核心数据结构
3. 每个函数的详细解析（参数、返回值、流程）
4. 设计亮点
5. 当前限制

**剩余3个模块**（Validator、Builder、Error Fixer）我可以继续补充。你想：
1. 继续看剩余3个模块的详解
2. 或者对当前5个模块有具体问题想深入探讨
3. 或者想要某个特定功能的实现示例

请告诉我你的需求！
