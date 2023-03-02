"""Block is a 2D data structure that supports data mutability and views.

These data structures are shared by DataFrame and Series. This allows views to
link in both directions (DataFrame to Series and vice versa) and prevents
circular dependencies.
"""

from __future__ import annotations

import itertools
import typing
from typing import Iterable, Optional, Sequence

import ibis.expr.types as ibis_types
import pandas

import bigframes.core
import bigframes.core.indexes as indexes


class Block:
    """A mutable 2D data structure."""

    def __init__(
        self, expr: bigframes.core.BigFramesExpr, index_columns: Iterable[str] = ()
    ):
        self._expr = expr
        self._index = indexes.ImplicitJoiner(expr)
        self._index_columns = tuple(index_columns)
        self._reset_index()

    @property
    def index(self) -> indexes.ImplicitJoiner:
        """Row identities for values in the Block."""
        return self._index

    @index.setter
    def index(self, value: indexes.ImplicitJoiner):
        self._expr = value._expr
        if isinstance(value, indexes.Index):
            self._index_columns = (value._index_column,)
        else:
            self._index_columns = ()
        self._index = value

    @property
    def index_columns(self) -> Sequence[str]:
        """Column(s) to use as row labels."""
        return self._index_columns

    @index_columns.setter
    def index_columns(self, value: Iterable[str]):
        self._index_columns = tuple(value)
        self._reset_index()

    @property
    def expr(self) -> bigframes.core.BigFramesExpr:
        """Expression representing all columns, including index columns."""
        return self._expr

    @expr.setter
    def expr(self, expr: bigframes.core.BigFramesExpr):
        self._expr = expr
        self._reset_index()

    def _reset_index(self):
        """Update index to match latest expression and column(s)."""
        expr = self._expr
        columns = self._index_columns
        if len(columns) == 0:
            self._index = indexes.ImplicitJoiner(expr)
        elif len(columns) == 1:
            name = self._index.name if hasattr(self._index, "name") else columns[0]
            self._index = indexes.Index(expr, columns[0])
            self._index.name = name
        else:
            raise NotImplementedError("MultiIndex not supported.")

    def compute(self, value_keys: Optional[Iterable[str]] = None) -> pandas.DataFrame:
        """Run query and download results as a pandas DataFrame."""
        # TODO(swast): Allow for dry run and timeout.
        expr = self._expr

        if value_keys is not None:
            value_columns = (
                self._expr.get_column(column_name) for column_name in value_keys
            )
            index_columns = (
                self._expr.get_column(column_name)
                for column_name in self._index_columns
            )
            expr = self.expr.projection(itertools.chain(value_columns, index_columns))

        # TODO(swast): Use Ibis execute() for now, but ideally we'd do our own
        # thing via the BQ client library where we can more easily override the
        # output dtypes to use nullable dtypes and avoid lossy conversions.
        df = expr.to_ibis_expr().execute()

        if self.index_columns:
            df = df.set_index(list(self.index_columns))
            # TODO(swast): Set names for all levels with MultiIndex.
            df.index.name = typing.cast(indexes.Index, self.index).name
        return df

    def copy(self, value_columns: Optional[Iterable[ibis_types.Value]] = None) -> Block:
        """Create a copy of this Block, replacing value columns if desired."""
        # BigFramesExpr and Tuple are immutable, so just need a new wrapper.
        block = Block(self._expr, self._index_columns)

        if value_columns is not None:
            block.replace_value_columns(value_columns)

        return block

    def replace_value_columns(self, value_columns: Iterable[ibis_types.Value]):
        columns = []
        index_columns = (
            self._expr.get_column(column_name) for column_name in self._index_columns
        )
        for column in itertools.chain(index_columns, value_columns):
            columns.append(column)
        self.expr = self._expr.projection(columns)