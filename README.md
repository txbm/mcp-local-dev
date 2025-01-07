![MCP Local Dev Demo](placeholder-for-demo.gif)

# 🚀 MCP Local Dev

Let AI handle your local development environments while you focus on building amazing things!

## ✨ What's This?

A local development environment manager that lets LLMs configure and manage dev environments for you. Built with ❤️ by AI, for AI, for developers who want their LLM assistant to handle environment setup, dependency management, and testing automatically.

## 🎯 Features That Slap

- 🤖 **Pure AI Magic**: Just tell your LLM to set up a dev environment for any GitHub repo
- 🧪 **Full Auto**: Automatic dependency installation, environment setup, and test running
- ⚡️ **Multiple Runtimes**: First-class support for Node.js, Bun, and Python+UV
- 🛠️ **Zero Config**: Everything just works™️ - no more environment headaches

## 🏃 Quick Start

1. Install Claude Desktop from the [MCP quickstart guide](https://modelcontextprotocol.io/quickstart/user)
2. Add the following to your Claude Desktop config:

```json
{
  "servers": {
    "local-dev": {
      "type": "github",
      "repo": "txbm/mcp-local-dev",
      "tools": ["uvx"],
      "config": {
        "workdir": "~/mcp-dev"
      }
    }
  }
}
```

3. Point Claude at any GitHub repository and ask it to set up a dev environment! 

## 💫 Under the Hood

- **MCP Server Spec**: Full compliance with comprehensive test coverage
- **Path Isolation**: Each environment is neatly contained
- **System Integration**: Uses your installed runtimes (Python, Node.js, Bun)
- **Package Management**: Automatically selects fastest available package manager for each runtime
- **Network Access**: Full connectivity for package management
- **Process Handling**: Native system processes for maximum speed

## 🌟 Behind the Scenes

Development involved rigorous testing across multiple models:
- 🏆 Claude 3.5 Sonnet: Crushed it
- 💪 DeepSeek V3: Strong performer
- 👎 O1: Not great, Bob

## 🚀 Key Takeaways

This project demonstrates the incredible potential of AI-assisted development:
- 🏃‍♂️ Lightning fast prototyping
- 🎯 That last 15% is still where the real work happens
- 📚 Great example of real-world AI development patterns

## 💭 A Note on AI & Development

As someone who's spent years in software development, what's exciting about this project isn't just automation - it's the shift in how we interact with development environments. The value isn't in replacing human developers, but in reducing cognitive overhead. When AI handles environment setup and maintenance, developers can focus more on architecture and design decisions.

This project demonstrates that AI isn't just about generating code - it's about managing complexity. By handling the mechanical aspects of development environment setup, we free up mental bandwidth for the creative and architectural challenges that truly need human insight.

## 🙏 Big Thanks To

- [UV](https://github.com/astral-sh/uv) - Speed demon Python package installer
- [Aider](https://github.com/paul-gauthier/aider) - Your AI pair programming buddy
- [Anthropic](https://www.anthropic.com) - For Claude's assistance in development
- [Helix Editor](https://helix-editor.com/) - Modal editing at its finest

## 📄 License

MIT
