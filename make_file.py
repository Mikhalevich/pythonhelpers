#!/usr/bin/python

import sys
import time

WRITE_CHUNK_SIZE = 1 * 1024 * 1024


def generate_file(filename, size, data):
    data_size = len(data.decode("utf-8"))
    write_chunk = int(WRITE_CHUNK_SIZE / data_size) * data
    real_write_chunk_size = len(write_chunk)
    chunks_to_write = int(size / real_write_chunk_size)
    last_chunk_size = size - chunks_to_write * real_write_chunk_size

    with open(filename, "w") as file:
        for _ in range(chunks_to_write):
            file.write(write_chunk)
        file.write(write_chunk[:last_chunk_size])


def main():
    print("start...")

    if len(sys.argv) < 3:
        print("parameter mismatch: {0} {1} {2} {3}".format(__file__, "<filename>", "<size in mb>", "<data>"))
        return

    try:
        filename = sys.argv[1]
        size = int(sys.argv[2]) * 1024 * 1024
        data = sys.argv[3]
    except IndexError:
        data = "0"
    except ValueError as value_err:
        print(value_err)
        return

    start_time = time.time()
    generate_file(filename, size, data)
    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()
