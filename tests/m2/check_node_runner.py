
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from routing.node_runner import model_node_runner


fake_response = SimpleNamespace(
    content="Test response",
    resolved_model="test-model",
    requested_model="test-model",
    input_tokens=10,
    output_tokens=20,
    total_tokens=30,
    latency_ms=100,
    cost_usd=0.0
)


async def run_test():
    test_cases = [
        ("Support", "read", "low"),
        ("Finance", "read", "medium"),
        ("Finance", "write", "high"),
    ]

    for role, side_effect, expected_model in test_cases:
        node = SimpleNamespace(
            node_id="test_node",
            role=role,
            instruction="Perform a test task",
            params={},
            side_effect_class=side_effect,
            depends_on=()
        )

        state = SimpleNamespace(results={})

        with patch(
            "routing.node_runner.execute_route",
            return_value=fake_response
        ) as mock_execute:

            result = await model_node_runner(node, state)

            decision = mock_execute.call_args.args[0]

            assert decision.selected_model == expected_model
            print("Actual status:", repr(result.status))
            assert result.status.value == "success"
            assert result.output["content"] == "Test response"

            print(f"{role} / {side_effect}: PASSED ({expected_model})")


asyncio.run(run_test())

print("\nNode runner integration test passed!")
