import torch

# Matches TabularModel's construction in model_loader._build_model.
DEFAULT_CAT_CARDINALITIES = [2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 3, 4, 3, 3, 3, 2]


def export_to_onnx(
    model: torch.nn.Module,
    output_path: str = "model.onnx",
    num_numerical: int = 7,
    cat_cardinalities: list = None,
):
    if cat_cardinalities is None:
        cat_cardinalities = DEFAULT_CAT_CARDINALITIES
    model.eval()
    dummy_numerical = torch.randn(1, num_numerical)
    dummy_cat = [torch.zeros(1, dtype=torch.long) for _ in cat_cardinalities]
    input_names = ["numerical"] + [f"cat_{i}" for i in range(len(cat_cardinalities))]
    torch.onnx.export(
        model,
        (dummy_numerical, *dummy_cat),
        output_path,
        input_names=input_names,
        output_names=["logits"],
        dynamic_axes={name: {0: "batch"} for name in input_names},
        opset_version=17,
    )
    print(f"Model exported to {output_path}")
