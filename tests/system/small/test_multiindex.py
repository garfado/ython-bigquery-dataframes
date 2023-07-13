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

import pandas
import pytest

import bigframes.pandas as bpd


def test_set_multi_index(scalars_df_index, scalars_pandas_df_index):
    bf_result = scalars_df_index.set_index(["bool_col", "int64_too"]).compute()
    pd_result = scalars_pandas_df_index.set_index(["bool_col", "int64_too"])

    pandas.testing.assert_frame_equal(bf_result, pd_result)


def test_reset_multi_index(scalars_df_index, scalars_pandas_df_index):
    bf_result = (
        scalars_df_index.set_index(["bool_col", "int64_too"]).reset_index().compute()
    )
    pd_result = scalars_pandas_df_index.set_index(
        ["bool_col", "int64_too"]
    ).reset_index()

    # Pandas uses int64 instead of Int64 (nullable) dtype.
    pd_result.index = pd_result.index.astype(pandas.Int64Dtype())

    pandas.testing.assert_frame_equal(bf_result, pd_result)


def test_binop_series_series_matching_multi_indices(
    scalars_df_index, scalars_pandas_df_index
):
    bf_left = scalars_df_index.set_index(["bool_col", "string_col"])
    bf_right = scalars_df_index.set_index(["bool_col", "string_col"])
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "string_col"])
    pd_right = scalars_pandas_df_index.set_index(["bool_col", "string_col"])

    bf_result = bf_left["int64_col"] + bf_right["int64_too"]
    pd_result = pd_left["int64_col"] + pd_right["int64_too"]

    pandas.testing.assert_series_equal(
        bf_result.sort_index().compute(), pd_result.sort_index()
    )


def test_binop_df_series_matching_multi_indices(
    scalars_df_index, scalars_pandas_df_index
):
    bf_left = scalars_df_index.set_index(["bool_col", "string_col"])
    bf_right = scalars_df_index.set_index(["bool_col", "string_col"])
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "string_col"])
    pd_right = scalars_pandas_df_index.set_index(["bool_col", "string_col"])

    bf_result = bf_left[["int64_col", "int64_too"]].add(bf_right["int64_too"], axis=0)
    pd_result = pd_left[["int64_col", "int64_too"]].add(pd_right["int64_too"], axis=0)

    pandas.testing.assert_frame_equal(
        bf_result.sort_index().compute(), pd_result.sort_index()
    )


def test_binop_multi_index_mono_index(scalars_df_index, scalars_pandas_df_index):
    bf_left = scalars_df_index.set_index(["bool_col", "rowindex_2"])
    bf_right = scalars_df_index.set_index("rowindex_2")
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "rowindex_2"])
    pd_right = scalars_pandas_df_index.set_index("rowindex_2")

    bf_result = bf_left["int64_col"] + bf_right["int64_too"]
    pd_result = pd_left["int64_col"] + pd_right["int64_too"]

    pandas.testing.assert_series_equal(bf_result.compute(), pd_result)


def test_binop_overlapping_multi_indices(scalars_df_index, scalars_pandas_df_index):
    bf_left = scalars_df_index.set_index(["bool_col", "int64_too"])
    bf_right = scalars_df_index.set_index(["bool_col", "int64_col"])
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "int64_too"])
    pd_right = scalars_pandas_df_index.set_index(["bool_col", "int64_col"])

    bf_result = bf_left["int64_col"] + bf_right["int64_too"]
    pd_result = pd_left["int64_col"] + pd_right["int64_too"]

    pandas.testing.assert_series_equal(
        bf_result.sort_index().compute(), pd_result.sort_index()
    )


def test_concat_compatible_multi_indices(scalars_df_index, scalars_pandas_df_index):
    if pandas.__version__.startswith("1."):
        pytest.skip("Labels not preserved in pandas 1.x.")
    bf_left = scalars_df_index.set_index(["bool_col", "int64_col"])
    bf_right = scalars_df_index.set_index(["bool_col", "int64_too"])
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "int64_col"])
    pd_right = scalars_pandas_df_index.set_index(["bool_col", "int64_too"])

    bf_result = bpd.concat([bf_left, bf_right])
    pd_result = pandas.concat([pd_left, pd_right])

    pandas.testing.assert_frame_equal(bf_result.compute(), pd_result)


def test_concat_multi_indices_ignore_index(scalars_df_index, scalars_pandas_df_index):
    bf_left = scalars_df_index.set_index(["bool_col", "int64_too"])
    bf_right = scalars_df_index.set_index(["bool_col", "int64_col"])
    pd_left = scalars_pandas_df_index.set_index(["bool_col", "int64_too"])
    pd_right = scalars_pandas_df_index.set_index(["bool_col", "int64_col"])

    bf_result = bpd.concat([bf_left, bf_right], ignore_index=True)
    pd_result = pandas.concat([pd_left, pd_right], ignore_index=True)

    # Pandas uses int64 instead of Int64 (nullable) dtype.
    pd_result.index = pd_result.index.astype(pandas.Int64Dtype())

    pandas.testing.assert_frame_equal(bf_result.compute(), pd_result)


def test_multi_index_loc(scalars_df_index, scalars_pandas_df_index):
    bf_result = (
        scalars_df_index.set_index(["int64_too", "bool_col"]).loc[[2, 0]].compute()
    )
    pd_result = scalars_pandas_df_index.set_index(["int64_too", "bool_col"]).loc[[2, 0]]

    pandas.testing.assert_frame_equal(bf_result, pd_result)


def test_multi_index_getitem_bool(scalars_df_index, scalars_pandas_df_index):
    bf_frame = scalars_df_index.set_index(["int64_too", "bool_col"])
    pd_frame = scalars_pandas_df_index.set_index(["int64_too", "bool_col"])

    bf_result = bf_frame[bf_frame["int64_col"] > 0].compute()
    pd_result = pd_frame[pd_frame["int64_col"] > 0]

    pandas.testing.assert_frame_equal(bf_result, pd_result)