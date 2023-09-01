# Authors: Alexandre Gramfort <alexandre.gramfort@inria.fr>
#          Mathieu Blondel <mathieu@mblondel.org>
#          Olivier Grisel <olivier.grisel@ensta.org>
#          Andreas Mueller <amueller@ais.uni-bonn.de>
#          Eric Martin <eric@ericmart.in>
#          Giorgio Patrini <giorgio.patrini@anu.edu.au>
#          Eric Chang <ericchang2017@u.northwestern.edu>
# License: BSD 3 clause

from bigframes import constants
from third_party.bigframes_vendored.sklearn.base import BaseEstimator, TransformerMixin


class StandardScaler(BaseEstimator, TransformerMixin):
    """Standardize features by removing the mean and scaling to unit variance.

    The standard score of a sample `x` is calculated as:z = (x - u) / s
    where `u` is the mean of the training samples or zero if `with_mean=False`,
    and `s` is the standard deviation of the training samples or one if
    `with_std=False`.

    Centering and scaling happen independently on each feature by computing
    the relevant statistics on the samples in the training set. Mean and
    standard deviation are then stored to be used on later data using
    :meth:`transform`.

    Standardization of a dataset is a common requirement for many
    machine learning estimators: they might behave badly if the
    individual features do not more or less look like standard normally
    distributed data (e.g. Gaussian with 0 mean and unit variance).

    Examples:

        .. code-block::

            from bigframes.ml.preprocessing import StandardScaler
            import bigframes.pandas as bpd

            scaler = StandardScaler()
            data = bpd.DataFrame({"a": [0, 0, 1, 1], "b":[0, 0, 1, 1]})
            scaler.fit(data)
            print(scaler.transform(data))
            print(scaler.transform(bpd.DataFrame({"a": [2], "b":[2]})))
    """

    def fit(self, X):
        """Compute the mean and std to be used for later scaling.

        Args:
            X (bigframes.dataframe.DataFrame or bigframes.series.Series):
                The Dataframe or Series with training data.

        Returns:
            StandardScaler: Fitted scaler.
        """
        raise NotImplementedError(constants.ABSTRACT_METHOD_ERROR_MESSAGE)

    def transform(self, X):
        """Perform standardization by centering and scaling.

        Args:
            X (bigframes.dataframe.DataFrame or bigframes.series.Series):
                The DataFrame or Series to be transformed.

        Returns:
           bigframes.dataframe.DataFrame: Transformed result.
        """
        raise NotImplementedError(constants.ABSTRACT_METHOD_ERROR_MESSAGE)
