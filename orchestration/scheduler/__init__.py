"""DAG scheduling: dependency validation, graph helpers, async executor.

Keep this file free of imports so that `state` and `scheduler` can import each
other's submodules without circular-import problems.
"""
