import os


class IODDNotFoundError(Exception):
    """Exception raised for missing IODD files in the collection."""

    def __init__(self, sensor: str, collection_loc: str = "collection") -> None:
        """Create IODDNotFoundError object.

        :param sensor: name of the sensor that is missing an IODD
        :param collection_loc: location of the IODD collection, defaults to "collection"
        """
        self.sensor = sensor
        if collection_loc == "collection":
            self.collection_loc = os.path.join(os.getcwd(), "iodd", collection_loc)
        else:
            self.collection_loc = collection_loc
        self.msg = (
            f"IODD collection @ {self.collection_loc} does not contain IODD "
            f"for sensor {self.sensor}"
        )
        super().__init__(self.msg)
