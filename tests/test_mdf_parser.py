# -*- coding: utf-8 -*-

import os
import pickle

from numpy.testing import assert_equal

import mdf_reader.mdf_parser as mdf

__author__ = "Eelco van Vliet"
__license__ = "none"

DATA_DIR = "data"
FILE_NAMES = ["AMS_BALDER_110225T233000_UTC222959.mdf", "BARGE_150409T145810.mdf"]


def write_header():
    """
    Read the header of the mdf data file and store it to a pickle file.
    In this routine, we need to explicitly set the path to the data as it is assumed
    that this routine is called from the main.
    """
    # define the data location with respect to the location of the test file
    data_location = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..", DATA_DIR)
    )
    for cnt, file_name in enumerate(FILE_NAMES):
        print("Reading {} from {}".format(file_name, data_location))
        header_object = mdf.MDFParser(
            os.path.join(data_location, file_name), verbose=1, import_data=False
        )

        test_file = os.path.splitext(file_name)[0] + ".pkl"
        print(
            "Writing header object to {}".format(
                os.path.join(os.path.dirname(__file__), test_file)
            )
        )
        with open(
            os.path.join(os.path.dirname(__file__), test_file), "wb"
        ) as out_stream:
            pickle.dump(
                header_object.dataset_records_index, out_stream, pickle.HIGHEST_PROTOCOL
            )


def test_header():
    # Test the reading of the header.
    # Since we run this as a test, we do not need to set the path to the data directory
    # as it is available already
    for file_name in FILE_NAMES:
        try:
            mdf_header = mdf.MDFParser(
                os.path.join(DATA_DIR, file_name), import_data=False
            )
        except FileNotFoundError:
            mdf_header = mdf.MDFParser(
                os.path.join("..", DATA_DIR, file_name), import_data=False
            )

        test_file = os.path.splitext(file_name)[0] + ".pkl"
        if not os.path.exists(test_file):
            test_file = os.path.join("tests", test_file)

        # read the pick file to compare if the data is correct
        with open(test_file, "rb") as in_stream:
            dataset_record_index = pickle.load(in_stream)
        assert_equal(mdf_header.dataset_records_index, dataset_record_index)


def test_data():
    """
    test importing of all data
    """
    for file_name in FILE_NAMES:
        try:
            mdf.MDFParser(os.path.join(DATA_DIR, file_name), import_data=True)
        except FileNotFoundError:
            mdf.MDFParser(os.path.join("..", DATA_DIR, file_name), import_data=True)


def test_data_selection():
    """
    test importing a selection of the data using a list of regular expression
    """
    for file_name in FILE_NAMES:

        try:
            mdf_header = mdf.MDFParser(
                os.path.join(DATA_DIR, file_name), import_data=False
            )
        except FileNotFoundError:
            mdf_header = mdf.MDFParser(
                os.path.join("..", DATA_DIR, file_name), import_data=False
            )
        mdf_header.set_column_selection(
            filter_list=["BALDER", "A[XYZ]", "Latitude", "Longitude", "^S_"],
            include_date_time=True,
        )
        mdf_header.import_data()


def main():
    write_header()


if __name__ == "__main__":
    # In case we run the test_mdf_parser as a script from the command line like
    # python.exe tests/test_mdf_parser.
    # We call the main routine which will call the routine to create the pkl data from
    # the header.
    # This pickle data is used later by the 'test_header' unit test to see if we read
    # the header correctly
    main()
