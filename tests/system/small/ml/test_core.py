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

from datetime import datetime
import typing
from unittest import TestCase

import pandas as pd
import pyarrow as pa
import pytz

import bigframes
import bigframes.ml.core


def test_model_eval(
    penguins_bqml_linear_model,
):
    result = penguins_bqml_linear_model.evaluate().compute()
    expected = pd.DataFrame(
        {
            "mean_absolute_error": [227.01223],
            "mean_squared_error": [81838.159892],
            "mean_squared_log_error": [0.00507],
            "median_absolute_error": [173.080816],
            "r2_score": [0.872377],
            "explained_variance": [0.872377],
        },
        dtype="Float64",
    )
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_model_eval_with_data(penguins_bqml_linear_model, penguins_df_default_index):
    result = penguins_bqml_linear_model.evaluate(
        penguins_df_default_index.dropna()
    ).compute()
    expected = pd.DataFrame(
        {
            "mean_absolute_error": [225.817334],
            "mean_squared_error": [80540.705944],
            "mean_squared_log_error": [0.004972],
            "median_absolute_error": [173.080816],
            "r2_score": [0.87529],
            "explained_variance": [0.87529],
        },
        dtype="Float64",
    )
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_model_predict(
    penguins_bqml_linear_model: bigframes.ml.core.BqmlModel, new_penguins_df
):
    predictions = penguins_bqml_linear_model.predict(new_penguins_df).compute()
    expected = pd.DataFrame(
        {"predicted_body_mass_g": [4030.1, 3280.8, 3177.9]},
        dtype="Float64",
        index=pd.Index([1633, 1672, 1690], name="tag_number", dtype="Int64"),
    )
    pd.testing.assert_frame_equal(
        predictions[["predicted_body_mass_g"]].sort_index(),
        expected,
        check_exact=False,
        rtol=1e-2,
    )


def test_model_predict_with_unnamed_index(
    penguins_bqml_linear_model: bigframes.ml.core.BqmlModel, new_penguins_df
):

    # This will result in an index that lacks a name, which the ML library will
    # need to persist through the call to ML.PREDICT
    new_penguins_df = new_penguins_df.reset_index()

    # remove the middle tag number to ensure we're really keeping the unnamed index
    new_penguins_df = typing.cast(
        bigframes.DataFrame, new_penguins_df[new_penguins_df.tag_number != 1672]
    )

    predictions = penguins_bqml_linear_model.predict(new_penguins_df).compute()

    expected = pd.DataFrame(
        {"predicted_body_mass_g": [4030.1, 3177.9]},
        dtype="Float64",
        index=pd.Index([0, 2], dtype="Int64"),
    )
    pd.testing.assert_frame_equal(
        predictions[["predicted_body_mass_g"]].sort_index(),
        expected,
        check_exact=False,
        rtol=1e-2,
    )


def test_model_generate_text(
    bqml_palm2_text_generator_model: bigframes.ml.core.BqmlModel, llm_text_df
):
    options = {"temperature": 0.5, "max_output_tokens": 100, "top_k": 20, "top_p": 0.5}
    df = bqml_palm2_text_generator_model.generate_text(
        llm_text_df, options=options
    ).compute()

    TestCase().assertSequenceEqual(df.shape, (3, 3))
    TestCase().assertSequenceEqual(
        ["ml_generate_text_result", "ml_generate_text_status", "prompt"],
        df.columns.to_list(),
    )
    series = df["ml_generate_text_result"]
    assert all(series.str.contains("predictions"))


def test_model_forecast(time_series_bqml_arima_plus_model: bigframes.ml.core.BqmlModel):
    utc = pytz.utc
    forecast = time_series_bqml_arima_plus_model.forecast().compute()[
        ["forecast_timestamp", "forecast_value"]
    ]
    expected = pd.DataFrame(
        {
            "forecast_timestamp": [
                datetime(2017, 8, 2, tzinfo=utc),
                datetime(2017, 8, 3, tzinfo=utc),
                datetime(2017, 8, 4, tzinfo=utc),
            ],
            "forecast_value": [2724.472284, 2593.368389, 2353.613034],
        }
    )
    expected["forecast_value"] = expected["forecast_value"].astype(pd.Float64Dtype())
    expected["forecast_timestamp"] = expected["forecast_timestamp"].astype(
        pd.ArrowDtype(pa.timestamp("us", tz="UTC"))
    )
    pd.testing.assert_frame_equal(
        forecast,
        expected,
        rtol=1e-2,
        check_index_type=False,
    )
