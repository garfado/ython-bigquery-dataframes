""" Principal Component Analysis.
"""

# Author: Alexandre Gramfort <alexandre.gramfort@inria.fr>
#         Olivier Grisel <olivier.grisel@ensta.org>
#         Mathieu Blondel <mathieu@mblondel.org>
#         Denis A. Engemann <denis-alexander.engemann@inria.fr>
#         Michael Eickenberg <michael.eickenberg@inria.fr>
#         Giorgio Patrini <giorgio.patrini@anu.edu.au>
#
# License: BSD 3 clause

from abc import ABCMeta

from third_party.bigframes_vendored.sklearn.base import BaseEstimator


class PCA(BaseEstimator, metaclass=ABCMeta):
    """Principal component analysis (PCA).

    Linear dimensionality reduction using Singular Value Decomposition of the
    data to project it to a lower dimensional space. The input data is centered
    but not scaled for each feature before applying the SVD.

    It uses the LAPACK implementation of the full SVD or a randomized truncated
    SVD by the method of Halko et al. 2009, depending on the shape of the input
    data and the number of components to extract.

    It can also use the scipy.sparse.linalg ARPACK implementation of the
    truncated SVD.

    Args:
         n_components: Optional[int]
            Number of components to keep. if n_components is not set all components are kept.

    """

    def fit(
        self,
        X,
    ):
        """Fit the model according to the given training data.

        Args:
            X:
                DataFrame of shape (n_samples, n_features). Training vector,
                where `n_samples` is the number of samples and `n_features` is
                the number of features.

        Returns:
            Fitted estimator.
        """
        raise NotImplementedError("abstract method")
