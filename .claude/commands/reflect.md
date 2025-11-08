# Reflect Command

## Description

Prompts Claude to reflect on learnings from the current conversation and suggest improvements to the project's CLAUDE.md file. This command helps maintain documentation quality by systematically evaluating what should be added, updated, or removed based on real development experience.

## Usage

Type `/reflect` to trigger Claude's reflection process.

**Best used when:**
- Completing a significant development task or project phase
- After resolving complex issues that required learning new patterns
- When onboarding workflows or setup procedures have changed
- Periodically to prevent documentation drift

## Prompt

Please reflect on what you've learned from our conversation and suggest specific improvements to the CLAUDE.md file. Consider both additions and removals:

## What to Add or Update:

1. **New commands or patterns discovered**: Have you encountered any uv commands, development workflows, or common tasks that aren't documented in CLAUDE.md?

2. **Architecture insights**: Did you learn anything new about the filter system, module relationships, or development patterns that would help future Claude instances?

3. **Environment or setup requirements**: Were there any missing virtual environment setup, configuration steps, or dependencies that caused issues?

4. **Testing and CI/CD improvements**: Did you discover any testing patterns, tox workflows, or pre-commit configuration details that should be documented?

5. **Common troubleshooting scenarios**: What problems did we solve that future developers might encounter?

6. **Missing context**: What information would have made you more effective earlier in our conversation?

## What to Remove or Simplify:

7. **Outdated information**: Are there any commands, patterns, or troubleshooting scenarios in CLAUDE.md that are no longer relevant due to changes in dependencies, Python versions, or project structure?

8. **Overly-specific scenarios**: Are there any very specific problems or solutions documented that were one-time issues unlikely to recur? These might clutter the guidance without providing lasting value.

9. **Redundant or conflicting guidance**: Is there any information that duplicates other sections or contradicts current best practices?

10. **Stale version-specific notes**: Are there any references to specific package versions, Python versions, or tool versions that are no longer current and might mislead future users?

## What to Reorganise:

11. **Information hierarchy**: Could any sections be better organised or moved to improve logical flow and findability?

12. **Section consolidation**: Are there scattered pieces of related information that should be grouped together?

13. **Cross-references**: Are there missing links between related sections or concepts that would help navigation?

## Implementation Instructions

Based on your reflection, suggest specific additions, modifications, removals, or reorganisations to CLAUDE.md. Then proceed to implement these improvements directly by editing the CLAUDE.md file.

**Implementation approach:**
1. Start with a brief analysis of what you discovered
2. Make the actual file changes
3. Provide a summary organised by: **Added**, **Updated**, **Removed**, **Reorganised**

Focus on practical, actionable improvements that will help future Claude instances be more productive from the start while keeping the documentation lean and current.