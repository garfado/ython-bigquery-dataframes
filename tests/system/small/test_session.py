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
from typing import List, Tuple, Union

import google.api_core.exceptions
import google.cloud.bigquery as bigquery
import numpy as np
import pandas as pd
import pyarrow as pa  # type: ignore
import pytest

import bigframes
import bigframes.core.indexes.index
import bigframes.dataframe
import bigframes.dtypes
import bigframes.ml.linear_model
from tests.system.utils import assert_pandas_df_equal_ignore_ordering


def test_read_gbq(
    session: bigframes.Session,
    scalars_table_id: str,
    scalars_schema: List[bigquery.SchemaField],
    scalars_pandas_df_default_index: pd.DataFrame,
):
    df = session.read_gbq(scalars_table_id)
    assert len(df.columns) == len(scalars_schema)

    bf_result = df.compute()
    pd_result = scalars_pandas_df_default_index
    assert bf_result.shape[0] == pd_result.shape[0]

    assert_pandas_df_equal_ignore_ordering(bf_result, pd_result)


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

    pd.testing.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    ("query_or_table", "col_order"),
    [
        pytest.param(
            "{scalars_table_id}", ["bool_col", "int64_col"], id="two_cols_in_table"
        ),
        pytest.param(
            """SELECT
                t.float64_col * 2 AS my_floats,
                CONCAT(t.string_col, "_2") AS my_strings,
                t.int64_col > 0 AS my_bools,
            FROM `{scalars_table_id}` AS t
            """,
            ["my_strings"],
            id="one_cols_in_query",
        ),
        pytest.param(
            "{scalars_table_id}",
            ["unknown"],
            marks=pytest.mark.xfail(
                raises=ValueError,
                reason="Column `unknown` not found in this table.",
            ),
            id="unknown_col",
        ),
    ],
)
def test_read_gbq_w_col_order(
    session: bigframes.Session,
    scalars_table_id: str,
    query_or_table: str,
    col_order: List[str],
):
    df = session.read_gbq(
        query_or_table.format(scalars_table_id=scalars_table_id), col_order=col_order
    )
    assert df.columns.tolist() == col_order


@pytest.mark.parametrize(
    ("query_or_table", "max_results"),
    [
        pytest.param("{scalars_table_id}", 2, id="two_rows_in_table"),
        pytest.param(
            """SELECT
                t.float64_col * 2 AS my_floats,
                CONCAT(t.string_col, "_2") AS my_strings,
                t.int64_col > 0 AS my_bools,
            FROM `{scalars_table_id}` AS t
            """,
            2,
            id="three_rows_in_query",
        ),
        pytest.param(
            "{scalars_table_id}",
            -1,
            marks=pytest.mark.xfail(
                raises=ValueError,
                reason="`max_results` should be a positive number.",
            ),
            id="neg_rows",
        ),
    ],
)
def test_read_gbq_w_max_results(
    session: bigframes.Session,
    scalars_table_id: str,
    query_or_table: str,
    max_results: int,
):
    df = session.read_gbq(
        query_or_table.format(scalars_table_id=scalars_table_id),
        max_results=max_results,
    )
    bf_result = df.compute()
    assert bf_result.shape[0] == max_results


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


def test_read_gbq_model(session, penguins_linear_model_name):
    model = session.read_gbq_model(penguins_linear_model_name)
    assert isinstance(model, bigframes.ml.linear_model.LinearRegression)


def test_read_pandas(session, scalars_dfs):
    _, scalars_pandas_df = scalars_dfs

    df = session.read_pandas(scalars_pandas_df)
    assert df._block._expr._ordering is not None

    result = df.compute()
    expected = scalars_pandas_df

    # TODO(chelsealin): Datetime types is detected as Timestamp type through BQ load job.
    result["datetime_col"] = result["datetime_col"].astype("timestamp[us][pyarrow]")

    pd.testing.assert_frame_equal(result, expected)


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

    # TODO(chelsealin): Datetime types is detected as Timestamp type through BQ load job.
    result["datetime_col"] = result["datetime_col"].astype(
        pd.ArrowDtype(pa.timestamp("us"))
    )

    pd.testing.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "sep",
    [
        pytest.param(None, id="without_sep"),
        pytest.param(",", id="with_sep"),
    ],
)
def test_read_csv_gcs_default_engine(session, scalars_dfs, gcs_folder, sep):
    scalars_df, _ = scalars_dfs
    if scalars_df.index.name is not None:
        path = gcs_folder + "test_read_csv_gcs_default_engine_w_index"
    else:
        path = gcs_folder + "test_read_csv_gcs_default_engine_wo_index"
    path = path + "_w_sep.csv" if sep is not None else path + "_wo_sep.csv"

    scalars_df.to_csv(path, index=False)
    dtype = scalars_df.dtypes.to_dict()
    dtype.pop("geography_col")
    df = session.read_csv(
        path,
        sep=sep,
        # Convert default pandas dtypes to match BigFrames dtypes.
        dtype=dtype,
    )
    assert df._block._expr._ordering is not None

    # TODO(chelsealin): If we serialize the index, can more easily compare values.
    pd.testing.assert_index_equal(df.columns, scalars_df.columns)

    # The auto detects of BigQuery load job have restrictions to detect the bytes,
    # numeric and geometry types, so they're skipped here.
    df = df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
    scalars_df = scalars_df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
    assert df.shape[0] == scalars_df.shape[0]
    pd.testing.assert_series_equal(df.dtypes, scalars_df.dtypes)


def test_read_csv_gcs_bq_engine(session, scalars_dfs, gcs_folder):
    scalars_df, _ = scalars_dfs
    if scalars_df.index.name is not None:
        path = gcs_folder + "test_read_csv_gcs_bq_engine_w_index.csv"
    else:
        path = gcs_folder + "test_read_csv_gcs_bq_engine_wo_index.csv"
    scalars_df.to_csv(path, index=False)
    df = session.read_csv(path, engine="bigquery")

    # TODO(chelsealin): If we serialize the index, can more easily compare values.
    pd.testing.assert_index_equal(df.columns, scalars_df.columns)

    # The auto detects of BigQuery load job have restrictions to detect the bytes,
    # numeric and geometry types, so they're skipped here.
    df = df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
    scalars_df = scalars_df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
    assert df.shape[0] == scalars_df.shape[0]
    pd.testing.assert_series_equal(df.dtypes, scalars_df.dtypes)


@pytest.mark.parametrize(
    "sep",
    [
        pytest.param(None, id="without_sep"),
        pytest.param(",", id="with_sep"),
    ],
)
def test_read_csv_local_default_engine(session, scalars_dfs, sep):
    scalars_df, scalars_pandas_df = scalars_dfs
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_default_engine.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df.to_csv(path, index=False)
        dtype = scalars_df.dtypes.to_dict()
        dtype.pop("geography_col")
        df = session.read_csv(
            path,
            sep=sep,
            # Convert default pandas dtypes to match BigFrames dtypes.
            dtype=dtype,
        )
        assert df._block._expr._ordering is not None

        # TODO(chelsealin): If we serialize the index, can more easily compare values.
        pd.testing.assert_index_equal(df.columns, scalars_df.columns)

        # The auto detects of BigQuery load job have restrictions to detect the bytes,
        # numeric and geometry types, so they're skipped here.
        df = df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
        scalars_df = scalars_df.drop(
            columns=["bytes_col", "numeric_col", "geography_col"]
        )
        assert df.shape[0] == scalars_df.shape[0]
        pd.testing.assert_series_equal(df.dtypes, scalars_df.dtypes)


def test_read_csv_local_bq_engine(session, scalars_dfs):
    scalars_df, scalars_pandas_df = scalars_dfs
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_bq_engine.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df.to_csv(path, index=False)
        df = session.read_csv(path, engine="bigquery")

        # TODO(chelsealin): If we serialize the index, can more easily compare values.
        pd.testing.assert_index_equal(df.columns, scalars_df.columns)

        # The auto detects of BigQuery load job have restrictions to detect the bytes,
        # numeric and geometry types, so they're skipped here.
        df = df.drop(columns=["bytes_col", "numeric_col", "geography_col"])
        scalars_df = scalars_df.drop(
            columns=["bytes_col", "numeric_col", "geography_col"]
        )
        assert df.shape[0] == scalars_df.shape[0]
        pd.testing.assert_series_equal(df.dtypes, scalars_df.dtypes)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        pytest.param(
            {"engine": "bigquery", "sep": ","},
            "BigQuery engine does not support these arguments",
            id="with_sep",
        ),
        pytest.param(
            {"engine": "bigquery", "names": []},
            "BigQuery engine does not support these arguments",
            id="with_names",
        ),
        pytest.param(
            {"engine": "bigquery", "dtype": {}},
            "BigQuery engine does not support these arguments",
            id="with_dtype",
        ),
        pytest.param(
            {"engine": "bigquery", "index_col": False},
            "BigQuery engine only supports a single column name for `index_col`.",
            id="with_index_col_false",
        ),
        pytest.param(
            {"engine": "bigquery", "index_col": 5},
            "BigQuery engine only supports a single column name for `index_col`.",
            id="with_index_col_not_str",
        ),
        pytest.param(
            {"engine": "bigquery", "usecols": [1, 2]},
            "BigQuery engine only supports an iterable of strings for `usecols`.",
            id="with_usecols_invalid",
        ),
    ],
)
def test_read_csv_bq_engine_throws_not_implemented_error(session, kwargs, match):
    with pytest.raises(NotImplementedError, match=match):
        session.read_csv("", **kwargs)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        pytest.param(
            {"index_col": [0, 1]},
            "MultiIndex not supported.",
            id="with_multiindex",
        ),
        pytest.param(
            {"chunksize": 5},
            "'chunksize' and 'iterator' arguments are not supported.",
            id="with_chunksize",
        ),
        pytest.param(
            {"iterator": True},
            "'chunksize' and 'iterator' arguments are not supported.",
            id="with_iterator",
        ),
    ],
)
def test_read_csv_default_engine_throws_not_implemented_error(
    session,
    scalars_df_index,
    gcs_folder,
    kwargs,
    match,
):
    path = (
        gcs_folder + "test_read_csv_gcs_default_engine_throws_not_implemented_error.csv"
    )
    scalars_df_index.to_csv(path)
    with pytest.raises(NotImplementedError, match=match):
        session.read_csv(path, **kwargs)


def test_read_csv_bq_engine_w_buffer_throws_not_implemented_error(session):
    buffer = StringIO("name,age,gender\nJohn,25,Male\nJane,30,Female\nMark,40,Male")
    with pytest.raises(
        NotImplementedError, match="BigQuery engine does not support buffers."
    ):
        session.read_csv(buffer, engine="bigquery")


def test_read_csv_gcs_default_engine_w_header(session, scalars_df_index, gcs_folder):
    path = gcs_folder + "test_read_csv_gcs_default_engine_w_header.csv"
    scalars_df_index.to_csv(path)

    # Skips header=N rows, normally considers the N+1th row as the header, but overridden by
    # passing the `names` argument. In this case, pandas will skip the N+1th row too, take
    # the column names from `names`, and begin reading data from the N+2th row.
    df = session.read_csv(
        path,
        header=2,
        names=scalars_df_index.columns.to_list(),
    )
    assert df.shape[0] == scalars_df_index.shape[0] - 2
    assert len(df.columns) == len(scalars_df_index.columns)


def test_read_csv_gcs_bq_engine_w_header(session, scalars_df_index, gcs_folder):
    path = gcs_folder + "test_read_csv_gcs_bq_engine_w_header.csv"
    scalars_df_index.to_csv(path, index=False)

    # Skip the header and the first 2 data rows. Without provided schema, the column names
    # would be like `bool_field_0`, `string_field_1` and etc.
    df = session.read_csv(path, header=2, engine="bigquery")
    assert df.shape[0] == scalars_df_index.shape[0] - 2
    assert len(df.columns) == len(scalars_df_index.columns)


def test_read_csv_local_default_engine_w_header(session, scalars_pandas_df_index):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_default_engine_w_header.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df_index.to_csv(path, index=False)

        # Skips header=N rows. Normally row N+1 would be the header now, but overridden by
        # passing the `names` argument. In this case, pandas will skip row N+1 too, infer
        # the column names from `names`, and begin reading data from row N+2.
        df = session.read_csv(
            path,
            header=2,
            names=scalars_pandas_df_index.columns.to_list(),
        )
        assert df.shape[0] == scalars_pandas_df_index.shape[0] - 2
        assert len(df.columns) == len(scalars_pandas_df_index.columns)


def test_read_csv_local_bq_engine_w_header(session, scalars_pandas_df_index):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_bq_engine_w_header.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df_index.to_csv(path, index=False)

        # Skip the header and the first 2 data rows. Without provided schema, the column names
        # would be like `bool_field_0`, `string_field_1` and etc.
        df = session.read_csv(path, header=2, engine="bigquery")
        assert df.shape[0] == scalars_pandas_df_index.shape[0] - 2
        assert len(df.columns) == len(scalars_pandas_df_index.columns)


def test_read_csv_gcs_default_engine_w_index_col_name(
    session, scalars_df_default_index, gcs_folder
):
    path = gcs_folder + "test_read_csv_gcs_default_engine_w_index_col_name.csv"
    scalars_df_default_index.to_csv(path)

    df = session.read_csv(path, index_col="rowindex")
    scalars_df_default_index = scalars_df_default_index.set_index(
        "rowindex"
    ).sort_index()
    pd.testing.assert_index_equal(df.columns, scalars_df_default_index.columns)
    assert df.index.name == "rowindex"


def test_read_csv_gcs_default_engine_w_index_col_index(
    session, scalars_df_default_index, gcs_folder
):
    path = gcs_folder + "test_read_csv_gcs_default_engine_w_index_col_index.csv"
    scalars_df_default_index.to_csv(path)

    index_col = scalars_df_default_index.columns.to_list().index("rowindex")
    df = session.read_csv(path, index_col=index_col)
    scalars_df_default_index = scalars_df_default_index.set_index(
        "rowindex"
    ).sort_index()
    pd.testing.assert_index_equal(df.columns, scalars_df_default_index.columns)
    assert df.index.name == "rowindex"


def test_read_csv_local_default_engine_w_index_col_name(
    session, scalars_pandas_df_default_index
):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_default_engine_w_index_col_name"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df_default_index.to_csv(path, index=False)

        df = session.read_csv(path, index_col="rowindex")
        scalars_pandas_df_default_index = scalars_pandas_df_default_index.set_index(
            "rowindex"
        ).sort_index()
        pd.testing.assert_index_equal(
            df.columns, scalars_pandas_df_default_index.columns
        )
        assert df.index.name == "rowindex"


def test_read_csv_local_default_engine_w_index_col_index(
    session, scalars_pandas_df_default_index
):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_default_engine_w_index_col_index"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df_default_index.to_csv(path, index=False)

        index_col = scalars_pandas_df_default_index.columns.to_list().index("rowindex")
        df = session.read_csv(path, index_col=index_col)
        scalars_pandas_df_default_index = scalars_pandas_df_default_index.set_index(
            "rowindex"
        ).sort_index()
        pd.testing.assert_index_equal(
            df.columns, scalars_pandas_df_default_index.columns
        )
        assert df.index.name == "rowindex"


@pytest.mark.parametrize(
    "engine",
    [
        pytest.param("bigquery", id="bq_engine"),
        pytest.param(None, id="default_engine"),
    ],
)
def test_read_csv_gcs_w_usecols(session, scalars_df_index, gcs_folder, engine):
    path = gcs_folder + "test_read_csv_gcs_w_usecols"
    path = path + "_default_engine.csv" if engine is None else path + "_bq_engine.csv"
    scalars_df_index.to_csv(path)

    # df should only have 1 column which is bool_col.
    df = session.read_csv(path, usecols=["bool_col"], engine=engine)
    assert len(df.columns) == 1


@pytest.mark.parametrize(
    "engine",
    [
        pytest.param("bigquery", id="bq_engine"),
        pytest.param(None, id="default_engine"),
    ],
)
def test_read_csv_local_w_usecols(session, scalars_pandas_df_index, engine):
    with tempfile.TemporaryDirectory() as dir:
        path = dir + "/test_read_csv_local_w_usecols.csv"
        # Using the pandas to_csv method because the BQ one does not support local write.
        scalars_pandas_df_index.to_csv(path, index=False)

        # df should only have 1 column which is bool_col.
        df = session.read_csv(path, usecols=["bool_col"], engine=engine)
        assert len(df.columns) == 1


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
