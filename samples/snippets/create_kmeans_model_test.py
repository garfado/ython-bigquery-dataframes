def test_kmeans_sample():
    import datetime

    import bigframes
    from bigframes import dataframe
    import bigframes.pandas as bpd

    # NOTE:  ask about line below and whether it is needed outside of colab notebooks
    # bigframes.options.bigquery.project= "username-testing"
    # read_gbq: Loads a DataFrame from BigQuery
    h = bpd.read_gbq("bigquery-public-data.london_bicycles.cycle_hire")
    s = bpd.read_gbq(
        """
        SELECT
        id,
        ST_DISTANCE(
            ST_GEOGPOINT(s.longitude, s.latitude),
            ST_GEOGPOINT(-0.1, 51.5)
        ) / 1000 AS distance_from_city_center
        FROM
        `bigquery-public-data.london_bicycles.cycle_stations` s
        """
    )
    # transform the data
    h = h.rename(
        columns={"start_station_name": "station_name", "start_station_id": "station_id"}
    )
    h = h[["start_date", "station_name", "station_id", "duration"]]

    # NOTE: line below is not accessed, is it needed outside of colab notebook?
    start_date = datetime.datetime.now()
    sample_time = datetime.datetime(2015, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    sample_time2 = datetime.datetime(2016, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    h = h.loc[(h["start_date"] >= sample_time) & (h["start_date"] <= sample_time2)]

    isweekday = h.start_date.dt.dayofweek.map(
        {
            0: "weekday",
            1: "weekday",
            2: "weekday",
            3: "weekday",
            4: "weekday",
            5: "weekend",
            6: "weekend",
        }
    )

    # create the new dataframe variable, stationstats
    merged_df = h.merge(
        right=s,
        how="inner",
        left_on="station_id",
        right_on="id",
    )

    stationstats = merged_df.groupby("station_name").agg(
        {"duration": ["mean", "count"], "distance_from_city_center": "max"}
    )

    def station_filter():
        stationstats.columns = ["duration", "num_trips", "distance_from_city_center"]
        stationstats.sort_values(by="distance_from_city_center", ascending=True)
        filter = """REGEXP_CONTAINS(station_name, 'Kennington')"""

    # import the KMeans model to cluster the data
    from bigframes.ml.cluster import KMeans

    cluster_model = KMeans(n_clusters=4)
    cluster_model = cluster_model.fit(stationstats)

    # the following function predicts the cluster of every station that has the string "Kennington" in its name.
    def predict_kennington_stations():
        cluster_model.predict(stationstats)
