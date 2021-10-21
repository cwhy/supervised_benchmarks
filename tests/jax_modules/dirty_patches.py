from functools import reduce
import jax.numpy as xp
from typing import NamedTuple, Protocol, Tuple, Literal, List

import jax
import numpy.typing as npt
from einops import rearrange
from jax import vmap

from tests.jax_activations import Activation
from tests.jax_components import Component
from tests.jax_modules.mlp import MlpConfigs, Mlp
from tests.jax_random_utils import WeightParams, ArrayTree, RNGKey


class DirtyPatchesConfigs(Protocol):
    dim_out: int
    n_sections_w: int
    n_sections_h: int
    w: int
    h: int
    ch: int
    mlp_n_hidden: List[int]
    mlp_activation: Activation
    dropout_keep_rate: float


class DirtyPatches(NamedTuple):
    dim_out: int
    n_sections_w: int
    n_sections_h: int
    w: int
    h: int
    ch: int
    mlp_n_hidden: List[int]
    mlp_activation: Activation
    dropout_keep_rate: float

    @staticmethod
    def make(config: DirtyPatchesConfigs) -> Component:
        assert config.w % config.n_sections_w == 0
        assert config.h % config.n_sections_h == 0
        dim_w = config.w // config.n_sections_w
        dim_h = config.h // config.n_sections_h
        components = {
            'mlp': Mlp.make(Mlp(
                n_hidden=config.mlp_n_hidden,
                activation=config.mlp_activation,
                dropout_keep_rate=config.dropout_keep_rate,
                n_in=dim_w * dim_h,
                n_out=config.dim_out
            ))
        }

        # [h, w, ch] -> [dim_out, n_sections_h, n_sections_w, ch]
        def _fn(params: ArrayTree, x: npt.NDArray, rng: RNGKey) -> npt.NDArray:
            x = xp.expand_dims(x, axis=0)
            # n h w c
            patches = jax.lax.conv_general_dilated_patches(
                lhs=x,
                filter_shape=(dim_h, dim_w),
                window_strides=(dim_h, dim_w),
                padding='VALID',
                rhs_dilation=(1, 1),
                dimension_numbers=("NHWC", "OIHW", "NHWC")
            ).squeeze(0)
            # n_patches_h, n_patches_w, ch*dim_h*dim_w
            patches = rearrange(patches, 'h w (c ph pw) -> (h w c) (ph pw)',
                                c=config.ch, ph=dim_h, pw=dim_w)

            features = vmap(components['mlp'].process, (None, 0, None), 0)(params['mlp'], patches, rng)
            return rearrange(features, '(h w c) out -> out h w c',
                             out=config.dim_out, h=config.n_sections_h, w=config.n_sections_w, c=config.ch)

        return Component({k: v.params for k, v in components.items()}, _fn)
