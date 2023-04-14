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
from io import StringIO
import tempfile
from typing import Tuple, Union

import db_dtypes  # type: ignore
import google.api_core.exceptions
import numpy as np
import pandas as pd
import pytest

import bigframes
import bigframes.core.indexes.index
import bigframes.dataframe
import bigframes.dtypes
import bigframes.ml.linear_model


def test_read_gbq(session: bigframes.Session, scalars_table_id, scalars_schema):
    df = session.read_gbq(scalars_table_id)
    # TODO(swast): Test against public properties like columns or dtypes. Also,
    # check the names and data types match up.
    assert len(df.columns) == len(scalars_schema)


def test_read_gbq_tokyo(
    session_tokyo: bigframes.Session,
    scalars_table_tokyo: str,
    scalars_pandas_df_index: pd.DataFrame,
    tokyo_location: str,
):
    df = session_tokyo.read_gbq(scalars_table_tokyo, index_cols=["rowindex"])
    result = df.sort_index().compute()
    expected = scalars_pandas_df_index

    query_job = df._block.expr.start_query()
    assert query_job.location == tokyo_location

    # TODO(chelsealin): Check the dtypes after supporting all dtypes.
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_column_type=False,
        check_dtype=False,
        check_index_type=False,
    )


def test_read_gbq_w_col_order(session, scalars_table_id, scalars_schema):
    columns = list(column.name for column in scalars_schema)
    df = session.read_gbq(scalars_table_id, col_order=columns)
    assert len(df.columns) == len(scalars_schema)

    df = session.read_gbq(scalars_table_id, col_order=[columns[0]])
    assert len(df.columns) == 1

    with pytest.raises(ValueError):
        df = session.read_gbq(scalars_table_id, col_order=["unknown"])


def test_read_gbq_sql(
    session, scalars_dfs: Tuple[bigframes.dataframe.DataFrame, pd.DataFrame]
):
    scalars_df, scalars_pandas_df = scalars_dfs
    df_len = len(scalars_pandas_df.index)

    index_cols: Union[Tuple[str], Tuple] = ()
    if scalars_df.index.name == "rowindex":
        sql = """SELECT
                t.rowindex AS rowindex,
                t.float64_col * 2 AS my_floats,
                CONCAT(t.string_col, "_2") AS my_strings,
                t.int64_col > 0 AS my_bools
            FROM ({subquery}) AS t
            ORDER BY t.rowindex""".format(
            subquery=scalars_df.sql
        )
        index_cols = ("rowindex",)
    else:
        sql = """SELECT
                t.float64_col * 2 AS my_floats,
                CONCAT(t.string_col, "_2") AS my_strings,
                t.int64_col > 0 AS my_bools
            FROM ({subquery}) AS t
            ORDER BY t.rowindex""".format(
            subquery=scalars_df.sql
        )
        index_cols = ()

    df = session.read_gbq(sql, index_cols=index_cols)
    result = df.compute()

    expected = pd.concat(
        [
            pd.Series(scalars_pandas_df["float64_col"] * 2, name="my_floats"),
            pd.Series(
                scalars_pandas_df["string_col"].str.cat(["_2"] * df_len),
                name="my_strings",
            ),
            pd.Series(scalars_pandas_df["int64_col"] > 0, name="my_bools"),
        ],
        axis=1,
    )

    # TODO(swast): Restore ordering for SQL inputs.
    if result.index.name is None:
        result = result.sort_values(["my_floats", "my_strings"]).reset_index(drop=True)
        expected = expected.sort_values(["my_floats", "my_strings"]).reset_index(
            drop=True
        )

    pd.testing.assert_frame_equal(result, expected)


def test_read_gbq_sql_w_col_order(session):
    sql = """SELECT 1 AS my_int_col, "hi" AS my_string_col, 0.2 AS my_float_col"""
    df = session.read_gbq(sql, col_order=["my_float_col", "my_string_col"])
    result = df.compute()
    expected: pd.DataFrame = pd.DataFrame(
        {
            "my_float_col": pd.Series([0.2], dtype=pd.Float64Dtype()),
            "my_string_col": pd.Series(["hi"], dtype=pd.StringDtype(storage="pyarrow")),
        },
        index=pd.Index([0], dtype=pd.Int64Dtype()),
    )
    pd.testing.assert_frame_equal(result, expected)


def test_read_gbq_model(session, penguins_linear_model_name):
    model = session.read_gbq_model(penguins_linear_model_name)
    assert isinstance(model, bigframes.ml.linear_model.LinearRegression)


def test_read_pandas(session, scalars_dfs):
    _, scalars_pandas_df = scalars_dfs

    df = session.read_pandas(scalars_pandas_df)
    assert df._block._expr._ordering is not None

    result = df.compute()
    expected = scalars_pandas_df

    # TODO(chelsealin): Check the dtypes after supporting all dtypes.
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_column_type=False,
        check_dtype=False,
        check_index_type=False,
    )


def test_read_pandas_multi_index_throws_error(session, scalars_pandas_df_multi_index):
    with pytest.raises(NotImplementedError, match="MultiIndex not supported."):
        session.read_pandas(scalars_pandas_df_multi_index)


def test_read_pandas_rowid_exists_adds_suffix(session, scalars_pandas_df_default_index):
    scalars_pandas_df_default_index["rowid"] = np.arange(
        scalars_pandas_df_default_index.shape[0]
    )

    df = session.read_pandas(scalars_pandas_df_default_index)
    assert df._block._expr._ordering.ordering_id == "rowid_2"


def test_read_pandas_tokyo(
    session_tokyo: bigframes.Session,
    scalars_pandas_df_index: pd.DataFrame,
    tokyo_location: str,
):
    df = session_tokyo.read_pandas(scalars_pandas_df_index)
    result = df.compute()
    expected = scalars_pandas_df_index

    query_job = df._block.expr.start_query()
    assert query_job.location == tokyo_location

    # TODO(chelsealin): Check the dtypes after supporting all dtypes.
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_column_type=False,
        check_dtype=False,
        check_index_type=False,
    )


def test_read_csv_gcs_default_engine(session, scalars_dfs, gcs_folder):
    scalars_df, _ = scalars_dfs
    if scalars_df.index.name is not None:
        path = gcs_folder + "test_read_csv_gcs_default_engine_w_index.csv"
    else:
        path = gcs_folder + "test_read_csv_gcs_default_engine_wo_index.csv"
    scalars_df.to_csv(path)
    gcs_df = session.read_csv(
        path,
        dtype={
            "bool_col": pd.BooleanDtype(),
            # TODO(swast): Needs microsecond precision support:
            # https://github.com/googleapis/python-db-dtypes-pandas/issues/47
            "date_col": db_dtypes.DateDtype(),
            "int64_col": pd.Int64Dtype(),
            "int64_too": pd.Int64Dtype(),
            "float64_col": pd.Float64Dtype(),
            "rowindex": pd.Int64Dtype(),
            "string_col": pd.StringDtype(storage="pyarrow"),
            # TODO(swast): Needs microsecond precision support:
            # https://github.com/googleapis/python-db-dtypes-pandas/issues/47
            "time_col": db_dtypes.TimeDtype(),
        },
    )

    # TODO(chelsealin): If we serialize the index, can more easily compare values.
    pd.testing.assert_index_equal(gcs_df.columns, scalars_df.columns)

    # In the read_csv() API, read_pandas auto detects the `byte_col` & `geography_col`
    # as the string type, the `numeric_col` as the Float64 type, and does not detect
    # the correct types for `datetime_col` & `timestamp_col`
    gcs_df = gcs_df.drop(
        ["bytes_col", "numeric_col", "geography_col", "datetime_col", "timestamp_col"]
    )
    scalars_df = scalars_df.drop(
        ["bytes_col", "numeric_col", "geography_col", "datetime_col", "timestamp_col"]
    )
    assert gcs_df.shape[0] == scalars_df.shape[0]
    pd.testing.assert_series_equal(gcs_df.dtypes, scalars_df.dtypes)


def test_read_csv_gcs_bq_engine(session, scalars_dfs, gcs_folder):
    scalars_df, _ = scalars_dfs
    if scalars_df.index.name is not None:
        path = gcs_folder + "test_read_csv_gcs_bq_engine_w_index.csv"
    else:
        path = gcs_folder + "test_read_csv_gcs_bq_engine_wo_index.csv"
    scalars_df.to_csv(path)
    gcs_df = session.read_csv(path, engine="bigquery")

    # TODO(chelsealin): If we serialize the index, can more easily compare values.
    pd.testing.assert_index_equal(gcs_df.columns, scalars_df.columns)

    # The auto detects of BigQuery load job have restrictions to detect the bytes,
    # numeric and geometry types, so they're skipped here.
    gcs_df = gcs_df.drop(["bytes_col", "numeric_col", "geography_col"])
    scalars_df = scalars_df.drop(["bytes_col", "numeric_col", "geography_col"])
    assert gcs_df.shape[0] == scalars_df.shape[0]
    pd.testing.assert_series_equal(gcs_df.dtypes, scalars_df.dtypes)


def test_read_csv_local_default_engine(session, scalars_dfs):
    scalars_df, scalars_pandas_df = scalars_dfs
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_default_engine.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df.to_csv(path, index=False)
        local_df = session.read_csv(
            path,
            dtype={
                "bool_col": pd.BooleanDtype(),
                # TODO(swast): Needs microsecond precision support:
                # https://github.com/googleapis/python-db-dtypes-pandas/issues/47
                "date_col": db_dtypes.DateDtype(),
                "int64_col": pd.Int64Dtype(),
                "int64_too": pd.Int64Dtype(),
                "float64_col": pd.Float64Dtype(),
                "rowindex": pd.Int64Dtype(),
                "string_col": pd.StringDtype(storage="pyarrow"),
                # TODO(swast): Needs microsecond precision support:
                # https://github.com/googleapis/python-db-dtypes-pandas/issues/47
                "time_col": db_dtypes.TimeDtype(),
            },
        )

        # TODO(chelsealin): If we serialize the index, can more easily compare values.
        pd.testing.assert_index_equal(local_df.columns, scalars_df.columns)

        # In the read_csv() API, read_pandas auto detects the `byte_col` & `geography_col`
        # as the string type, the `numeric_col` as the Float64 type, and does not detect
        # the correct types for `datetime_col` & `timestamp_col`
        local_df = local_df.drop(
            [
                "bytes_col",
                "numeric_col",
                "geography_col",
                "datetime_col",
                "timestamp_col",
            ]
        )
        scalars_df = scalars_df.drop(
            [
                "bytes_col",
                "numeric_col",
                "geography_col",
                "datetime_col",
                "timestamp_col",
            ]
        )
        assert local_df.shape[0] == scalars_df.shape[0]
        pd.testing.assert_series_equal(local_df.dtypes, scalars_df.dtypes)


def test_read_csv_local_bq_engine(session, scalars_dfs):
    scalars_df, scalars_pandas_df = scalars_dfs
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_bq_engine.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df.to_csv(path, index=False)
        local_df = session.read_csv(path, engine="bigquery")

        # TODO(chelsealin): If we serialize the index, can more easily compare values.
        pd.testing.assert_index_equal(local_df.columns, scalars_df.columns)

        # The auto detects of BigQuery load job have restrictions to detect the bytes,
        # numeric and geometry types, so they're skipped here.
        local_df = local_df.drop(["bytes_col", "numeric_col", "geography_col"])
        scalars_df = scalars_df.drop(["bytes_col", "numeric_col", "geography_col"])
        assert local_df.shape[0] == scalars_df.shape[0]
        pd.testing.assert_series_equal(local_df.dtypes, scalars_df.dtypes)


def test_read_csv_bq_engine_w_arguments_throws_not_implemented_error(session):
    with pytest.raises(
        NotImplementedError, match="BigQuery engine does not support these arguments"
    ):
        session.read_csv("", engine="bigquery", names=["1", "2"], dtype={})


def test_read_csv_bq_engine_w_buffer_throws_not_implemented_error(session):
    buffer = StringIO("name,age,gender\nJohn,25,Male\nJane,30,Female\nMark,40,Male")
    with pytest.raises(
        NotImplementedError, match="BigQuery engine does not support buffers."
    ):
        session.read_csv(buffer, engine="bigquery")


def test_read_csv_gcs_w_header_default_engine(session, scalars_df_index, gcs_folder):
    path = gcs_folder + "test_read_csv_gcs_w_header_default_engine.csv"
    scalars_df_index.to_csv(path)

    # Skips header=N rows, normally considers the N+1th row as the header, but overridden by
    # passing the `names` argument. In this case, pandas will skip the N+1th row too, take
    # the column names from `names`, and begin reading data from the N+2th row.
    gcs_df = session.read_csv(
        path,
        header=2,
        names=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
    )
    assert gcs_df.shape[0] == scalars_df_index.shape[0] - 2
    assert len(gcs_df.columns) == len(scalars_df_index.columns)


def test_read_csv_gcs_w_header_bq_engine(session, scalars_df_index, gcs_folder):
    path = gcs_folder + "test_read_csv_gcs_w_header_bq_engine.csv"
    scalars_df_index.to_csv(path)

    # Skip the header and the first 2 data rows. Without provided schema, the column names
    # would be like `bool_field_0`, `string_field_1` and etc.
    gcs_df = session.read_csv(path, header=2, engine="bigquery")
    assert gcs_df.shape[0] == scalars_df_index.shape[0] - 2
    assert len(gcs_df.columns) == len(scalars_df_index.columns)


def test_read_csv_local_w_header_default_engine(session, scalars_pandas_df_index):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_w_header_default_engine.csv"
        scalars_pandas_df_index.to_csv(path, index=False)

        # Skips header=N rows. Normally row N+1 would be the header now, but overridden by
        # passing the `names` argument. In this case, pandas will skip row N+1 too, infer
        # the column names from `names`, and begin reading data from row N+2.
        local_df = session.read_csv(
            path,
            header=2,
            names=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
        )
        assert local_df.shape[0] == scalars_pandas_df_index.shape[0] - 2
        assert len(local_df.columns) == len(scalars_pandas_df_index.columns)


def test_read_csv_local_w_header_bq_engine(session, scalars_pandas_df_index):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_w_header_bq_engine.csv"
        scalars_pandas_df_index.to_csv(path, index=False)

        # Skip the header and the first 2 data rows. Without provided schema, the column names
        # would be like `bool_field_0`, `string_field_1` and etc.
        local_df = session.read_csv(path, header=2, engine="bigquery")
        assert local_df.shape[0] == scalars_pandas_df_index.shape[0] - 2
        assert len(local_df.columns) == len(scalars_pandas_df_index.columns)


def test_session_id(session):
    assert session._session_id is not None

    # BQ client always runs query within the opened session.
    query_job = session.bqclient.query("SELECT 1")
    assert query_job.session_info.session_id == session._session_id

    # TODO(chelsealin): Verify the session id can be binded with a load job.


def test_session_dataset_exists_and_configured(session: bigframes.Session):
    dataset = session.bqclient.get_dataset(session._session_dataset_id)
    assert dataset.default_table_expiration_ms == 24 * 60 * 60 * 1000


@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_to_close_session():
    session = bigframes.Session()
    assert session._session_id is not None
    session.close()
    assert session._session_id is None

    # Session has expired and is no longer available.
    with pytest.raises(google.api_core.exceptions.BadRequest):
        query_job = session.bqclient.query("SELECT 1")
        query_job.result()  # blocks until finished
