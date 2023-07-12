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

"""BigQuery DataFrame provides a DataFrame API backed by the BigQuery engine."""

from __future__ import annotations

import inspect
import threading
from typing import (
    Any,
    Callable,
    Dict,
    IO,
    Iterable,
    List,
    Literal,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from google.cloud import bigquery
import numpy
import pandas

import bigframes._config as config
import bigframes.bigframes
import bigframes.core.indexes
import bigframes.dataframe
import bigframes.series
import bigframes.session

concat = bigframes.bigframes.concat
options = config.options

_global_session: Optional[bigframes.session.Session] = None
_global_session_lock = threading.Lock()


def reset_session() -> None:
    """Start a fresh session next time a function requires a session.

    Closes the current session if it was already started.
    """
    global _global_session

    with _global_session_lock:
        if _global_session is not None:
            _global_session.close()
            _global_session = None

        options.bigquery._session_started = False


def get_global_session():
    """Gets the global session.

    Creates the global session if it does not exist.
    """
    global _global_session, _global_session_lock

    with _global_session_lock:
        if _global_session is None:
            _global_session = bigframes.session.connect(options.bigquery)

    return _global_session


_T = TypeVar("_T")


def _with_default_session(func: Callable[..., _T], *args, **kwargs) -> _T:
    return func(get_global_session(), *args, **kwargs)


def _set_default_session_location_if_possible(query):
    # If the default session has not started yet and this is the first API user
    # is calling, then set the default location as per the query.
    # If query is a table name, then it would be the location of the table.
    # If query is a SQL with a table, then it would be table's location.
    # If query is a SQL with no table, then it would be the BQ default location.
    if options.bigquery._session_started or options.bigquery.use_regional_endpoints:
        return

    bqclient, _, _ = bigframes.session._create_bq_clients(
        project=options.bigquery.project,
        location=options.bigquery.location,
        use_regional_endpoints=options.bigquery.use_regional_endpoints,
        credentials=options.bigquery.credentials,
    )

    if bigframes.session._is_query(query):
        job = bqclient.query(query, bigquery.QueryJobConfig(dry_run=True))
        options.bigquery.location = job.location
    else:
        table = bqclient.get_table(query)
        options.bigquery.location = table.location


# Note: the following methods are duplicated from Session. This duplication
# enables the following:
#
# 1. Static type checking knows the argument and return types, which is
#    difficult to do with decorators. Aside: When we require Python 3.10, we
#    can use Concatenate for generic typing in decorators. See:
#    https://stackoverflow.com/a/68290080/101923
# 2. docstrings get processed by static processing tools, such as VS Code's
#    autocomplete.
# 3. Positional arguments function as expected. If we were to pull in the
#    methods directly from Session, a Session object would need to be the first
#    argument, even if we allow a default value.
# 4. Allows to set BigQuery options for the BigFrames session based on the
#    method and its arguments.


def read_csv(
    filepath_or_buffer: str | IO["bytes"],
    *,
    sep: Optional[str] = ",",
    header: Optional[int] = 0,
    names: Optional[
        Union[MutableSequence[Any], numpy.ndarray[Any, Any], Tuple[Any, ...], range]
    ] = None,
    index_col: Optional[
        Union[int, str, Sequence[Union[str, int]], Literal[False]]
    ] = None,
    usecols: Optional[
        Union[
            MutableSequence[str],
            Tuple[str, ...],
            Sequence[int],
            pandas.Series,
            pandas.Index,
            numpy.ndarray[Any, Any],
            Callable[[Any], bool],
        ]
    ] = None,
    dtype: Optional[Dict] = None,
    engine: Optional[
        Literal["c", "python", "pyarrow", "python-fwf", "bigquery"]
    ] = None,
    encoding: Optional[str] = None,
    **kwargs,
) -> bigframes.dataframe.DataFrame:
    return _with_default_session(
        bigframes.session.Session.read_csv,
        filepath_or_buffer=filepath_or_buffer,
        sep=sep,
        header=header,
        names=names,
        index_col=index_col,
        usecols=usecols,
        dtype=dtype,
        engine=engine,
        encoding=encoding,
        **kwargs,
    )


read_csv.__doc__ = inspect.getdoc(bigframes.session.Session.read_csv)


def read_gbq(
    query: str,
    *,
    index_col: Iterable[str] | str = (),
    col_order: Iterable[str] = (),
    max_results: Optional[int] = None,
) -> bigframes.dataframe.DataFrame:
    _set_default_session_location_if_possible(query)
    return _with_default_session(
        bigframes.session.Session.read_gbq,
        query,
        index_col=index_col,
        col_order=col_order,
        max_results=max_results,
    )


read_gbq.__doc__ = inspect.getdoc(bigframes.session.Session.read_gbq)


def read_gbq_model(model_name: str):
    return _with_default_session(
        bigframes.session.Session.read_gbq_model,
        model_name,
    )


read_gbq_model.__doc__ = inspect.getdoc(bigframes.session.Session.read_gbq_model)


def read_gbq_query(
    query: str,
    *,
    index_col: Iterable[str] | str = (),
    col_order: Iterable[str] = (),
    max_results: Optional[int] = None,
) -> bigframes.dataframe.DataFrame:
    _set_default_session_location_if_possible(query)
    return _with_default_session(
        bigframes.session.Session.read_gbq_query,
        query,
        index_col=index_col,
        col_order=col_order,
        max_results=max_results,
    )


read_gbq_query.__doc__ = inspect.getdoc(bigframes.session.Session.read_gbq_query)


def read_gbq_table(
    query: str,
    *,
    index_col: Iterable[str] | str = (),
    col_order: Iterable[str] = (),
    max_results: Optional[int] = None,
) -> bigframes.dataframe.DataFrame:
    _set_default_session_location_if_possible(query)
    return _with_default_session(
        bigframes.session.Session.read_gbq_table,
        query,
        index_col=index_col,
        col_order=col_order,
        max_results=max_results,
    )


read_gbq_table.__doc__ = inspect.getdoc(bigframes.session.Session.read_gbq_table)


def read_pandas(pandas_dataframe: pandas.DataFrame) -> bigframes.dataframe.DataFrame:
    return _with_default_session(
        bigframes.session.Session.read_pandas,
        pandas_dataframe,
    )


read_pandas.__doc__ = inspect.getdoc(bigframes.session.Session.read_pandas)


def read_parquet(path: str | IO["bytes"]) -> bigframes.dataframe.DataFrame:
    return _with_default_session(
        bigframes.session.Session.read_parquet,
        path,
    )


read_parquet.__doc__ = inspect.getdoc(bigframes.session.Session.read_parquet)


def remote_function(
    input_types: List[type],
    output_type: type,
    dataset: Optional[str] = None,
    bigquery_connection: Optional[str] = None,
    reuse: bool = True,
):
    return _with_default_session(
        bigframes.session.Session.remote_function,
        input_types=input_types,
        output_type=output_type,
        dataset=dataset,
        bigquery_connection=bigquery_connection,
        reuse=reuse,
    )


remote_function.__doc__ = inspect.getdoc(bigframes.session.Session.remote_function)


# Other aliases
DataFrame = bigframes.dataframe.DataFrame
Index = bigframes.core.indexes.Index
Series = bigframes.series.Series

# Use __all__ to let type checkers know what is part of the public API.
__all___ = [
    "concat",
    "DataFrame",
    "options",
    "read_csv",
    "read_gbq",
    "read_gbq_model",
    "read_pandas",
    "remote_function",
    "Series",
]
