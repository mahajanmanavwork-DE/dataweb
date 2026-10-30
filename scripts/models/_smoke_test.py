from scripts.models.dataframe import Dataframe

# Pick any file you have in your input folder
d = Dataframe.from_file(r"C:\Users\mahaj\Desktop\college-prac-2\input_files\data.csv")   # <-- change this

print("key:", d.key)
print("cols:", d.cols)
print("shape:", d.df.shape)
print("path:", d.path)

# Now load it back by key
d2 = Dataframe.load(d.key)
print("reload cols:", d2.cols)
print("reload shape:", d2.df.shape)