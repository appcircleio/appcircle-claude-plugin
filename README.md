# Appcircle Claude Plugin

Appcircle's official plugin for Claude. It connects Claude to the [Appcircle](https://appcircle.io) mobile CI/CD platform, covering build, code signing, distribution, publishing (App Store / Google Play), and testing, so you can ask Appcircle questions and look up your own organization's data right from chat.

## Install in Claude Code

This repo is itself a Claude Code plugin marketplace.

```shell
/plugin marketplace add appcircleio/appcircle-claude-plugin
/plugin install appcircle@appcircle
/reload-plugins
```

## Using it in claude.ai

You can install this plugin's skills in claude.ai too:

1. Open **Customize**.
2. Click **Add plugin**.
3. Choose **Create plugin**, then **Add marketplace**.
4. Enter the repository URL: `https://github.com/appcircleio/appcircle-claude-plugin`.

MCP tools are only available in Claude Code for now; installing the plugin in claude.ai gets you the skills, not the MCP tools.

## Skills

| Skill | Purpose |
|-------|---------|
| `appcircle:doc-assistant` | Answers Appcircle questions from official docs and product sources |

Claude invokes a skill automatically when your question matches its purpose, or you can call it directly in Claude Code:

```
/appcircle:doc-assistant How do I configure iOS code signing for a build profile?
```

## MCP server (Claude Code only)

The plugin registers `mcp.appcircle.io` as an MCP server named `appcircle`, authenticated via a bearer-token header using an Appcircle access token. For the full list of available tools and how it works, see the [Appcircle MCP](https://github.com/appcircleio/appcircle-mcp) repository.

### Configure the MCP server

The server authenticates with an `APPCIRCLE_ACCESS_TOKEN`, which you can obtain from either credential type:

- [Personal Access Key](https://docs.appcircle.io/account/my-organization/security/personal-access-key)
- [API Key](https://docs.appcircle.io/account/my-organization/security/api-keys)

1. Export it in the environment where Claude Code runs:

   ```bash
   export APPCIRCLE_ACCESS_TOKEN=<your-token>
   ```
2. Restart/reload Claude Code so the MCP server picks up the token.
3. Re-export and reload when it expires.

Without this, the MCP tools won't be able to authenticate. The doc-assistant skill works regardless, since it only reads public documentation.

## Local development

These commands require the Claude Code CLI. Test the plugin without installing it by loading the directory directly:

```bash
claude --plugin-dir .
```

Validate it against the standard plugin schema:

```bash
claude plugin validate .
```
