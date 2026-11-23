import torch
import torch.nn.functional as F
import numpy as np
from typing import Dict, Optional


def generate_gradcam(
    model: torch.nn.Module,
    numerical: torch.Tensor,
    categorical_indices,
    images: Dict[str, Optional[torch.Tensor]],
    target_class: int,
    target_layer: str = "backbone.layer4",
    device: str = "cuda",
):
    model.eval()

    activations = {}
    gradients = {}

    def forward_hook(name):
        def hook(module, input, output):
            activations[name] = output.detach()
        return hook

    def backward_hook(name):
        def hook(module, grad_input, grad_output):
            gradients[name] = grad_output[0].detach()
        return hook

    backbone = getattr(model.image_encoder, "backbone", None)
    if backbone is None:
        raise ValueError("No backbone found in image_encoder")

    target_module = None
    for name, module in backbone.named_modules():
        if name == target_layer or name.endswith(target_layer):
            target_module = module
            break

    if target_module is None:
        last_layer = list(backbone.named_modules())[-1][1]
        target_module = last_layer

    fh = target_module.register_forward_hook(forward_hook("target"))
    bh = target_module.register_full_backward_hook(backward_hook("target"))
    output = model(numerical, categorical_indices, images)
    fh.remove()

    model.zero_grad()
    output[0, target_class].backward()
    bh.remove()

    weights = gradients["target"].mean(dim=(2, 3), keepdim=True)
    cam = (weights * activations["target"]).sum(dim=1, keepdim=True)
    cam = F.relu(cam)
    cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
    cam = cam.squeeze().cpu().numpy()
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)

    return cam
