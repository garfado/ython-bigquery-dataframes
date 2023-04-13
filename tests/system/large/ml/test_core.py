import pandas

import bigframes.ml.core


def test_bqml_e2e(session, dataset_id, penguins_df_no_index):
    df = penguins_df_no_index.dropna()
    train_X = df[
        [
            "species",
            "island",
            "culmen_length_mm",
            "culmen_depth_mm",
            "flipper_length_mm",
            "sex",
        ]
    ]
    train_y = df[["body_mass_g"]]
    model = bigframes.ml.core.create_bqml_model(
        train_X, train_y, {"model_type": "linear_reg"}
    )

    # no data - report evaluation from the automatic data split
    evaluate_result = model.evaluate().compute()
    evaluate_expected = pandas.DataFrame(
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
        evaluate_result, evaluate_expected, check_exact=False, rtol=1e-2
    )

    # evaluate on all training data
    evaluate_result = model.evaluate(df).compute()
    pandas.testing.assert_frame_equal(
        evaluate_result, evaluate_expected, check_exact=False, rtol=1e-2
    )

    # predict new labels
    new_penguins = session.read_pandas(
        pandas.DataFrame(
            {
                "tag_number": [1633, 1672, 1690],
                "species": [
                    "Adelie Penguin (Pygoscelis adeliae)",
                    "Adelie Penguin (Pygoscelis adeliae)",
                    "Chinstrap penguin (Pygoscelis antarctica)",
                ],
                "island": ["Torgersen", "Torgersen", "Dream"],
                "culmen_length_mm": [39.5, 38.5, 37.9],
                "culmen_depth_mm": [18.8, 17.2, 18.1],
                "flipper_length_mm": [196.0, 181.0, 188.0],
                "sex": ["MALE", "FEMALE", "FEMALE"],
            }
        ).set_index("tag_number")
    )
    predictions = model.predict(new_penguins).compute()
    expected = pandas.DataFrame(
        {"predicted_body_mass_g": [4030.1, 3280.8, 3177.9]},
        dtype="Float64",
        index=pandas.Index([1633, 1672, 1690], name="tag_number", dtype="Int64"),
    )
    pandas.testing.assert_frame_equal(
        predictions[["predicted_body_mass_g"]], expected, check_exact=False, rtol=1e-2
    )

    new_name = f"{dataset_id}.my_model"
    new_model = model.copy(new_name, True)
    assert new_model.model_name == new_name

    fetch_result = session.bqclient.get_model(new_name)
    assert fetch_result.model_type == "LINEAR_REGRESSION"