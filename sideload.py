import os
import sys
import shutil
import struct
import configparser
from io import StringIO


def rm_f(path):
    try:
        os.remove(path)
    except OSError:
        pass


adf_template = struct.pack("<I 2052s 4120s I 144s I 20580s I I 12s I 52s I 832s I 260s I 2312s",
    1, b"http://example.com", b"http://example.com", 0xDEADBEEF, b"", 1, b"", 1, 0x31, b"", 0x31, b"", 2, b"", 0xFFFFFFFF, b"", 0x01000000, b"")


def patch_jam(jam, jar_len):
    config = configparser.ConfigParser()
    config.optionxform = str

    try:
        config.read_string("[jam]\r\n" + jam.decode("shift-jis"))
    except UnicodeDecodeError:
        print("WARN: can't patch jam due to UnicodeDecodeError")
        return jam

    config["jam"]["AppSize"] = str(jar_len)
    config["jam"]["TargetDevice"] = "P01F"

    config_string = StringIO()
    config.write(config_string)

    return config_string.getvalue()[6:].replace("\r\n", "\n").replace("\n", "\r\n").encode("shift-jis")


def main():
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    jar_path = sp_path = jam_path = sdf_path = None

    for fname in os.listdir(input_dir):
        if fname.endswith(".jar"):
            jar_path = fname
        elif fname.endswith(".sp"):
            sp_path = fname
        elif fname.endswith(".jam"):
            jam_path = fname
        elif fname.endswith(".sdf"):
            sdf_path = fname

    if jar_path is None:
        raise RuntimeError("can't find jar")
    elif jam_path is None:
        raise RuntimeError("can't find jam")

    if sp_path is not None:
        with open(os.path.join(input_dir, sp_path), "rb") as inf:
            sp = inf.read()

    with open(os.path.join(input_dir, jam_path), "rb") as inf:
        jam = inf.read()

    jam = patch_jam(jam, os.path.getsize(os.path.join(input_dir, jar_path)))
    adf = bytearray(adf_template + jam)
    adf[0x1820:0x1824] = struct.pack("<I", len(jam))

    target = None

    for x in range(512):
        if not os.path.exists(os.path.join(output_dir, str(x))):
            target = x
            break

    if target is None:
        raise RuntimeError("no target folder")

    output_path = os.path.join(output_dir, str(target))

    os.mkdir(output_path)
    with open(os.path.join(output_path, "adf"), "wb") as outf:
        outf.write(adf)
    if sp_path is not None:
        with open(os.path.join(output_path, "sp"), "wb") as outf:
            outf.write(sp[0x40:])
    shutil.copyfile(os.path.join(input_dir, jar_path), os.path.join(output_path, "jar"))
    if sdf_path is not None:
        shutil.copyfile(os.path.join(input_dir, sdf_path), os.path.join(output_path, "sdf"))

    for filename in ["Entry", "JavaAdl", "JavaSys", "PushSms"]:
        rm_f(os.path.join(output_dir, filename))

    print("{} => {}".format(input_dir, output_path))


if __name__ == "__main__":
    main()
