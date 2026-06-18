# Appcircle Claude Plugin

A Claude plugin that bundles Appcircle-aware skills and MCP connectivity to the
Appcircle platform, the mobile-focused CI/CD platform covering build, code signing,
distribution, publishing (App Store / Google Play), and testing. The plugin is
designed to grow: new skills can be added under `skills/` over time and are
automatically namespaced under `appcircle:`.

## Skills

Each subdirectory under `skills/` is an independent skill. Currently bundled:

| Skill | Purpose |
|-------|---------|
| `appcircle:doc-assistant` | Answers Appcircle questions from official docs and product sources |

More skills can be added over time: drop a new `skills/<name>/SKILL.md` and it
becomes available as `appcircle:<name>`.

## MCP Server

The plugin registers `mcp.appcircle.io` as an MCP server named `appcircle`.

**Required env var:**

```bash
export APPCIRCLE_ACCESS_TOKEN=<your-pat>
```

## Install

Install via the plugin marketplace (this repo ships its own `marketplace.json`):

```shell
/plugin marketplace add appcircleio/appcircle-claude-plugin
/plugin install appcircle@appcircle
```

Then reload:

```shell
/reload-plugins
```

## Local development

Test without installing by loading the plugin directory directly:

```bash
claude --plugin-dir .
```

Validate the plugin against the standard schema:

```bash
claude plugin validate .
```
