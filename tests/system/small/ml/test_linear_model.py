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
import pandas
import pytest

import bigframes.ml.linear_model


def test_model_eval(
    penguins_linear_model: bigframes.ml.linear_model.LinearRegression,
):
    result = penguins_linear_model.score().compute()
    expected = pandas.DataFrame(
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
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_model_score_with_data(penguins_linear_model, penguins_df_default_index):
    df = penguins_df_default_index.dropna()
    test_X = df[
        [
            "species",
            "island",
            "culmen_length_mm",
            "culmen_depth_mm",
            "flipper_length_mm",
            "sex",
        ]
    ]
    test_y = df[["body_mass_g"]]
    result = penguins_linear_model.score(test_X, test_y).compute()
    expected = pandas.DataFrame(
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
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_model_predict(penguins_linear_model, new_penguins_df):
    predictions = penguins_linear_model.predict(new_penguins_df).compute()
    expected = pandas.DataFrame(
        {"predicted_body_mass_g": [4030.1, 3280.8, 3177.9]},
        dtype="Float64",
        index=pandas.Index([1633, 1672, 1690], name="tag_number", dtype="Int64"),
    )
    pandas.testing.assert_frame_equal(
        predictions.sort_index(),
        expected,
        check_exact=False,
        rtol=1e-2,
    )


def test_to_gbq_saved_model_scores(penguins_linear_model, dataset_id):
    saved_model = penguins_linear_model.to_gbq(
        f"{dataset_id}.test_penguins_model", replace=True
    )
    result = saved_model.score().compute()
    expected = pandas.DataFrame(
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
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_to_gbq_replace(penguins_linear_model, dataset_id):
    penguins_linear_model.to_gbq(f"{dataset_id}.test_penguins_model", replace=True)
    with pytest.raises(google.api_core.exceptions.Conflict):
        penguins_linear_model.to_gbq(f"{dataset_id}.test_penguins_model")


def test_logistic_model_eval(
    penguins_logistic_model: bigframes.ml.linear_model.LogisticRegression,
):
    result = penguins_logistic_model.score().compute()
    expected = pandas.DataFrame(
        {
            "precision": [0.616753],
            "recall": [0.618615],
            "accuracy": [0.92515],
            "f1_score": [0.617681],
            "log_loss": [1.498832],
            "roc_auc": [0.975807],
        },
        dtype="Float64",
    )
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_logistic_model_score_with_data(
    penguins_logistic_model, penguins_df_default_index
):
    df = penguins_df_default_index.dropna()
    test_X = df[
        [
            "species",
            "island",
            "culmen_length_mm",
            "culmen_depth_mm",
            "flipper_length_mm",
            "body_mass_g",
        ]
    ]
    test_y = df[["sex"]]
    result = penguins_logistic_model.score(test_X, test_y).compute()
    expected = pandas.DataFrame(
        {
            "precision": [0.616753],
            "recall": [0.618615],
            "accuracy": [0.92515],
            "f1_score": [0.617681],
            "log_loss": [1.498832],
            "roc_auc": [0.975807],
        },
        dtype="Float64",
    )
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_logsitic_model_predict(penguins_logistic_model, new_penguins_df):
    predictions = penguins_logistic_model.predict(new_penguins_df).compute()
    expected = pandas.DataFrame(
        {"predicted_sex": ["MALE", "MALE", "FEMALE"]},
        dtype="string[pyarrow]",
        index=pandas.Index([1633, 1672, 1690], name="tag_number", dtype="Int64"),
    )
    pandas.testing.assert_frame_equal(
        predictions.sort_index(),
        expected,
        check_exact=False,
        rtol=1e-2,
    )


def test_to_gbq_saved_logsitic_model_scores(penguins_logistic_model, dataset_id):
    saved_model = penguins_logistic_model.to_gbq(
        f"{dataset_id}.test_penguins_model", replace=True
    )
    result = saved_model.score().compute()
    expected = pandas.DataFrame(
        {
            "precision": [0.616753],
            "recall": [0.618615],
            "accuracy": [0.92515],
            "f1_score": [0.617681],
            "log_loss": [1.498832],
            "roc_auc": [0.975807],
        },
        dtype="Float64",
    )
    pandas.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
        # int64 Index by default in pandas versus Int64 (nullable) Index in BigFramese
        check_index_type=False,
    )


def test_to_logistic_model_gbq_replace(penguins_logistic_model, dataset_id):
    penguins_logistic_model.to_gbq(f"{dataset_id}.test_penguins_model", replace=True)
    with pytest.raises(google.api_core.exceptions.Conflict):
        penguins_logistic_model.to_gbq(f"{dataset_id}.test_penguins_model")
