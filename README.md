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

## 💭 A Note on AI & The Future of Software

As a software engineer with 20+ years of production experience across firmware, systems, video games, distributed systems and frontend development, I'm incredibly excited about the future of LLM-assisted coding. This project isn't just a demo - it's a revelation about how AI fundamentally changes the development experience.

The key insight isn't about commit counts or development speed - I could have hand-written this program more efficiently in terms of raw commits and iterations. What's revolutionary is the dramatic reduction in cognitive load. I finished this project feeling energized rather than exhausted, having spent almost no time trudging through source code and documentation hunting for gotchas and edge cases. The AI handled that cognitive heavy lifting, letting me focus on architecture and design decisions.

This transformation in the development experience is what makes me bullish about the future. We're looking at a world where AI doesn't just help us code faster - it fundamentally changes how we interact with complex technical systems. The global demand for software is infinite, and now we can meet that demand while keeping developers fresh and focused on the creative and architectural challenges that truly need human insight.

This isn't about replacement - it's about unlocking human potential. When AI handles the cognitive overhead of implementation details, we're free to tackle bigger challenges and push the boundaries of what's possible. The future of software isn't just about writing more code - it's about building better systems with less mental fatigue.

## 🙏 Big Thanks To

- [UV](https://github.com/astral-sh/uv) - Speed demon Python package installer
- [Aider](https://github.com/paul-gauthier/aider) - Your AI pair programming buddy
- [Anthropic](https://www.anthropic.com) - For the absolutely massive Claude 3.5 Sonnet
- [Helix Editor](https://helix-editor.com/) - Modal editing at its finest
- [Grok 2](https://grok.x.ai/) - Extra AI muscle

## 📄 License

MIT