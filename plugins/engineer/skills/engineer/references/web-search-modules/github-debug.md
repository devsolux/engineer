# GitHub Debug Module

**Last verified**: 2026-10-22 · **Review cadence**: 6 months
Translation and structure review; search-site operators were not re-tested against live sites.

> Extracted strategy pack for GitHub and debugging searches (from web-search-agent.md).

**Trigger scenarios**: project bugs, error debugging, issue lookup, version-specific problems

## Search sources
- **GitHub Issues** (both open and closed) - excellent for known bugs and workarounds

## Query strategy (1.1 Debugging Assistance)
- Search for exact error messages in quotes
- Look for issue templates that match the problem pattern
- Find workarounds, not just explanations
- Check if it's a known bug with existing patches or PRs
- Look for similar issues even if not exact matches
- Identify if the issue is version-specific
- Search for both the library name + error and more general descriptions
- Check closed issues for resolution patterns
