# R15-CODE-RESEARCH-005 (second attempt, CN) - RESULT

- Stamped: 06:55 IST
- Branch: worktree-agent-lows-CN-r15-code-research-005-4c6dfe8 (base 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2)
- Outcome: fixed_untested
- Cherry-picked: none (the prior branch worktree-agent-lows-P1-W3-actions-research carries no commit for this entry)

## Commits
- 84c912e6 refactor(research): make deep's shared round helpers public exports
- 3f8dffa4 refactor(research): keep web_only_floor_note's signature line byte-stable

## Fix
The 15 underscore-private names that iter.py, verify.py and citecheck.py import from deep.py are now
public deep exports, listed in deep.__all__. This is a rename only, with no behaviour change:
_ROUND_MODEL, _ROUND_PROVIDER, _WEB_ONLY_FLOOR_NOTE -> ROUND_MODEL, ROUND_PROVIDER, WEB_ONLY_FLOOR_NOTE;
_Findings -> Findings; _emit -> emit_step; _safe_llm, _safe_tool -> safe_llm, safe_tool;
_record_structured, _record_web, _reflect_says_complete, _round_wall_limit, _run_researcher,
_split_subquestions, _synthesis_llm, _synthesize_brief -> the same names without the underscore.
No services/research module imports another module's underscore name any more.

Deviation from fix_shape (Tier 2): I promoted the helpers in place instead of moving them to a
new _loop.py. The dead loop is already gone (R15-CODE-RESEARCH-003, 9703eee7), so deep.py is purely
the shared helper module. Moving everything to _loop.py would leave deep.py empty, which is just a
rename of the module. It would also churn the deep_research tool, about 20 tests and the
sys.modules stub in test_research_tools.py.

## Files
sidecar/services/research/{deep,iter,verify,citecheck,disclosures,relevance}.py
sidecar/tests/{test_b6_research_funnel,test_b7_research_sources,test_research_deep,test_research_depth,
test_research_disclosures,test_research_r9_regressions,test_research_verify}.py (import/call renames, same assertions)
sidecar/tests/test_research_module_boundary.py (new acceptance test)

## Tests written (source only, NOT run: off-lane rule)
- test_no_research_module_imports_a_private_name_across_modules: an AST audit over services/research/**.py
  that finds no ImportFrom of an underscore name from a services.research module.
- test_shared_round_helpers_are_public_deep_exports: checks that the 15 helpers are in deep.__all__
  and that every __all__ name resolves.

## Checks run
ruff check, ruff format and py_compile passed on every touched file. A trial merge
`git merge-tree --write-tree origin/worktree-agent-lows-P1-W3-actions-research HEAD` is clean
(acdedfdf). On that merged tree:
- A grep finds no stale old name.
- `ruff check` (I001 ignored) passes on services/research and the research tests. The scratch
  copy lacks the first-party dirs, so isort there is environment-dependent.
- `ruff format --check` passes.
- py_compile passes.

## Untested pending integration
Every change. Pytest was not run (off-lane).

## Risks
- deep.py keeps one module-local alias `_Findings = Findings`, used only by web_only_floor_note's
  annotation. W3 (R15-RESEARCH-041) inserts is_web_search_source directly above that line, so
  renaming it conflicts when both branches merge. No other module uses the alias.
- Out-of-tree callers of the old private names would break. A search found none in sidecar or src.
  Historical docs under docs/ still mention the old names and are left as history.
- fast.py keeps its own private _emit (a duplicate of emit_step). It is not an import leak and is
  out of scope.
