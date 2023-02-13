"""Session manages the connection to BigQuery."""

from typing import Optional

import google.auth.credentials
import google.cloud.bigquery
import ibis

from bigframes.core import BigFramesExpr
from bigframes.dataframe import DataFrame


class Context:
    """Encapsulates configuration for working with an Session.

    Attributes:
      credentials: The OAuth2 Credentials to use for this client. If not passed
        falls back to the default inferred from the environment.
      project: Project ID for the project which the client acts on behalf of. Will
        be passed when creating a dataset / job. If not passed, falls back to the
        default inferred from the environment.
      location: Default location for jobs / datasets / tables.
    """

    def __init__(
        self,
        credentials: Optional[google.auth.credentials.Credentials] = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
    ):
        self._credentials = credentials
        self._project = project
        self._location = location

    @property
    def credentials(self) -> Optional[google.auth.credentials.Credentials]:
        return self._credentials

    @property
    def project(self) -> Optional[str]:
        return self._project

    @property
    def location(self) -> Optional[str]:
        return self._location


class Session:
    """Establishes a BigQuery connection to capture a group of job activities related to DataFrames."""

    def __init__(self, context: Optional[Context] = None):
        # TODO(chelsealin): create a BigQuery Session at connect time.
        if context is not None:
            self.bqclient = google.cloud.bigquery.Client(
                credentials=context.credentials,
                project=context.project,
                location=context.location,
            )
            self.ibis_client = ibis.bigquery.connect(
                project_id=context.project, credentials=context.credentials
            )
        else:
            self.bqclient = google.cloud.bigquery.Client()
            self.ibis_client = ibis.bigquery.connect(project_id=self.bqclient.project)

    def read_gbq(self, table: str) -> "DataFrame":
        """Loads data from Google BigQuery."""
        parts = table.replace(":", ".").split(".")
        # TODO(swast): allow for a default project and/or dataset
        # TODO(swast): If a table ID, make sure we read from a snapshot to
        # better emulate pandas.read_gbq.
        if len(parts) != 3:
            raise ValueError(
                "read_gbq requires a full table ID, including project and dataset."
            )
        table_expression = self.ibis_client.table(
            parts[2], database=f"{parts[0]}.{parts[1]}"
        )
        return DataFrame(BigFramesExpr(self, table_expression))


def connect(context: Optional[Context] = None) -> Session:
    # TODO(swast): Start a BigQuery Session too.
    return Session(context)