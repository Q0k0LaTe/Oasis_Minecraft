# Changes After Compiler

This note summarizes recent changes to the IR and the follow-up work needed
to keep the pipeline consistent and deterministic.

## Context
- I added new IR item capabilities to support custom Java subclasses.
- The goal is to let items override `use`, `useOnBlock`, and/or `useOnEntity`.
- These method bodies are stored as full Java method strings in the IR.

## What changed in the IR
- `IRItem.type` now explicitly categorizes items:
  - `ITEM_MAINCLASS`: uses base `Item` class directly.
  - `ITEM_SUBCLASS`: reserved for a future shared subclass strategy.
  - `ITEM_NEWCLASS`: generates a new Java class per item.
- Added item behavior flags and stats in `IRItem`:
  - `isFood`, `nutrition`, `saturationModifier`
  - `isSword`, `swordAttackDamage`, `swordAttackSpeed`
  - `isPickaxe`, `pickaxeAttackDamage`, `pickaxeAttackSpeed`
- `IRItem.use`, `IRItem.useOnBlock`, `IRItem.useOnEntity` are now part of IR.
  - Each field must contain a complete overridden method body.
  - Strings are injected directly into the generated class.
  - Expected method formats (use these as templates and replace `(actual code)`):
    - `use`:
      ```java
      @Override
      public ActionResult use(World world, PlayerEntity player, Hand hand){
          if (!world.isClient()) {
              // actual code
              return ActionResult.SUCCESS;
          }
          return super.use(world, player, hand);
      }
      ```
    - `useOnBlock`:
      ```java
      @Override
      public ActionResult useOnBlock(ItemUsageContext context) {
          BlockPos pos = context.getBlockPos();
          PlayerEntity player = context.getPlayer();
          World world = context.getWorld();
          if (!world.isClient()) {
              // actual code
              return ActionResult.SUCCESS;
          }
          return super.useOnBlock(context);
      }
      ```
    - `useOnEntity`:
      ```java
      @Override
      public ActionResult useOnEntity(ItemStack stack, PlayerEntity user, LivingEntity entity, Hand hand) {
          if (true) { // some conditions on the entity
              // actual code
              return ActionResult.SUCCESS;
          }
          return ActionResult.PASS;
      }
      ```
  - It is compilable and buildable, but not recommended, for all three fields to be empty strings. In that case the
    generated class behaves the same as `ITEM_MAINCLASS`.

## What I updated in generation
- `java_code_tool.py`:
  - `_generate_mod_items_class` now inspects `IRItem.type`.
  - For `ITEM_NEWCLASS`, it calls `_generate_new_item_class`.
  - The registration uses `new <CustomClass>(settings)` instead of `new Item(...)`.
  - Imports are added if the class is outside `{package}.item`.
  - `isFood` now adds `FoodComponent` settings when true.
  - `isSword`/`isPickaxe` now apply `.sword(...)`/`.pickaxe(...)` settings.
  - Generates tag files for tool behavior:
    - `data/minecraft/tags/item/swords.json`
    - `data/minecraft/tags/item/pickaxes.json`
- `_generate_new_item_class`:
  - Creates a Java class in the specified `java_package`.
  - Injects `use`, `useOnBlock`, and `useOnEntity` as-is if provided.
  - If none are provided, the class will still compile but is useless.

## Required updates in upstream agents
- Orchestrator:
  - Must set `type` for every item to one of the three values.
  - Must populate the method strings for `ITEM_NEWCLASS`.
  - Should set tool/food flags and related stats when the item is meant to act
    as food or a tool (sword/pickaxe).
- SpecManager:
  - Should validate and persist `type` + method bodies in the spec.
  - Should validate `isFood`/`isSword`/`isPickaxe` are consistent with stats.
- Compiler:
  - Must carry `type` + method strings into `IRItem`.
  - Should enforce that `ITEM_NEWCLASS` has at least one method body, unless the
    intent is to mirror `ITEM_MAINCLASS` behavior (all three empty).
  - Must carry new tool/food flags and stats into the IR.

## Validation guidance
- Prefer failing fast if `ITEM_NEWCLASS` has empty `use`, `useOnBlock`, and `useOnEntity`,
  unless explicitly allowed to behave like `ITEM_MAINCLASS`.
- Consider warning if `ITEM_SUBCLASS` is used without an implemented subclass path.
- Ensure strings are complete method bodies, not snippets or partial blocks.

## Downstream inspection
- Generated Java code can include errors due to malformed method strings or
  missing imports. Downstream agents (for example, error handling or validation)
  should inspect generated Java sources and surface compiler errors with context.

## Action summary
- Update orchestrator/spec/compilation flow to assign `type` and method bodies.
- Add validation for `ITEM_NEWCLASS` requirements.
- Keep the IR deterministic: no runtime interpretation of missing methods.
