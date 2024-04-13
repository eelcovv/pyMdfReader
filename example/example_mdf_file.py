from mlab_mdfreader import mdf_parser as mdf

data_file = "../data/AMS_BALDER_160927T143000.mdf"

print("With relative  time included")
# example reading a column with relative time, which implies data time is true
mdf_obj = mdf.MDFParser(data_file, set_relative_time_column=True, import_data=False)
mdf_obj.set_column_selection(["MRU_Roll$"])
mdf_obj.import_data()
mdf_obj.make_report(show_loaded_data_only=True)
print(mdf_obj.data.head())

# example reading a column without date time
print("Without Date time included")
mdf_obj = mdf.MDFParser(data_file, include_date_time=False, import_data=False)
mdf_obj.set_column_selection(["MRU_Roll$"])
mdf_obj.import_data()
mdf_obj.make_report(show_loaded_data_only=True)
print(mdf_obj.data.head())


print("With Date time included")
# example reading a column with date time
mdf_obj = mdf.MDFParser(data_file, include_date_time=True, import_data=False)
mdf_obj.set_column_selection(["MRU_Roll$"])
mdf_obj.import_data()
mdf_obj.make_report(show_loaded_data_only=True)
print(mdf_obj.data.head())
