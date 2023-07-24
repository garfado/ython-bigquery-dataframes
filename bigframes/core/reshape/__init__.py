# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import typing
from typing import Iterable, Literal, Optional, Union

import bigframes.core as core
import bigframes.dataframe
import bigframes.operations.aggregations as agg_ops
import bigframes.series


@typing.overload
def concat(
    objs: Iterable[bigframes.dataframe.DataFrame], *, join, ignore_index
) -> bigframes.dataframe.DataFrame:
    ...


@typing.overload
def concat(
    objs: Iterable[bigframes.series.Series], *, join, ignore_index
) -> bigframes.series.Series:
    ...


def concat(
    objs: Union[
        Iterable[bigframes.dataframe.DataFrame], Iterable[bigframes.series.Series]
    ],
    *,
    join: Literal["inner", "outer"] = "outer",
    ignore_index: bool = False,
) -> Union[bigframes.dataframe.DataFrame, bigframes.series.Series]:
    contains_dataframes = any(
        isinstance(x, bigframes.dataframe.DataFrame) for x in objs
    )
    if not contains_dataframes:
        # Special case, all series, so align everything into single column even if labels don't match
        series = typing.cast(typing.Iterable[bigframes.series.Series], objs)
        names = {s.name for s in series}
        # For series case, labels are stripped if they don't all match
        if len(names) > 1:
            blocks = [s._block.with_column_labels([None]) for s in series]
        else:
            blocks = [s._block for s in series]
        block = blocks[0].concat(blocks[1:], how=join, ignore_index=ignore_index)
        return bigframes.series.Series(block)
    blocks = [obj._block for obj in objs]
    block = blocks[0].concat(blocks[1:], how=join, ignore_index=ignore_index)
    return bigframes.dataframe.DataFrame(block)


def cut(
    x: bigframes.series.Series,
    bins: int,
    *,
    labels: Optional[bool] = None,
) -> bigframes.series.Series:
    if bins <= 0:
        raise ValueError("`bins` should be a positive integer.")

    if labels is not False:
        raise NotImplementedError(
            "Only labels=False is supported in BigQuery DataFrames so far."
        )
    return x._apply_window_op(agg_ops.CutOp(bins), window_spec=core.WindowSpec())