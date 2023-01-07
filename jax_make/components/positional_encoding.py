from abc import abstractmethod
from functools import reduce
from math import prod
from typing import NamedTuple, Protocol, Tuple, Literal

import jax.numpy as xp
import numpy.typing as npt
from jax import vmap, jit, tree_map

from jax_make.component_protocol import Component, X, FixedProcess, make_ports, pipeline_ports
from jax_make.params import WeightParams, ArrayTree, ArrayTreeMapping
import jax_make.params as p

PositionalEncodeStrategies = Literal['dot', 'sum', 'naive_sum']


class PositionalEncodingConfigs(Protocol):
    @property
    @abstractmethod
    def input_shape(self) -> Tuple[int, ...]: ...

    @property
    @abstractmethod
    def input_channels(self) -> int: ...

    @property
    @abstractmethod
    def output_channels(self) -> int: ...

    @property
    @abstractmethod
    def dim_encoding(self) -> int: ...

    @property
    @abstractmethod
    def positional_encode_strategy(self) -> PositionalEncodeStrategies: ...

    @property
    @abstractmethod
    def init_scale(self) -> float: ...


class PositionalEncoding(NamedTuple):
    input_shape: Tuple[int, ...]
    input_channels: int
    output_channels: int
    dim_encoding: int
    positional_encode_strategy: PositionalEncodeStrategies
    init_scale: float

    @staticmethod
    def make(config: PositionalEncodingConfigs) -> Component:
        assert config.output_channels == config.dim_encoding == config.input_channels

        if config.positional_encode_strategy == 'dot':
            components = {
                f'encoding_dim_{i}': WeightParams(shape=(config.dim_encoding, dim),
                                                  init="embedding",
                                                  scale=config.init_scale / len(config.input_shape))
                for i, dim in enumerate(config.input_shape)
            }

            # [input_channels, *input_shape] -> [output_channels, prod(input_shape)]
            def _fn(weights: ArrayTreeMapping, x: npt.NDArray) -> npt.NDArray:
                x *= dot_product_encode(weights, len(config.input_shape))
                # [output_channels, *input_shape]

                return x.reshape(config.output_channels, prod(config.input_shape))

            return Component.from_fixed_pipeline(components, _fn)

        elif config.positional_encode_strategy == 'sum':
            components = {
                f'encoding_dim_{i}': WeightParams(shape=(config.dim_encoding, dim),
                                                  init="embedding",
                                                  scale=config.init_scale / len(config.input_shape))
                for i, dim in enumerate(config.input_shape)
            }

            # [input_channels, *input_shape] -> [output_channels, prod(input_shape)]
            def _fn(weights: ArrayTreeMapping, x: npt.NDArray) -> npt.NDArray:

                x += sum_encode(weights, config.input_shape)
                # [output_channels, *input_shape]

                return x.reshape(config.output_channels, prod(config.input_shape))

            return Component.from_fixed_pipeline(components, _fn)
        elif config.positional_encode_strategy == 'naive_sum':
            dict_size = prod(config.input_shape)
            components = {
                f'encoding_all_dim': WeightParams(shape=(config.dim_encoding, dict_size),
                                                  init="embedding",
                                                  scale=config.init_scale)
            }

            # [input_channels, *input_shape] -> [output_channels, prod(input_shape)]
            def _fn(weights: ArrayTreeMapping, x: npt.NDArray) -> npt.NDArray:
                x = x.reshape(config.output_channels, prod(config.input_shape))
                # [output_channels, *input_shape]

                x += p.get_arr(weights, 'encoding_all_dim')

                return x

            # noinspection PyTypeChecker
            # Because Pycharm sucks
            return Component.from_fixed_pipeline(components, _fn)
        else:
            raise ValueError(f"Positional encoding type {config.positional_encode_strategy} is not supported")


# {} -> [output_channels, *input_shape]
def dot_product_encode(weights: ArrayTreeMapping, input_n_dims: int) -> npt.NDArray:
    def _t_outer(a: npt.NDArray, b: npt.NDArray) -> npt.NDArray:
        return a[..., None] @ b[None, :]

    pos_encode = reduce(vmap(_t_outer, (0, 0), 0),
                        [p.get_arr(weights, f'encoding_dim_{i}') for i in range(input_n_dims)])
    return pos_encode


# {} -> [output_channels, *input_shape]
def sum_encode(weights: ArrayTreeMapping, input_shape: Tuple[int, ...]) -> npt.NDArray:
    return reduce(xp.add,
                  (p.get_arr(weights, f'encoding_dim_{i}').reshape(
                      [-1] + [n if ii == i else 1 for ii, n in enumerate(input_shape)])
                      for i in range(len(input_shape)))
                  )
    # pos_encode = xp.zeros(input_shape)
    # for i in range(len(input_shape)):
    #     tile_shape = list(input_shape)
    #     tile_shape[i] = 1
    #     pos_encode += xp.tile(p.get_arr(weights, f'encoding_dim_{i}'), tile_shape)
    # return pos_encode


# {} -> [output_channels, *input_shape]
def dot_product_encode2(weights: ArrayTreeMapping, input_shape: Tuple[int, ...]) -> npt.NDArray:
    return reduce(xp.multiply,
                  (p.get_arr(weights, f'encoding_dim_{i}').reshape(
                      [-1] + [n if ii == i else 1 for ii, n in enumerate(input_shape)])
                      for i in range(len(input_shape)))
                  )
# assert (dot_product_encode(params, len(config.input_shape)) == dot_product_encode2(params,
#                                                                                    config.input_shape)).all()
