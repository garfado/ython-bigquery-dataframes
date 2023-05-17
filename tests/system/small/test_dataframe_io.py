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

import google.api_core.exceptions
import pandas as pd
import pytest

from tests.system.utils import (
    assert_pandas_df_equal_ignore_ordering,
    convert_pandas_dtypes,
)

try:
    import pandas_gbq  # type: ignore
except ImportError:
    pandas_gbq = None


def test_to_pandas_w_correct_dtypes(scalars_df_default_index):
    """Verify to_pandas() APIs returns the expected dtypes."""
    actual = scalars_df_default_index.to_pandas().dtypes
    expected = scalars_df_default_index.dtypes

    # TODO(chelsealin): Remove it after importing latest ibis with b/279503940.
    expected["timestamp_col"] = "timestamp[us, tz=UTC][pyarrow]"

    pd.testing.assert_series_equal(actual, expected)


@pytest.mark.parametrize(
    ("index"),
    [True, False],
)
def test_to_csv_index(scalars_dfs, gcs_folder, index):
    """Test the `to_csv` API with the `index` parameter."""
    scalars_df, scalars_pandas_df = scalars_dfs
    index_col = None
    if scalars_df.index.name is not None:
        path = gcs_folder + f"test_index_df_to_csv_index_{index}"
        if index:
            index_col = scalars_df.index.name
    else:
        path = gcs_folder + f"test_default_index_df_to_csv_index_{index}"

    scalars_df.to_csv(path, index=index)

    # Pandas dataframes dtypes from read_csv are not fully compatible with BigFrames
    # dataframes, so manually convert the dtypes specifically here.
    dtype = scalars_df.reset_index().dtypes.to_dict()
    dtype.pop("timestamp_col")
    dtype.pop("geography_col")
    gcs_df = pd.read_csv(
        path, dtype=dtype, parse_dates=["timestamp_col"], index_col=index_col
    )
    convert_pandas_dtypes(gcs_df, bytes_col=True)

    assert_pandas_df_equal_ignore_ordering(gcs_df, scalars_pandas_df)


@pytest.mark.parametrize(
    ("index"),
    [True, False],
)
@pytest.mark.skipif(pandas_gbq is None, reason="required by pd.read_gbq")
def test_to_gbq_index(scalars_dfs, dataset_id, index):
    """Test the `to_gbq` API with the `index` parameter."""
    scalars_df, scalars_pandas_df = scalars_dfs
    index_col = None
    if scalars_df.index.name is not None:
        destination_table = f"{dataset_id}.test_index_df_to_gbq_{index}"
        if index:
            index_col = scalars_df.index.name
    else:
        destination_table = f"{dataset_id}.test_default_index_df_to_gbq_{index}"

    scalars_df.to_gbq(destination_table, if_exists="replace", index=index)
    gcs_df = pd.read_gbq(destination_table, index_col=index_col)
    convert_pandas_dtypes(gcs_df, bytes_col=False)
    assert_pandas_df_equal_ignore_ordering(gcs_df, scalars_pandas_df)


@pytest.mark.parametrize(
    ("if_exists", "expected_index"),
    [
        pytest.param("replace", 1),
        pytest.param("append", 2),
        pytest.param(
            "fail",
            0,
            marks=pytest.mark.xfail(
                raises=google.api_core.exceptions.Conflict,
            ),
        ),
        pytest.param(
            "unknown",
            0,
            marks=pytest.mark.xfail(
                raises=ValueError,
            ),
        ),
    ],
)
@pytest.mark.skipif(pandas_gbq is None, reason="required by pd.read_gbq")
def test_to_gbq_if_exists(
    scalars_df_default_index,
    scalars_pandas_df_default_index,
    dataset_id,
    if_exists,
    expected_index,
):
    """Test the `to_gbq` API with the `if_exists` parameter."""
    destination_table = f"{dataset_id}.test_to_gbq_if_exists_{if_exists}"

    scalars_df_default_index.to_gbq(destination_table)
    scalars_df_default_index.to_gbq(destination_table, if_exists=if_exists)

    gcs_df = pd.read_gbq(destination_table)
    assert len(gcs_df.index) == expected_index * len(
        scalars_pandas_df_default_index.index
    )
    pd.testing.assert_index_equal(
        gcs_df.columns, scalars_pandas_df_default_index.columns
    )


def test_to_gbq_w_invalid_destination_table(scalars_df_index):
    with pytest.raises(ValueError):
        scalars_df_index.to_gbq("table_id")


@pytest.mark.parametrize(
    ("index"),
    [True, False],
)
def test_to_parquet_index(scalars_dfs, gcs_folder, index):
    """Test the `to_parquet` API with the `index` parameter."""
    scalars_df, scalars_pandas_df = scalars_dfs
    if scalars_df.index.name is not None:
        path = gcs_folder + f"test_index_df_to_parquet_{index}"
    else:
        path = gcs_folder + f"test_default_index_df_to_parquet_{index}"

    # TODO(b/268693993): Type GEOGRAPHY is not currently supported for parquet.
    scalars_df = scalars_df.drop(columns="geography_col")
    scalars_pandas_df = scalars_pandas_df.drop(columns="geography_col")

    # TODO(swast): Do a bit more processing on the input DataFrame to ensure
    # the exported results are from the generated query, not just the source
    # table.
    scalars_df.to_parquet(path, index=index)

    gcs_df = pd.read_parquet(path)
    convert_pandas_dtypes(gcs_df, bytes_col=False)
    if index and scalars_df.index.name is not None:
        gcs_df = gcs_df.set_index(scalars_df.index.name)

    assert len(gcs_df.index) == len(scalars_pandas_df.index)
    pd.testing.assert_index_equal(gcs_df.columns, scalars_pandas_df.columns)
    assert_pandas_df_equal_ignore_ordering(gcs_df, scalars_pandas_df)
