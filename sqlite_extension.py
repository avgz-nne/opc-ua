"""Module to extend sqlite3 with types to store lists with flexible length.

Classes
-------
StringList
    Manages lists that contain only strings
FloatList
    Manages lists that contain only numerical values (as floats)

Functions
---------
adapt_stringlist
    SQLite adapter for StringList class
adapt_floatlist
    SQLite adapter for FloatList class
convert_stringlist
    SQLite converter for StringList class
convert_floatlist
    SQLite converter for FloatList class
register_list_types
    Convenience wrapper to register the StringList and FloatList class with their
    respective adapter and converter functions

"""
from collections.abc import Generator

import sqlite3


class StringList:
    """Class to manage lists containing strings that get inserted into SQLite databases.

    Attributes
    ----------
    ls : list
        List containing the strings

    """

    def __init__(self, *args) -> None:
        """Create StringList object.

        :param args: list entries
        """
        self.ls = [str(arg) for arg in list(args)]

    def __repr__(self) -> str:
        """Show human-readable version of the object."""
        return f"StringList({', '.join(self.ls)})"

    def __iter__(self) -> Generator:
        """Provide a generator so the object can be converted to a list."""
        for item in self.ls:
            yield item


class FloatList:
    """Class to manage lists containing numbers that get inserted into SQLite databases.

    Attributes
    ----------
    ls : list
        List containing the numbers

    """

    def __init__(self, *args) -> None:
        """Create FloatList object.

        :param args: list entries
        """
        self.ls = [float(arg) if arg is not None else -1.0 for arg in args]

    def __repr__(self) -> str:
        """Show human-readable version of the object."""
        return f"FloatList({', '.join([str(i) for i in self.ls])})"

    def __iter__(self) -> Generator:
        """Provide a generator so the object can be converted to a list."""
        for item in self.ls:
            yield item


def adapt_stringlist(ls: StringList) -> str:
    """Convert StringList object to string for SQLite usage.

    :param ls: StringList object to be inserted into a table
    :returns: converted string
    """
    return ",".join([str(i) for i in ls.ls])


def convert_stringlist(s: str) -> StringList:
    """Convert string received from SQLite db to StringList object.

    :param s: string input from SQL query
    :returns: converted StringList object
    """
    return StringList(*list(map(str, s.split(b","))))


def adapt_floatlist(ls: FloatList) -> str:
    """Convert FloatList object to string for SQLite usage.

    :param ls: FloatList object to be inserted into a table
    :returns: converted string
    """
    return ",".join([str(i) for i in ls.ls])


def convert_floatlist(s: str) -> FloatList:
    """Convert string received from SQLite db to FloatList object.

    :param s: string input from SQL query
    :returns: converted FloatList object
    """
    return FloatList(*list(map(float, s.split(b","))))


def register_list_types():
    """Register adapter and converter functions to sqlite3."""
    sqlite3.register_adapter(StringList, adapt_stringlist)
    sqlite3.register_adapter(FloatList, adapt_floatlist)

    sqlite3.register_converter("stringlist", convert_stringlist)
    sqlite3.register_converter("floatlist", convert_floatlist)
