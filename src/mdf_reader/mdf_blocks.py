"""
This module is part of the mdf_parser.

The *md_blocks* module contains classes for all required blocks of a mdf-file

Objects of the different mdf format blocks are instantiated by the MDFParser or by the
classes within mdf_blocks itself.

Short description of the block classes
======================================

MDFBlock
--------
Is the base class for all other classes

Provides methods for the interpretation of the mdf standard

Provides methods to manipulate strings

Methods is this class a common for all other classes

MDHFileHeader
-------------
Name in MDF: Identification block

Identification of the file as MDF file and MDF version

"""

import logging
from builtins import object, range, str
from re import match
from struct import unpack_from

from numpy import asarray, dtype, ndarray


class DataFormat(object):
    """
    Definition of format names according to MDF manual.

    Notes
    -----
    - The coding is one-index-based and cyclic on 256, meaning that 256 = 1, 257 = 2,…
    - To obtain the correct name, do : DataFormat[ data_format_nr % 256 - 1]
    """

    _names = [
        "CHAR",  # x01
        "UCHAR",  # x02
        "SHORT",  # x03
        "USHORT",  # x04
        "LONG",  # x05
        "ULONG",  # x06
        "LONGLONG",  # x07
        "ULONGLONG",  # x09
        "FLOAT",  # x0A (10 in decimal)
        "DOUBLE",  # x0B (11 in decimal)
        "BOOL8",  # x0C (12 in decimal)
        "BOOL16",  # x0D (13 in decimal)
        "BOOL32",  # x0E (14 in decimal)
        "BOOL64",  # x0F (15 in decimal)
        "ymdhms",  # x10 (16 in decimal)
        "text",  # x11 (17 in decimal)
        "REAL48",  # x12 (18 in decimal)
        "LONG DOUBLE",  # x13 (19 in decimal)
        "UINT8",  # Not MDF def, but own
        "UINT16",  # Not MDF def, but own
        "INT16",  # Not MDF def, but own
        "UINT32",  # Not MDF def, but own
        "UINT64",  # Not MDF def, but own
        "BOOL",  # Not MDF def, but own
        "REAL",  # Not MDF def, but own
        "LINK",  # Not MDF def, but own
    ]

    # define a dictionary carrying the size of all the data formats above
    bytes = dict()
    for name in _names:
        if name in ("CHAR", "UCHAR", "BOOL8", "UINT8"):
            bytes[name] = 1
        elif name in ("SHORT", "USHORT", "BOOL16", "UINT16", "INT16", "BOOL"):
            bytes[name] = 2
        elif name in ("LONG", "ULONG", "FLOAT", "BOOL32", "UINT32", "ymdhms", "LINK"):
            bytes[name] = 4
        elif name in "REAL48":
            bytes[name] = 6
        elif name in ("LONGLONG", "ULONGLONG", "DOUBLE", "BOOL64", "UINT64", "REAL"):
            bytes[name] = 8
        elif name in "LONG DOUBLE":
            bytes[name] = 10
        else:
            bytes[name] = None

    # create another dictionary carrying the data types for numpy
    np_dtypes = dict()
    for name in _names:
        if name in ("CHAR", "UCHAR", "UINT8", "text"):
            # Force chars to be ints to prevent a vstack error in python3.
            # Most likely, the CHAR columns are not decoded correctly, so in case these
            # columns are really needed, we need to have a look at this again
            np_dtypes[name] = dtype("int")
        elif name in ("BOOL8", "BOOL", "BOOL16", "BOOL32", "BOOL64"):
            np_dtypes[name] = dtype("bool")
        elif name in ("LONG", "LONG DOUBLE", "LINK"):
            np_dtypes[name] = dtype("int_")
        elif name in ("ULONG", "ymdhms"):
            np_dtypes[name] = dtype("uint")
        elif name in ("REAL", "REAL48"):
            np_dtypes[name] = dtype("float")
        else:
            np_dtypes[name] = dtype(name.lower())


def set_logging_level(logger, verbose=1):
    """function to set the level of the logger

    Parameters
    ----------
    logger :
        handle to the logger
    verbose :
        0=silent, 1=info, 2=debug (Default value = 1)

    Raises
    ------
    AssertionError
        In case a non valid option is passed


    """
    if verbose == 0:
        logger.setLevel(logging.WARNING)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    elif verbose == 2:
        logger.setLevel(logging.DEBUG)
    else:
        raise AssertionError("verbose must be 0, 1, or 2")


class MDFBlock:
    """
    Base class to define a block in the mdf file
    """

    def read_format(self, fp, data_type, number=1):
        """

        Parameters
        ----------
        fp : file object
            pointer to the current file

        data_type : dtype
            Type of the data to read

        number : int, optional
            Number of items to read. Default value = 1

        Returns
        -------
        dtype
            Unpacked data

        """

        byte_array = fp.read(number * DataFormat.bytes[data_type])

        out = self.unpack_byte_array(byte_array, data_type)

        return out

    @staticmethod
    def unpack_byte_array(byte_array, data_type):
        """

        Parameters
        ----------
        byte_array :  ndarray
            Array with the data to unpack

        data_type : dtype
            Type of the data

        Returns
        -------
        ndarray:
            Unpacked data

        """

        # turn the byte array in the appropriate data format
        try:
            if data_type == "CHAR":
                out = unpack_from("<b", byte_array)[0]
            elif data_type == "UCHAR":
                out = unpack_from("<B", byte_array)[0]
            elif data_type in ("UINT16", "USHORT"):
                out = unpack_from("<H", byte_array)[0]
            elif data_type in ("INT16", "SHORT"):
                out = unpack_from("<h", byte_array)[0]
            elif data_type in ("LONG", "LONGLONG"):
                out = unpack_from("<l", byte_array)[0]
            elif data_type in ("LINK", "UINT32", "ULONG", "ymdhms"):
                out = unpack_from("<L", byte_array)[0]
            elif data_type == "FLOAT":
                out = unpack_from("<f", byte_array)[0]
            elif data_type in ("REAL", "DOUBLE"):
                out = unpack_from("<d", byte_array)[0]
            elif data_type == "BOOL":
                tmp = unpack_from("<H", byte_array)[0]
                if tmp != 0:
                    out = True
                else:
                    out = False
            else:
                raise AssertionError("Data type '{}' not supported".format(data_type))
        except TypeError:
            raise

        return out

    @staticmethod
    def pretty(string):
        """Removes tailing zero strings from a string

        Parameters
        ----------
        string : str
            The string to clean

        Returns
        -------
        str
            string with removed tailing zero strings

        """

        try:
            # python 2 succeed here
            string = string.replace("\0", "").replace("\n", "").replace("\r", "")
        except TypeError:
            # if it fails, assume it it python 3, thus string is a byte array
            string = (
                str(string)
                .replace("\\x00", "")
                .replace("\\n", "")
                .replace("\\r", "")
                .replace("'", "")
                .replace("b", "")
            )

        return string

    def read_string(self, fp, n_characters):
        """Read a string consisting of n_characters starting at the current position of
        the file pointer

        Args:
            fp (IOStream): file pointer to the current data
            n_characters (int): Number of characters to read

        Returns:
            str: The string read from the fp file pointer

        Notes:
            It is also ensured that the file pointer is positioned at the end of the
            *n_characters* after reading
        """
        # the length of the name of the data set
        string_size = n_characters * DataFormat.bytes["CHAR"]
        fp_current_position = fp.tell()  # the current position in the binary file
        result = self.pretty(fp.read(string_size))
        fp.seek(
            fp_current_position + string_size
        )  # set the pointer to the end of the name string

        return result

    def _props(self):
        """ """
        return dict(
            (key, getattr(self, key))
            for key in dir(self)
            if key not in dir(self.__class__)
        )

    def __str__(self):
        """
        Overload the print-statement of the class.

        Now a pretty format al the attributes can be made by just printing the object

        Return
        ------
        str
            string passed to the print statement
        """
        ret_str = ""
        # loop over the dictionary props in alphabetical order
        for k, v in iter(sorted(self._props().items())):
            if not (match("^_", k)):
                ret_str += "{:<25} : {}\n".format(k, v)

        return ret_str


class MDHFileHeader(MDFBlock):
    """MDHFileHeader contains all information specified by MDF for the ID BLOCK

    Args:
        mdf_stream (IOStream): reference to mdf file

    Attributes:
        version (str) : Version string, such as 2.1
        version_minor (UINT16): Minor version (1)
        version_major (UINT16): Major version (2)
        status_record_position (LONG): Refers to status of type 10. Must be 0 if unused
        created_by(LONG): Generated by: 0=User, 1=MLab
        mdf_header_size (LONG): Size of the header (normally 72)
        store_type (LONG): storage method:
            0. Multiplexed
            1. Block-wise (currently unused)
        file_type (LONG): File type
        frame_size (LONG): Size of the data frame in bytes
        no_of_data_sets (LONG): Number of datasets in the file
        day (LONG): Day of the date at which the MDF file was created
        month (LONG): Month of the date at which the MDF file was created
        year (LONG): Year of the date at which the MDF file was created
        hour (LONG): Hour of the time at which the MDF file was created
        minute (LONG): Minute of the time at which the MDF file was created
        second (LONG): Second of the time at which the MDF file was created
    """

    def __init__(self, file_pointer):
        # initialize the attributes
        self.file_identifier = ""
        self.version = None
        self.version_minor = None
        self.version_major = None
        self.status_record_position = None
        self.created_by = None
        self.mdf_header_size = None
        self.store_type = None
        self.file_type = None
        self.frame_size = None
        self.no_of_data_sets = None
        self.day = None
        self.month = None
        self.year = None
        self.hour = None
        self.minute = None
        self.second = None

        self._read(file_pointer)

    def _read(self, fp):
        """Populates the attributes of the MDHFileHeader object with data from file

        Args:
            fp (IOStream): Reference to mdf file pointer

        """
        created_by_list = ["User", "MLab"]

        self.file_identifier = self.read_string(fp, 16)

        # The version is stored in a 4 byte (UINT32) of which the first 2 bytes contain
        # the minor and then the major
        version_minor = self.read_format(fp, "UINT16")
        version_major = self.read_format(fp, "UINT16")
        self.version = "{:d}.{:d}".format(version_major, version_minor)
        self.version_minor = version_minor
        self.version_major = version_major
        self.status_record_position = self.read_format(fp, "LONG")
        self.created_by = created_by_list[self.read_format(fp, "LONG")]
        self.mdf_header_size = self.read_format(fp, "LONG")
        self.store_type = self.read_format(fp, "LONG")
        self.file_type = self.read_format(fp, "LONG")
        self.frame_size = self.read_format(fp, "LONG")
        self.no_of_data_sets = self.read_format(fp, "LONG")
        self.day = self.read_format(fp, "LONG")
        self.month = self.read_format(fp, "LONG")
        self.year = self.read_format(fp, "LONG")
        self.hour = self.read_format(fp, "LONG")
        self.minute = self.read_format(fp, "LONG")
        self.second = self.read_format(fp, "LONG")


class DataSetRecord(MDFBlock):
    """
    DataSetRecord contains all information specified by MDF for the Dataset Record

    Args:
        file_pointer (object): Point to the file stream
        verbose (int): verbosity level

    Attributes:
        type (int): type of the data record
        size (int): size of the data record
        version (int): verbosity level
        frame_offset (int): offset of the current frame

    """

    def __init__(self, file_pointer, verbose=1):
        """constructor of the class"""
        self._log = logging.getLogger(__name__)
        set_logging_level(self._log, verbose)

        self.loaded_data = False

        # values belonging to the simple Data Set Entry which is read by all formats
        self.type = None
        self.size = None
        self.version = None
        self.frame_offset = None

        self._read_general_record_data(file_pointer)

        self._log.debug("Reading data file name section with type={}".format(self.type))

        if self.type == 1:
            self._read_data_filename(file_pointer)
        elif self.type == 2:
            self._read_simple_time_data(file_pointer)
        elif self.type in (100, 101, 110):

            # Always read the simple data set, even for extended data set in order to
            # position the file pointer
            self._read_simple_dataset(file_pointer)

            if self.type == 101:
                self._read_extended_dataset(file_pointer)
            elif self.type == 110:
                self._read_extended_dataset_multi_dim(file_pointer)
        else:
            raise IOError("Record Type not recognised: {}".format(self.type))

    def byte_to_ndarray(
        self,
        byte_array: object,
        frame_size: int,
        n_frames_to_read: int,
    ) -> ndarray:
        """
        Turn a byte array into a numpy array

        Args:
            byte_array (object): Binary array containing all the records
            frame_size (int): Size of a single frame
            n_frames_to_read (int): Number of records to read

        Returns:
            ndarray: The numpy array with the converted that
        """
        data_points = list()

        # loop over the data frames and convert the values of the current record
        for p_index in range(n_frames_to_read):
            ptr = self.frame_offset + p_index * frame_size
            value = self.unpack_byte_array(
                byte_array[ptr : ptr + self.data_format_size], self.data_format
            )
            data_points.append(value)

        np_data = asarray(data_points, dtype=self.data_format_numpy)

        return np_data

    def _read_general_record_data(self, fp):
        """
        Read the general record data

        Parameters
        ----------
        fp : file object
            pointer to the file buffer
        """
        self.type = self.read_format(fp, "LONG")
        self.size = self.read_format(fp, "LONG")
        version_minor = self.read_format(fp, "UINT16")
        version_major = self.read_format(fp, "UINT16")
        self.version = "{:d}.{:d}".format(version_major, version_minor)

    def _read_simple_dataset(self, fp):
        """
        Read the simple data set

        Parameters
        ----------
        fp : object file

        """

        self.id = self.read_format(fp, "LONG")
        self.name = self.read_string(fp, 64)
        self.label = self.read_string(fp, 64)
        self.unit = self.read_string(fp, 32)

        self.data_format_number = self.read_format(fp, "LONG")
        self.data_format = DataFormat._names[self.data_format_number % 256 - 1]
        self.data_format_size = DataFormat.bytes[self.data_format]
        self.data_format_numpy = DataFormat.np_dtypes[self.data_format]
        self.data_mask = self.read_format(fp, "LONG")
        self.factor = self.read_format(fp, "DOUBLE")
        self.constant = self.read_format(fp, "DOUBLE")
        self.frame_offset = self.read_format(fp, "LONG")
        self.NoInFrame = self.read_format(fp, "LONG")

    def _read_extended_dataset(self, fp):
        """
        Read the extended data set

        Parameters
        ----------
        fp : file pointer

        """

        self.data_type_id = self.read_format(fp, "LONG")
        self.parent_id = self.read_format(fp, "LONG")
        self.group_id = self.read_format(fp, "LONG")
        self.sensor_id = self.read_format(fp, "LONG")
        self.reference_id = self.read_format(fp, "LONG")
        self.frame_set_type = self.read_format(fp, "LONG")
        self.frame_increment = self.read_format(fp, "LONG")
        self.gap_offset = self.read_format(fp, "LONG")
        self.gap_increment = self.read_format(fp, "LONG")
        self.no_of_gaps = self.read_format(fp, "LONG")
        self.comment = self.read_string(fp, 128)
        self.def_color_flag = self.read_format(fp, "LONG")
        self.def_color_red = self.read_format(fp, "LONG")
        self.def_color_green = self.read_format(fp, "LONG")
        self.def_color_blue = self.read_format(fp, "LONG")
        self.def_scale_flag = self.read_format(fp, "LONG")
        self.def_min_scale = self.read_format(fp, "DOUBLE")
        self.def_max_scale = self.read_format(fp, "DOUBLE")
        self.carrier_offset = self.read_format(fp, "LONG")
        self.reserve_bytes = self.read_format(fp, "LONG")

    def _read_extended_dataset_multi_dim(self, fp):
        """
        Read the multi-dimensional data set

        Parameters
        ----------
        fp : file pointer
            The current file buffer

        """

        self.array_dimension = self.read_format(fp, "LONG")
        self.reserve_bytes = self.read_string(fp, 28)

        self.dim_size = []
        self.dim_type_type_id = []
        self.index_label = []
        self.index_unit = []
        self.index_offset = []
        self.reserve1 = []
        self.reserve2 = []
        self.reserve3 = []
        self.phys_label = []
        self.phys_unit = []
        self.phys_min_range = []
        self.phys_max_range = []

        for i in range(self.array_dimension):
            self.dim_size.append(self.read_format(fp, "LONG"))
            self.dim_type_type_id.append(self.read_format(fp, "LONG"))
            self.index_label.append(self.read_string(fp, 64))
            self.index_unit.append(self.read_string(fp, 32))
            self.index_offset.append(self.read_format(fp, "LONG"))
            self.reserve1.append(self.read_format(fp, "LONG"))
            self.reserve2.append(self.read_format(fp, "LONG"))
            self.reserve3.append(self.read_format(fp, "LONG"))
            self.phys_label.append(self.read_string(fp, 64))
            self.phys_unit.append(self.read_string(fp, 32))
            self.phys_min_range.append(self.read_format(fp, "DOUBLE"))
            self.phys_max_range.append(self.read_format(fp, "DOUBLE"))

            print("Type {} not yet implemented".format(self.type))

    def _read_data_filename(self, fp):
        """
        Read the current file name

        Parameters
        ----------
        fp : file object
            Pointer to the current file buffer
        """
        self.file_id = self.read_format(fp, "LONG")
        self.type_filename = self.read_format(fp, "LONG")
        self.filename = self.read_string(fp, 128)
        self.header_size = self.read_format(fp, "LONG")

    def _read_simple_time_data(self, fp):
        """
        Read the simple time section

        Parameters
        ----------
        fp : object file
            Pointer to the current file buffer
        """
        self.file_id = self.read_format(fp, "LONG")
        self.section_id = self.read_format(fp, "LONG")
        self.no_of_frames = self.read_format(fp, "ULONG")
        self.frame_start = self.read_format(fp, "ULONG")
        self.start_data_time = self.read_format(fp, "LONG")
        self.stop_dataT_time = self.read_format(fp, "LONG")
        self.sample_rate = self.read_format(fp, "DOUBLE")
        self.store_frame = self.read_format(fp, "ULONG")
        self.time_low = self.read_format(fp, "ULONG")
        self.time_high = self.read_format(fp, "ULONG")
