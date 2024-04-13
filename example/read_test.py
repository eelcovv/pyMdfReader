"""
Small example on how to read an mdf file. The simplest way would just be

mdf_object = mdf.MDFParser(file_name)

the mdf_object will carry all the information of the mdf file. The actual data is stored
in a Pandas dataframe which can be assessed with mdf_object.data

In this example, it is, however, demonstrated to read just a selection of data columns,
which will speed up the reading time significantly. The idea is to first read the header
only a mdf_header object with the call

mdf_header = mdf.MDFParser(file_name, import_data=False)

Then we have information on all the data columns which are available. Based on the
'include_columns' and 'exclude_columns', we can make a selection of columns we want to
read, which is done with the second call to the MDFParser

@author: Eelco van Vliet


"""

import logging

import matplotlib.pyplot as plt

import mdf_reader.mdf_parser as mdf

logging.basicConfig(level=logging.INFO)


def print_title(title):
    print("-" * 40)
    print(title)
    print("-" * 40)


file_name = "../data/AMS_BALDER_110225T233000_UTC222959.mdf"

# first read the header dat only to get the column names
header_object = mdf.MDFParser(
    file_name, import_data=False, set_relative_time_column=True
)

header_object.make_report()

# You can select the columns cumulative.
# The include_data_time only needs to be given one time
header_object.set_column_selection(filter_list=["MRU_Roll"], include_date_time=True)
header_object.import_data()
print(header_object.data.head(5))
header_object.set_column_selection(filter_list=["^BALDER", "HZ3.*A[XYZ]"])
header_object.import_data()
print(header_object.data.head(5))

# Note that you can also automatically calculate the relative time in s wrt the start if
# the *set_relative_time_column* flag is set to true.
# In that case, a column with the name *time_r* is created which holds the relative time
# Alternatively you can make your own choice of columns. We will import again
header_object = mdf.MDFParser(file_name, import_data=False)

# create a list of columns to import
columns_to_include = []
columns_to_exclude = []

# Here, you can control how to read the columns. If max_columns = None, read the named
# selection. If a number is given, read the columns in order they occur, starting
# at the 'start_col' index and stopping as soon as max_columns is exceeded
max_columns = None
start_col = 0

if max_columns is None:
    name_list, label_list, group_list = header_object.set_column_selection(
        filter_list=["GPS_L.*|MRU_Roll|DateTime.*"]
    )
    columns_to_include = header_object.include_columns
    print("name list: {}".format(name_list))
    print("label list: {}".format(label_list))
    print("group list: {}".format(group_list))
else:
    # In this section, we just add all columns to include in order they appear up to a
    # maximum number of columns
    n_col = 0
    for cnt, obj in enumerate(header_object.dataset_records):
        if n_col < max_columns and cnt > start_col:
            columns_to_include.append(obj.name)
            n_col += 1

print(columns_to_include)
# now do the actual import
mdf_object = mdf.MDFParser(
    file_name, verbose=1, include_columns=columns_to_include, import_data=True
)

# mdf_object.data.info()
mdf_object.make_report(show_loaded_data_only=True)

try:
    # Plot one of the columns. Works only if this column was actually imported.
    # Otherwise, skip the plot
    mdf_object.data.plot(y="MRU_Roll")
except KeyError:
    print("Not plotting the key, not loaded")
else:
    plt.ioff()
    plt.show()
