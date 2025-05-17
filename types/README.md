# Workers Types Generator

This directory contains scripts for automatically generating TypeScript types
from [JSG RTTI](../src/workerd/jsg/rtti.h).

## Generating Types

```shell
# Generates types to `../bazel-bin/types/api.d.ts`
$ bazel build //types:types
```

## Developing Generator Scripts

When developing generator scripts with an IDE, you'll need to install
dependencies yourself for integrated type checking and completions to work.

```shell
# Generates JSG RTTI Cap’n Proto JavaScript/TypeScript files
$ bazel build //src/workerd/jsg:rtti_capnp_js
# Install dependencies (note pnpm is required by https://github.com/aspect-build/rules_js)
$ pnpm install
# Generates types to `../bazel-bin/types/api.d.ts`
$ bazel build //types:types
# Run tests
$ bazel test //types:all
```

## Structure

- `src/generator`: generating TypeScript AST nodes from JSG RTTI
- `src/transforms`: post-processing TypeScript AST transforms
- `src/index.ts`: main entrypoint
- `src/{print,program}.ts`: helpers for printing nodes and creating programs
- `defines`: additional TypeScript-only definitions that don't correspond to
  `workerd` runtime APIs, appended to the end of outputs

## Updates types

```shell
just generate-types
```
