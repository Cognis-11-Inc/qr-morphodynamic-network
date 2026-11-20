"""Small external-only QR13 predictors; no simulator state mutation interface."""

import contextlib
import time

import numpy as np
import torch
from torch import nn


def setup(seed=17):
    torch.set_num_threads(1)
    with contextlib.suppress(RuntimeError):
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)


class Predictor(nn.Module):
    """Bounded residual forecast over three physical-time horizons."""

    def __init__(self, features, palettes, outputs, kind="mlp"):
        super().__init__()
        self.kind = kind
        if kind == "mlp":
            self.network = nn.Sequential(
                nn.Linear(3 * features + palettes, 32), nn.Tanh(), nn.Linear(32, outputs)
            )
        else:
            self.gru = nn.GRU(features, 32, batch_first=True)
            self.network = nn.Sequential(
                nn.Linear(32 + palettes, 32), nn.Tanh(), nn.Linear(32, outputs)
            )

    def forward(self, x, palette):
        state = x.flatten(1) if self.kind == "mlp" else self.gru(x)[0][:, -1]
        return self.network(torch.cat((state, palette), dim=1))


class Autoencoder(nn.Module):
    """Rank-eight external state representation, with no physical interpretation built in."""

    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(512, 32), nn.Tanh(), nn.Linear(32, 8), nn.Tanh())
        self.decoder = nn.Sequential(nn.Linear(8, 32), nn.Tanh(), nn.Linear(32, 512))

    def forward(self, x):
        return self.decoder(self.encoder(x))


def uv_loss(pred, target, scale, crossing=None):
    e = ((pred - target) / scale) ** 2
    e = e.reshape(len(e), 3, -1, 130)[..., :128]
    if crossing is not None:
        e = e[np.asarray(crossing)]
    return float(e.mean()) if e.size else None


def predict(model, x, palette, batch=256):
    model.eval()
    with torch.no_grad():
        return np.concatenate(
            [
                model(
                    torch.from_numpy(x[i : i + batch]), torch.from_numpy(palette[i : i + batch])
                ).numpy()
                for i in range(0, len(x), batch)
            ]
        )


def fit_forecast(train, valid, kind, seed, epochs=120):
    setup(seed)
    x, p, y = train
    vx, vp, vy = valid
    model = Predictor(x.shape[-1], p.shape[-1], y.shape[-1], kind)
    count = sum(v.numel() for v in model.parameters())
    if count > 300000:
        raise ValueError("QR13 registered parameter cap")
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    rng = np.random.default_rng(seed)
    best = float("inf")
    checkpoint = None
    history = []
    begun = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        order = rng.permutation(len(x))
        for indices in np.array_split(order, max(1, int(np.ceil(len(x) / 256)))):
            opt.zero_grad(set_to_none=True)
            out = model(torch.from_numpy(x[indices]), torch.from_numpy(p[indices]))
            loss = ((out - torch.from_numpy(y[indices])) ** 2).mean()
            if not torch.isfinite(loss):
                raise ValueError("QR13 nonfinite training loss")
            loss.backward()
            opt.step()
        if epoch % 5 == 0 or epoch == epochs:
            prediction = predict(model, vx, vp).reshape(len(vy), 3, -1, 130)[..., :128]
            actual = vy.reshape(len(vy), 3, -1, 130)[..., :128]
            value = float(np.mean((prediction - actual) ** 2))
            history.append(dict(epoch=epoch, validation_uv_loss=value))
            if value < best:
                best = value
                checkpoint = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(checkpoint)
    return model, dict(
        kind=kind,
        seed=seed,
        parameters=count,
        epochs=epochs,
        best_validation_loss=best,
        seconds=time.perf_counter() - begun,
        history=history,
    )
