from unittest import mock

import ibis
from ibis.expr.types import Column, Table

from bigframes import core


def test_constructor_from_ibis_table_adds_all_columns(
    session, scalars_ibis_table: Table
):
    actual = core.BigFramesExpr(session=session, table=scalars_ibis_table)
    assert actual._table is scalars_ibis_table
    assert len(actual._columns) == len(scalars_ibis_table.columns)


def test_projection_doesnt_change_original(session):
    mock_table = mock.create_autospec(Table)
    mock_column = mock.create_autospec(Column)
    original = core.BigFramesExpr(
        session=session, table=mock_table, columns=[mock_column]
    )
    assert original._table is mock_table
    assert len(original._columns) == 1
    assert original._columns[0] is mock_column

    # Create a new expression from a projection.
    new_column_1 = mock.create_autospec(Column)
    new_column_2 = mock.create_autospec(Column)
    assert new_column_1 is not mock_column
    assert new_column_2 is not mock_column
    actual = original.projection([new_column_1, mock_column, new_column_2])

    # Expected values are present.
    assert actual._table is mock_table
    assert len(actual._columns) == 3
    assert actual._columns[0] is new_column_1
    assert actual._columns[1] is mock_column
    assert actual._columns[2] is new_column_2
    # Don't modify the original.
    assert original._table is mock_table
    assert len(original._columns) == 1
    assert original._columns[0] is mock_column


def test_to_ibis_expr_with_projection(session, scalars_ibis_table: Table):
    expr = core.BigFramesExpr(session=session, table=scalars_ibis_table).projection(
        [
            scalars_ibis_table["int64_col"],
            ibis.literal(123456789).name("literals"),
            scalars_ibis_table["string_col"],
        ]
    )
    actual = expr.to_ibis_expr()
    assert len(actual.columns) == 3
    assert actual.columns[0] == "int64_col"
    assert actual.columns[1] == "literals"
    assert actual.columns[2] == "string_col"