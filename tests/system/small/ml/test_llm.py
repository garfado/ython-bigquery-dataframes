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

from unittest import TestCase

import numpy as np


def test_create_text_generator_model(palm2_text_generator_model):
    # Model creation doesn't return error
    assert palm2_text_generator_model is not None


def test_text_generator_predict_default_params_success(
    palm2_text_generator_model, llm_text_df
):
    df = palm2_text_generator_model.predict(llm_text_df).compute()
    TestCase().assertSequenceEqual(df.shape, (3, 1))
    assert "ml_generate_text_llm_result" in df.columns
    series = df["ml_generate_text_llm_result"]
    assert all(series.str.len() > 20)


def test_text_generator_predict_with_params_success(
    palm2_text_generator_model, llm_text_df
):
    df = palm2_text_generator_model.predict(
        llm_text_df, temperature=0.5, max_output_tokens=100, top_k=20, top_p=0.5
    ).compute()
    TestCase().assertSequenceEqual(df.shape, (3, 1))
    assert "ml_generate_text_llm_result" in df.columns
    series = df["ml_generate_text_llm_result"]
    assert all(series.str.len() > 20)


def test_create_embedding_generator_model(palm2_embedding_generator_model):
    # Model creation doesn't return error
    assert palm2_embedding_generator_model is not None


def test_embedding_generator_predict_success(
    palm2_embedding_generator_model, llm_embedding_df
):
    df = palm2_embedding_generator_model.predict(llm_embedding_df).compute()
    TestCase().assertSequenceEqual(df.shape, (3, 1))
    assert "ml_embed_text_embedding" in df.columns
    series = df["ml_embed_text_embedding"]
    value = series[0]
    assert isinstance(value, np.ndarray)
    assert value.size == 768
