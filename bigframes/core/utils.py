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
import typing
from typing import Hashable, Iterable, List

import pandas as pd
import typing_extensions

import third_party.bigframes_vendored.pandas.io.common as vendored_pandas_io_common

UNNAMED_COLUMN_ID = "bigframes_unnamed_column"
UNNAMED_INDEX_ID = "bigframes_unnamed_index"


def get_axis_number(axis: typing.Union[str, int, None]) -> typing.Literal[0, 1]:
    if axis in {0, "index", "rows", None}:
        return 0
    elif axis in {1, "columns"}:
        return 1
    raise ValueError(f"Not a valid axis: {axis}")


def is_list_like(obj: typing.Any) -> typing_extensions.TypeGuard[typing.Sequence]:
    return pd.api.types.is_list_like(obj)


def is_dict_like(obj: typing.Any) -> typing_extensions.TypeGuard[typing.Mapping]:
    return pd.api.types.is_dict_like(obj)


def get_standardized_ids(
    col_labels: Iterable[Hashable], idx_labels: Iterable[Hashable] = ()
) -> tuple[list[str], list[str]]:
    """Get stardardized column ids as column_ids_list, index_ids_list.
    The standardized_column_id must be valid BQ SQL schema column names, can only be string type and unique.

    Args:
        col_labels: column labels

        idx_labels: index labels, optional. If empty, will only return column ids.

    Return:
        Tuple of (standardized_column_ids, standardized_index_ids)
    """
    col_ids = [
        UNNAMED_COLUMN_ID if col_label is None else str(col_label)
        for col_label in col_labels
    ]
    idx_ids = [
        UNNAMED_INDEX_ID if idx_label is None else str(idx_label)
        for idx_label in idx_labels
    ]

    ids = idx_ids + col_ids
    # Column values will be loaded as null if the column name has spaces.
    # https://github.com/googleapis/python-bigquery/issues/1566
    ids = [id.replace(" ", "_") for id in ids]

    ids = typing.cast(
        List[str],
        vendored_pandas_io_common.dedup_names(ids, is_potential_multiindex=False),
    )
    idx_ids, col_ids = ids[: len(idx_ids)], ids[len(idx_ids) :]

    return col_ids, idx_ids
