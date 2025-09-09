# Reflect Command

## Description

Prompts Claude to reflect on learnings from the current conversation and suggest improvements to the project's CLAUDE.md file.

## Usage

Type `/reflect` to trigger Claude's reflection process.

## Prompt

Please reflect on what you've learned from our conversation and suggest specific improvements to the CLAUDE.md file. Consider:

1. **New commands or patterns discovered**: Have you encountered any uv commands, development workflows, or common tasks that aren't documented in CLAUDE.md?

2. **Architecture insights**: Did you learn anything new about the filter system, module relationships, or development patterns that would help future Claude instances?

3. **Environment or setup requirements**: Were there any missing virtual environment setup, configuration steps, or dependencies that caused issues?

4. **Testing and CI/CD improvements**: Did you discover any testing patterns, tox workflows, or pre-commit configuration details that should be documented?

5. **Common troubleshooting scenarios**: What problems did we solve that future developers might encounter?

6. **Missing context**: What information would have made you more effective earlier in our conversation?

Based on your reflection, suggest specific additions, modifications, or reorganisations to CLAUDE.md. Then proceed to implement these improvements directly by editing the CLAUDE.md file.

Focus on practical, actionable improvements that will help future Claude instances be more productive from the start. After making your changes, provide a brief summary of what you've updated.