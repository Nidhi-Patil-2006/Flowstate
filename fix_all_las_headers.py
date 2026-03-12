import os
import laspy

raw_folder = "data/raw"

print("Scanning LAS files...")

for file in os.listdir(raw_folder):

    # make extension check case-insensitive
    if file.lower().endswith(".las") or file.lower().endswith(".laz"):

        input_path = os.path.join(raw_folder, file)

        # create new file name
        name, ext = os.path.splitext(file)
        output_path = os.path.join(raw_folder, name + "_fixed" + ext)

        try:
            print("\nProcessing:", file)

            las = laspy.read(input_path)

            # remove problematic CRS encoding
            las.header.global_encoding.value = 0

            las.write(output_path)

            print("Saved:", output_path)

        except Exception as e:
            print("Skipped:", file)
            print("Reason:", e)

print("\nFinished fixing LAS files.")