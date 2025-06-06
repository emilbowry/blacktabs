import importlib.metadata
import sys


def test_schema_entrypoint() -> None:
    if sys.version_info < (3, 10):
        eps = importlib.metadata.entry_points()["validate_pyproject.tool_schema"]
        (monochromatic_ep,) = [ep for ep in eps if ep.name == "monochromatic"]
    else:
        (monochromatic_ep,) = importlib.metadata.entry_points(
            group="validate_pyproject.tool_schema", name="monochromatic"
        )

    monochromatic_fn = monochromatic_ep.load()
    schema = monochromatic_fn()
    assert schema == monochromatic_fn("monochromatic")
    assert schema["properties"]["line-length"]["type"] == "integer"
