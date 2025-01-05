![MCP Local Dev Demo](placeholder-for-demo.gif)

# MCP Local Dev

A fully automated local development environment manager for MCP-connected Language Models. This groundbreaking tool enables any MCP-compliant LLM to manage development environments, run tests, execute shell commands, and more - all within path-isolated local environments.

## 🚀 Highlights

- **Fully Automated**: Let your MCP-connected LLMs handle local development tasks autonomously
- **Path Isolation**: Operations run in path-isolated environments with their own virtual filesystem layout
- **System Integration**: Leverages existing system and runtime binaries while handling all environment-specific setup
- **MCP Spec Compliant**: Complete implementation of the MCP specification with comprehensive test coverage
- **AI-Generated**: 98% of the codebase was written by Claude 3.5 Sonnet using [Aider](https://github.com/paul-gauthier/aider)
- **Open Development**: Full, unredacted Git history preserved for research and analysis

## 🤖 An AI Development Experiment

This project stands as one of the few public examples of a non-trivial program being implemented almost entirely by an LLM with minimal human intervention. The complete Git history has been preserved to provide researchers and developers insights into the current state of AI-assisted development, including:

- Development patterns and "churn inefficiency"
- Regression patterns and recovery strategies
- Prompting techniques and context optimization
- Real-world examples of LLM-driven development workflows

## 📊 Model Performance Analysis

During development, multiple LLM models were evaluated:

- **Claude 3.5 Sonnet**: Excellent performance, primary development model
- **DeepSeek V3**: Strong results, particularly with system-level operations
- **O1**: Poor performance, not recommended for this use case

## ⚡️ Installation

1. Install the MCP Claude desktop client
2. Ensure required system and runtime binaries are installed (Python, Node.js, etc. as needed)
3. Clone this repository:
```bash
git clone https://github.com/txbm/mcp-local-dev
cd mcp-local-dev
```
4. Configure your MCP environment:
```bash
mcp configure local-dev
```

## 🛠 Command Reference

```bash
mcp local-dev init          # Initialize a new dev environment
mcp local-dev test         # Run test suite in isolated environment
mcp local-dev shell        # Open interactive shell in environment
mcp local-dev exec         # Execute command in environment
mcp local-dev clean        # Clean up environments
```

## 💡 Key Insights

- **Rapid Prototyping**: Achieved incredible time-to-value for initial development
- **The 80/20 Rule Persists**: While LLMs excel at initial implementation, the final 15% refinement remains challenging
- **Context is King**: Success heavily dependent on providing models with:
  - MCP Python SDK source code
  - Third-party library documentation
  - Convention files and best practices

## 🏗️ Environment Details

The tool provides path-isolated environments for development tasks with some important characteristics:

- **Path Isolation**: Each environment gets its own virtual filesystem layout
- **System Dependencies**: Relies on standard system binaries being present (bash, grep, etc.)
- **Runtime Dependencies**: Requires application runtime binaries (Python, Node.js, etc.) to be installed
- **Network Access**: Environments have normal network access - not network isolated
- **Process Isolation**: Processes run as normal system processes - not containerized

While not providing full containerization, the tool handles all environment-specific setup, dependencies, and virtual filesystem management automatically.

## 🤝 Acknowledgments

- [Aider](https://github.com/paul-gauthier/aider) - AI pair programming tool
- [Anthropic](https://www.anthropic.com) - Claude 3.5 Sonnet
- [Helix Editor](https://helix-editor.com/) - Text editor
- [Grok 2](https://grok.x.ai/) - Additional testing and validation

## 📝 License

MIT