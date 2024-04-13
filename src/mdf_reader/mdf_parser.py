"""
A module for reading microlab MDF file.
Usage

import mdf_parser.mdf_parser as mdf

mdf_object = mdf.MDFParser(file_name)

Author: Eelco van Vliet
29-2-2015
"""

__author__ = "Eelco van Vliet"
__copyright__ = "Eelco van Vliet"
__license__ = "MIT"

import argparse
import logging
import struct
import sys
from builtins import object, range
from os.path import getsize, join, split, splitext
from re import IGNORECASE, compile, match, search, sub
from sys import version_info

import numpy as np
import pandas as pd

from . import __version__
from .mdf_blocks import DataSetRecord, MDHFileHeader, set_logging_level

PythonVersion = version_info[0]

logging.basicConfig(format="%(message)s", level=logging.INFO)

_logger = logging.getLogger(__name__)

MDF_EXTENSION = ".mdf"


def decode_ymdhms(ymdhms):
    """The year month day hour minute seconds are stored in the 4-byte integer

    Parameters
    ----------
    ymdhms : int
        A 4-byte integer containing the date time according to the MTF manual

    Returns
    -------
    type
        The ISO Data time string

    """
    ymdhms = int(ymdhms)
    year = np.right_shift(ymdhms & 0b11111100000000000000000000000000, 26) + 1980
    months = np.right_shift(ymdhms & 0b00000011110000000000000000000000, 22)
    days = np.right_shift(ymdhms & 0b00000000001111100000000000000000, 17)
    hours = np.right_shift(ymdhms & 0b00000000000000011111000000000000, 12)
    minutes = np.right_shift(ymdhms & 0b00000000000000000000111111000000, 6)
    seconds = np.right_shift(ymdhms & 0b00000000000000000000000000111111, 0)

    return year, months, days, hours, minutes, seconds


def convert_ymdhms_to_data_time(ymdhrs_array, sample_rate=1, constant_sample_rate=True):
    """Convert the binary year month day hour minutes seconds representation into a
    readable data/time string

    Parameters
    ----------
    ymdhrs_array : binary
        array with the ymdhrs datatime integers
    sample_rate : float, optional
        the sampling rate of the signal (Default value = 1)
    constant_sample_rate : bool, optional
        If True assume that the sample read is leading (Default value = True)

    Returns
    -------
    type
        DateTime pandas index array

    Notes
    -----
    In the first version of the script, the ymdhrs was taken as leading and the number
    of samples per seconds we corrected to take care of missing samples or too many
    samples in a second.
    It appears that the sample rate is really constant and that the clock time may vary.
    Setting this flag true takes the sample rate leading
    """

    # initialise some variables
    number_of_samples = ymdhrs_array.shape[0]
    delta_t_ms = int(1000.0 / sample_rate)

    # create an empty datetime64 array
    date_time_array = np.empty(number_of_samples, dtype="datetime64[ms]")

    # the date time format string: YYYY-MM-DDThh:mm:ss.msec
    dts_format = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:03d}"

    if constant_sample_rate:
        # This routine return the date time based on the assumption the the sample rate
        # is leading and constant

        # get the start time first
        (year, month, day, hour, minutes, seconds) = decode_ymdhms(ymdhrs_array[0])

        start_date_time = np.datetime64(
            dts_format.format(year, month, day, hour, minutes, seconds, 0), "ms"
        )
        end_date_time = start_date_time + np.timedelta64(
            delta_t_ms * number_of_samples, "ms"
        )

        date_time_array = np.arange(start_date_time, end_date_time, step=delta_t_ms)

    else:
        # This routine assumes that the ymdhrs is leading and exact and that the sample
        # rate is not constant. This means that the number of samples per second can
        # slightly vary. In this routine, samples are removed and added such that the
        # ymdhrs is correct. This routine may not be needed as it appears that in fact,
        # the sampling rate is very constant and the PC clock is not.
        # To use the 'constant_sample_rate' by default, initialize the milliseconds on
        # 0; the ymdhrs integer does not hold milliseconds, we get it our by counting
        ms = 0
        ms_prev = None
        old_sec = None
        i_first_change = None  # Keep the index where the seconds changed
        cnt_per_sec = 0
        cnt_list = list()
        sec_step = 0
        for i in range(number_of_samples):

            # convert the ymdhrs 4-byte integer into readable integers for each item
            (year, month, day, hour, minutes, seconds) = decode_ymdhms(ymdhrs_array[i])

            # update the milliseconds-counter if the seconds increase
            if old_sec is not None and ((old_sec < seconds) or (sec_step == -59)):
                # set the milliseconds to zero again
                ms = 0
                cnt_list.append(cnt_per_sec)
                cnt_per_sec = 0
                if i_first_change is None:
                    # Store the position where we change for the first time to a new
                    # second
                    i_first_change = i
            else:
                # increase the milliseconds with the time step in milliseconds
                ms += delta_t_ms

            # correct the milliseconds if too many samples occurred
            if ms_prev is not None and ms >= 1000:
                # Add a small time-step when we get closer to the 1000.
                ms = ms_prev + (1000 - ms_prev) / 2.0

            # create a data time string and store it in the datetime64 numpy array
            date_time_array[i] = dts_format.format(
                year, month, day, hour, minutes, seconds, ms
            )

            cnt_per_sec += 1
            if old_sec is not None:
                # This is to monitor when we step back from 59 s to 0 s at the
                # minute/hour change
                sec_step = seconds - old_sec
            old_sec = seconds
            ms_prev = ms

        # Correct for the first i_first_change sample as the ms may not have started at
        # 0 as we assumed
        date_time_array[:i_first_change] += np.timedelta64(
            delta_t_ms * (int(sample_rate) - i_first_change - 1), "ms"
        )

    return pd.DatetimeIndex(date_time_array)


class MDFParser(object):
    """
    The MDFParser class contains methods for reading mdf files.

    Parameters
    ----------
    mdf_file : str
        Path to a binary the follows MDF 3.3 specification

    import_data: bool , optional
        Flag to enable to import the data, default = True. If False, only the header
        information is read.

    include_columns : list
        List with columns to import. Default value = []. If empty, all columns are
        included

    exclude_columns: list
        List with colums to exclude. Default value =[]. If empty, none are excluded

    verbose: int
        Set the logging level. Obsolete
        0. Silent
        1. Normal info
        2. Debugging

    convert_datetime: int, optional
        Translate the ymdhms integer into a data time string

    resample_data: bool, optional, False
        The sampled data is not completely uniformly sampled. To enforce an equidistant
        sampling, set this flag to true

    constant_sample_rate: bool, optional
        If true, use the sample rate for the clock, otherwise, the ymdhms is leading.
        Defaults to *True*

    replace_record_names : dict, optional
        A dictionary with records names which we want to replace from A1 to B1

    date_time_label : str, optional
        Default label to assign to the Date time string. Default = "DateTime"

    date_time_match_string : str, optional
        The date time column is selected based on this match string.
        Default = "_DateTime32"

    load_date_time: bool, optional
        Always read the date time information channel, even if it is not explicitly
        mentioned in the filter list. Defaults to *True*

    set_relative_time_column: bool, optional
        If true, create a column *time_r* in seconds with the relative time starting at
        t=0 s. Defaults to *False*

    Examples
    --------

    Reading an MDF file is done by creating a MDFParser object with a file_name as first
    argument.

    >>> file_name = "../data/AMS_BALDER_110225T233000_UTC222959.mdf"
    >>> header_object = MDFParser(mdf_file=file_name, import_data=False)
    >>> names = header_object.make_report()

    If the *import_data* flag would have been set to *True*, the *header_object* class
    would have been created and all MDF data would be put in a data frame
    *header_object.data*.
    In this example, however, we only read the header information of the MDF file first.
    As a next step, we can make a selection of the data columns we want to import.
    In this way the reading time of an MDF data file can be reduced significantly as
    only the selected data needs to be imported.
    The data available in the mdf file can be explored by using the  *make_report()*
    method. which writes all channels to screen. Now, we are going to select the
    MRU_Roll data first.

    >>> from tabulate import tabulate
    >>> names_labels_and_groups = header_object.set_column_selection(
    ...     filter_list=["MRU_Roll"], include_date_time=True)
    >>> header_object.import_data()
    >>> print(tabulate(header_object.data.head(5), headers="keys", tablefmt="psql"))
    +----------------------------+------------+
    | DateTime                   |   MRU_Roll |
    |----------------------------+------------|
    | 2011-02-25 23:30:00        |    0.01207 |
    | 2011-02-25 23:30:00.040000 |    0.01207 |
    | 2011-02-25 23:30:00.080000 |    0.01207 |
    | 2011-02-25 23:30:00.120000 |    0.01204 |
    | 2011-02-25 23:30:00.160000 |    0.01204 |
    +----------------------------+------------+

    The *names_labels_and_groups* now contains 3 lists, but we don't use it now.
    For more information about the return values, look at the docstring of the
    *set_column_selection* method.

    Because we have added the *include_date_time* flag, the DataTime column is read by
    default and set as the index of the DataFrame. You can do this multiple times if
    you want to add more columns.
    The *include_data_time* does not have to be given again as we already have imported
    the DateTime.
    So let's import the MRU Roll Pitch Heave channels as well. We do this with a regular
    expression matching all the channels names starting with MRU_R, MRU_P, or MRU_H

    >>> names_labels_and_groups = header_object.set_column_selection(
    ...    filter_list=["MRU_[RPH]"])
    >>> header_object.import_data()
    >>> print(tabulate(header_object.data.head(5), headers="keys", tablefmt="psql"))
    +----------------------------+------------+-------------+-------------+
    | DateTime                   |   MRU_Roll |   MRU_Heave |   MRU_Pitch |
    |----------------------------+------------+-------------+-------------|
    | 2011-02-25 23:30:00        |    0.01207 |     -0.1051 |  -0.0001869 |
    | 2011-02-25 23:30:00.040000 |    0.01207 |     -0.1051 |  -0.0001869 |
    | 2011-02-25 23:30:00.080000 |    0.01207 |     -0.1051 |  -0.0001869 |
    | 2011-02-25 23:30:00.120000 |    0.01204 |     -0.1078 |  -0.0002593 |
    | 2011-02-25 23:30:00.160000 |    0.01204 |     -0.1078 |  -0.0002593 |
    +----------------------------+------------+-------------+-------------+

    Since all data is stored in the Pandas Dataframe *header_object.data* we can plot
    the data using all Pandas/matplotlib plotting capabilities.
    This is demonstrated in the example notebook.

    """

    def __init__(
        self,
        mdf_file,
        import_data=True,
        include_columns=None,
        exclude_columns=None,
        verbose=1,
        convert_datetime=True,
        resample_data=False,
        constant_sample_rate=True,
        replace_record_names=dict(),
        log_level=logging.WARNING,
        date_time_label="DateTime",
        date_time_match_string=r"^_DateTime32$",
        load_date_time=True,
        set_relative_time_column=False,
        include_date_time=False,
    ):

        self.include_columns = include_columns
        self.exclude_columns = exclude_columns
        self.convert_datetime = convert_datetime
        self.resample_data = resample_data
        self.constant_sample_rate = constant_sample_rate
        self.verbose = verbose
        self.replace_record_names = replace_record_names

        self.date_time_label = date_time_label
        self.date_time_match_string = date_time_match_string
        self.load_date_time = load_date_time
        self.include_date_time = include_date_time
        self.set_relative_time_column = set_relative_time_column
        if self.set_relative_time_column:
            # If we want to set a relative data time column, the include date time
            # must be set
            self.include_date_time = True

        # set the logger and update the level if you want to debug
        self.log = logging.getLogger(__name__)
        self.log.setLevel(log_level)

        self.header = None
        self.data = None  # This Pandas dataframe will contain all the data at the end

        mdf_file_base, extension = splitext(mdf_file)
        if not bool(match(MDF_EXTENSION, extension, IGNORECASE)):
            raise ImportError("file name should be of type {}".format(MDF_EXTENSION))

        self.mdf_path_to_file = split(mdf_file_base)[0]
        self.dta_filename = None

        # initialise some attributes
        self.dataset_records = []
        # dictionary to hold the index belong to each record name
        self.dataset_records_index = dict()
        self.filename_record = None
        self.time_record = None
        self.data = None

        # import the mdf header
        self.log.debug("Starting reading mdf_file header")
        self.import_header(mdf_file)

        if self.include_date_time:
            # To prevent problems later, just put the date time column in the include
            # list
            self.set_column_selection([self.date_time_match_string])

        # only import the data if import_data was set true
        if import_data:
            self.log.debug("Starting reading dta data ")
            self.import_data()

    def import_header(self, mdf_file):
        """Read the header data from the mdf file

        Parameters
        ----------
        mdf_file :
            the name of the mdf header file

        Returns
        -------
        type
            nothing

        """
        self.log.debug("Reading header file {}".format(mdf_file))
        with open(mdf_file, "rb") as fp_mdf:
            # read the header of the MDF file
            self.header = MDHFileHeader(fp_mdf)

            # keep looping over the data set records and read them all
            block_read = True
            while block_read:
                try:
                    self.log.debug(
                        "Reading Dataset record no {}".format(len(self.dataset_records))
                    )
                    record = DataSetRecord(fp_mdf, self.verbose)
                    self.log.debug(
                        "Found record type {};  size {}; version {}"
                        "".format(record.type, record.size, record.version)
                    )
                    # A hack which allows to replace a name of a record into a new name.
                    # Required to change the typo in the MDF file by Marin from Pitch to
                    # Pitch, so I do not have to take care of that later
                    try:
                        # Try to replace the name of the record if it is given in the
                        # dictionary
                        record.name = sub(
                            record.name,
                            self.replace_record_names[record.name],
                            record.name,
                        )
                    except (KeyError, AttributeError, TypeError):
                        # Failed to replace the name, so keep the original
                        pass

                    if record.type == 1:
                        self.filename_record = record
                    elif record.type == 2:
                        self.time_record = record
                    else:
                        self.log.debug(
                            "Store Data record {} in a list".format(record.name)
                        )
                        self.dataset_records.append(record)
                        self.dataset_records_index[record.name] = (
                            len(self.dataset_records) - 1
                        )
                except struct.error:
                    self.log.debug(
                        "Found {} data set records in MDF file"
                        "".format(len(self.dataset_records))
                    )
                    block_read = False

            self.log.debug("Finalised while loop in scanning header blocks")

    def import_data(self, set_relative_time_column=None):
        """
        Import the binary data from the dta file

        Parameters
        ----------
        set_relative_time_column: bool or None, optional
            If true, store the relative time in the time_r column. Default is None,
            which means that the value as stored during initialization of the class is
            taken. This is *False* by default, but can also be passed through the
            constructor arguments.
        """

        self.log = logging.getLogger(__name__)
        set_logging_level(self.log, self.verbose)

        if set_relative_time_column is not None:
            # only if the argument is explicitly passed, we can overrule the value
            self.set_relative_time_column = set_relative_time_column

        self.dta_filename = join(self.mdf_path_to_file, self.filename_record.filename)
        file_size = getsize(self.dta_filename)
        n_frames_to_read = int(file_size / self.header.frame_size)

        self.log.debug(
            "Reading {} frames from {}".format(n_frames_to_read, self.dta_filename)
        )
        with open(self.dta_filename, "rb") as fp_dta:
            byte_array = fp_dta.read(n_frames_to_read * self.header.frame_size)

        # create a pandas data frame and a numpy data array to store the current data
        if self.data is None:
            self.data = pd.DataFrame(index=list(range(n_frames_to_read)), columns=[])

        # Loop over all the data sets records and convert them from the binary array and
        # put them in the dataframe
        for index, record in enumerate(self.dataset_records):
            # Check if we want to skip the column based on the include_columns and
            # exclude_columns lists
            if (
                self.include_columns is not None
                and record.name not in self.include_columns
            ):
                continue
            if self.exclude_columns is not None and record.name in self.exclude_columns:
                continue

            # ok, we can proceed.
            self.log.debug(
                "Decoding data set nr {} : {}/{}  (format {})"
                "".format(index, record.name, record.label, record.data_format)
            )

            # create an empty numpy array to store the converted data
            np_data = np.empty(n_frames_to_read, record.data_format_numpy)

            # loop over the data frames and convert the values of the current record
            for i in range(n_frames_to_read):
                ptr = record.frame_offset + i * self.header.frame_size
                value = record.unpack_byte_array(
                    byte_array[ptr : ptr + record.data_format_size], record.data_format
                )
                np_data[i] = value
                self.log.debug(
                    "Assigned {} -> {} ({} -> {})"
                    "".format(value, np_data[i], type(value), type(np_data[i]))
                )

            # copy the numpy array in the Pandas data frame
            if record.data_format == "ymdhms" and self.convert_datetime:
                # convert the ymdhms integer into a datatime-index.
                self.data[record.name] = convert_ymdhms_to_data_time(
                    np_data,
                    self.time_record.sample_rate,
                    constant_sample_rate=self.constant_sample_rate,
                )
                new_columns = self.data.columns.values
                index_of_column = None
                for ii, name in enumerate(new_columns):
                    if name == record.name:
                        index_of_column = ii

                if index_of_column is not None:
                    new_columns[index_of_column] = self.date_time_label
                self.data.columns = new_columns
                record.name = self.date_time_label

                # set the date time index as the index of the data frame
                self.data.set_index(record.name, inplace=True)
            else:
                # Copy the current data array to the data frame
                self.log.debug(
                    "Copying data of type {} to {}".format(type(np_data), record.name)
                )
                try:
                    self.data[record.name] = np_data
                except (TypeError, KeyError):
                    self.log.warning(
                        "Failed to copy data for {} due to KeyError. Skipping this "
                        "column".format(record.name)
                    )
                    continue

            record.loaded_data = True

        if self.convert_datetime and self.resample_data:
            # resampling is only required if the
            delta_time = int(1000.0 / self.time_record.sample_rate)
            self.log.debug("Resampling the data set with dt = {}".format(delta_time))

            # Resample get a parameter of the sampling frequency in ms as a
            # string-argument.
            # The resampled result needs to be passed to interpolate to fill the gaps
            self.data = self.data.resample("{}ms".format(delta_time)).interpolate()

        if self.set_relative_time_column:
            # set the relative time in a separate column
            self.data["time_r"] = (self.data.index - self.data.index[0]) / pd.Timedelta(
                1, "s"
            )

    def set_column_selection(
        self, filter_list, set_on_exclude_list=False, include_date_time=None
    ):
        """Select the data to import based on a list of regular expressions

        Parameters
        ----------
        filter_list : list
            A list with regular expression in which the first filter is always applied
            on the name field and the next filters are all applied to the label field
            of the record.
        set_on_exclude_list : bool, optional
            By default, the selected columns are added to the include list.
            If this value is true, set the selection on the excluded list.
            Defaults to False
        include_date_time: bool, optional
            Include the date time field by default (without specification in the
            *filter_list*).
            Handy for the examples as you don't have to specify the DateTime explicitly.
            Defaults to None, implying that the setting is taken from the constructor
            and is set to *False*.

        Returns
        -------
        tuple (name_list, label_list, group_list)
            Selection of name columns along with a list of the () group selection

        Notes
        -----
        The data reader allows passing a list of exclude_columns and include_columns by
        which you can select which column is actually read. With the routine, lists can
        be created by a regular expression filter

        """

        if include_date_time is not None:
            # we can overrule the include date time
            self.include_date_time = include_date_time

        # Create the regular expression belong to the name and labels.
        # For the labels, multiple regular expression can be defined.
        # Note that filtering takes place based on the name field and label fields of
        # the record.
        # The name field only has one item, whereas the label fields can have multiple
        # items. Tol select a record, define a reg exp for first the name field, and
        # then the multiple labels field if required.
        regular_expression_labels = list()
        regular_expression_names = None
        for index, reg_filter in enumerate(filter_list):
            if index == 0:
                # The first in the list is always the filter applied on the name field
                # of the record
                if (
                    self.load_date_time
                    and self.include_date_time
                    and not bool(search(self.date_time_match_string, reg_filter))
                ):
                    # if the date time label is not present yet in the filter
                    reg_filter += "|{}".format(self.date_time_match_string)
                regular_expression = compile(reg_filter)
                self.log.debug("Filtering on name with {}".format(reg_filter))
                regular_expression_names = regular_expression
            else:
                # The remaining of the filter all apply on the label field of the record
                self.log.debug("Filtering on label with {}".format(reg_filter))
                regular_expression = compile(reg_filter)
                regular_expression_labels.append(regular_expression)

        name_list = []
        label_list = []
        group_lists = []
        if not regular_expression_labels:
            # In case no second filter is given (ie no filter for the label fields), set
            # it to fit everything with .*
            regular_expression_labels.append(compile(".*"))

        for record in self.dataset_records:
            # first check if the name field matches the namefield regular expression
            date_time_match = match(self.date_time_match_string, record.name)
            if bool(regular_expression_names.search(record.name)) or (
                date_time_match and self.include_date_time
            ):
                if record.name in name_list:
                    # We have this record already in the list. Continue to the next
                    continue
                # It matches, now check if the label fields match the label field
                # regular expression by looping
                self.log.debug("Checking = {} ".format(record.name))
                for reg_exp in regular_expression_labels:
                    label_match = reg_exp.search(record.label)
                    if bool(label_match):
                        # This label match the regular expression, to add this record to
                        # the name list
                        self.log.debug(
                            "Found match name = {} label = {}"
                            "".format(record.name, record.label)
                        )
                        name_list.append(record.name)
                        label_list.append(record.label)
                        group_number = 1
                        groups = []
                        while group_number:
                            # A regular expression stores all patterns in between () in
                            # a group.
                            # These patterns are here stored in the group list such that
                            # it can be used later if needed
                            try:
                                groups.append(label_match.group(group_number))
                                group_number += 1
                            except (IndexError, AttributeError):
                                # No () were used in the regular expression to no groups
                                # need to be stored
                                group_number = 0
                        # the group list eventually contains a list of lists with stored
                        # matches per label
                        group_lists.append(groups)

        # The lists of names created by this routine are normally stored in the
        # include_list, such that all matches are imported.
        # You can also specify it to be excluded by the set_on_exclude_list flag
        def append_missing_name(column_list, names):
            if column_list is None:
                column_list = names
            else:
                for name in names:
                    if name not in column_list:
                        column_list.append(name)
            return column_list

        if set_on_exclude_list:
            self.exclude_columns = append_missing_name(self.exclude_columns, name_list)
        else:
            self.include_columns = append_missing_name(self.include_columns, name_list)

        return name_list, label_list, group_lists

    def make_report(self, show_loaded_data_only=False):
        """
        Make a report of the records available in the mdf file

        Parameters
        ----------
        show_loaded_data_only: bool, optional
            If True, only show the data columns that have been loaded. Default = False,
            which means that all channels are shown

        Returns
        -------
        list
            List of the reported columns. We can use this list to obtain the channel
            name by the index

        """
        self.log.setLevel(logging.INFO)
        msg1 = "{:3s} {:5s} {:6s} : {:50s} : {}"
        msg2 = "{:3d} {:5d} {:6d} : {:50s} : {}"
        self.log.info(msg1.format("cnt", "index", "Loaded", "Name", "Label"))
        self.log.info(msg1.format("-" * 3, "-" * 5, "-" * 6, "-" * 50, "-" * 30))
        cnt = 0
        loaded_data_list = list()
        for index, record in enumerate(self.dataset_records):
            if show_loaded_data_only and not record.loaded_data:
                # Skip if not loaded this data and the show loaded_data_only flag is
                # True
                continue
            self.log.info(
                msg2.format(cnt, index, record.loaded_data, record.name, record.label)
            )
            cnt += 1
            loaded_data_list.append(record.name)

        return loaded_data_list


def parse_args(args):
    """Parse command line parameters

    Parameters
    ----------
    args : list
        Command line parameters as a list of strings

    Returns
    -------
    :obj:`argparse.Namespace`
        command line parameters
    """

    parser = argparse.ArgumentParser(description="A tool to read mdf fils")
    parser.add_argument(
        "--version",
        action="version",
        version="mdf_reader {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)


def main(args):
    """
    The main routine for testing purpose

    Parameters
    ----------
    args : list
        Command line arguments

    """
    args = parse_args(args)
    logging.basicConfig(level=args.loglevel, stream=sys.stdout)
    _logger.debug("Writing pickling data to tests directory...")
    _logger.info("Script ends here")


def run():
    """ """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
