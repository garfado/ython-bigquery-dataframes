class DatetimeProperties:
    """
    Accessor object for datetimelike properties of the Series values.
    """

    @property
    def day(self):
        """The day of the datetime."""

        raise NotImplementedError("abstract method")

    @property
    def dayofweek(self):
        """The day of the week with Monday=0, Sunday=6.

        Return the day of the week. It is assumed the week starts on
        Monday, which is denoted by 0 and ends on Sunday which is denoted
        by 6. This method is available on both Series with datetime
        values (using the `dt` accessor) or DatetimeIndex.

        Returns:
            Series or Index
                Containing integers indicating the day number.
        """

        raise NotImplementedError("abstract method")

    @property
    def date(self):
        """Returns numpy array of python :class:`datetime.date` objects.

        Namely, the date part of Timestamps without time and
        timezone information.

        warning:
            This method returns a Series whereas pandas returns
            a numpy array.
        """

        raise NotImplementedError("abstract method")

    @property
    def hour(self):
        """The hours of the datetime."""

        raise NotImplementedError("abstract method")

    @property
    def minute(self):
        """The minutes of the datetime."""

        raise NotImplementedError("abstract method")

    @property
    def month(self):
        """The month as January=1, December=12."""

        raise NotImplementedError("abstract method")

    @property
    def second(self):
        """The seconds of the datetime."""

        raise NotImplementedError("abstract method")

    @property
    def time(self):
        """Returns numpy array of :class:`datetime.time` objects.

        The time part of the Timestamps.

        warning:
            This method returns a Series whereas pandas returns
            a numpy array.
        """

        raise NotImplementedError("abstract method")

    @property
    def quarter(self):
        """The quarter of the date.

        warning:
           This method returns a Series whereas pandas returns
           a numpy array.
        """

        raise NotImplementedError("abstract method")

    @property
    def year(self):
        """The year of the datetime."""

        raise NotImplementedError("abstract method")