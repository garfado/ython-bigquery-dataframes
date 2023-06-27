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

import numpy as np
import pandas as pd


def test_create_model(imported_tensorflow_model):
    # Model creation doesn't return error
    assert imported_tensorflow_model is not None


def test_model_predict(imported_tensorflow_model, llm_text_df):
    df = llm_text_df.rename(columns={"prompt": "input"})
    result = imported_tensorflow_model.predict(df).compute()
    # The values are non-human-readable. As they are a dense layer of Neural Network.
    # And since it is pretrained and imported, the model is a opaque-box.
    # We may want to switch to better test model and cases.
    value = np.array(
        [9.375373792863684e-07, 0.00015779426030348986, 0.9998412132263184]
    )
    expected = pd.DataFrame(
        {
            "dense_1": [value, value, value],
        },
    )
    expected.set_index(expected.index.astype("Int64"), inplace=True)
    pd.testing.assert_frame_equal(
        result,
        expected,
        check_exact=False,
        rtol=1e-2,
    )