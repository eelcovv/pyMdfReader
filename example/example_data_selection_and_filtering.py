import funcy
import matplotlib.pyplot as plt
from signal_filters.filters import filter_signal

import mdf_reader.mdf_parser as mdf

data_file = "../data/AMS_BALDER_160927T143000.mdf"

mdf_obj = mdf.MDFParser(data_file, set_relative_time_column=True, import_data=False)

# This is the way the make a selectio of all acceleration channels
# The first regular expression in the list applies on the name field of the record.
# The next regular expressions on the label fields.
# First select all names
reg_ex_list_acc = [
    r"BALDER_+UI\d_A(\d+)_VI1",
    r"(.*) - A([XYZ])\s*-\s*(\d+)",
    r"(.*) - ACC\s( \d+)\s*-\s*A([XYZ])",
]
reg_ex_mru_list = [
    "\bMRU_Heave\b|\bMRU_Pitch\b|\bMRU_Roll\b|\bMRU_Sway\b|\bMRU_Surge\b"
    "|\bMRU_Heading\b"
]
reg_ex_sg_list = [r"BALDER__UI\d_A(\d+)_VI1", r"(.*) - SG (\d+)"]

mdf_obj.set_column_selection(reg_ex_list_acc[:2])
mdf_obj.import_data()
mdf_obj.make_report(show_loaded_data_only=True)

mdf_data = mdf_obj.data
mdf_data.set_index("time_r", inplace=True, drop=True)
mdf_data.index.name = "Time [s]"
mdf_data.info()

delta_t = mdf_data.index[1] - mdf_data.index[0]
f_s = 1.0 / delta_t

fc_low = 0.0033
fc_hig = 0.25

filter_types = [
    "butterworth",
    "kaiser",
]

plt.ion()
for filter_type in filter_types:
    for col_name in mdf_data.columns.values[:1]:
        signal = mdf_data[col_name]
        print("start filtering {} {}".format(filter_type, col_name))
        with funcy.print_durations("{} : {}".format(filter_type, col_name)):
            mdf_d_f = filter_signal(
                signal=signal.values,
                filter_type=filter_type,
                f_cut_low=fc_low,
                f_cut_high=fc_hig,
                f_sampling=f_s,
                f_width_edge=0.05,
                order=3,
            )
            col_name_f = "_".join([col_name, filter_type, "f"])
            col_name_m = "_".join([col_name, filter_type, "m"])
            mdf_data[col_name_f] = mdf_d_f
            mdf_data[col_name_m] = signal - signal.mean()
        ax = mdf_data.plot(y=col_name_m)
        ax = mdf_data.plot(y=col_name_f, ax=ax)
plt.ioff()
plt.show()
