import os
import csv
import sys
import random
import string
from os import fdopen, remove
from glob import glob
from tempfile import mkstemp
from shutil import move, copymode


def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, delimiter=str("\t"), quotechar=str('"'), **kwargs)
    for row in csv_reader:
        yield [cell for cell in row]


def fix_file(target_path):
    if not target_path or not os.path.isfile(target_path):
        return
    basename = os.path.basename(target_path)
    parent_dir = os.path.dirname(os.path.dirname(target_path))
    source_path = os.path.join(parent_dir, 'en_tn', basename)
    book = basename.split("_")[2].split("-")[1].split(".")[0]

    fh, abs_path = mkstemp()
    with fdopen(fh, 'w') as new_file, open(target_path, encoding="utf-8") as target_file:
        lines = target_file.readlines()
        new_lines = []
        ids = []
        for line in lines:
            parts = line.split("\t")
            if len(parts) < 9:
                if parts[0] != book:
                    if len(parts) == 1 and len(new_lines) > 1:
                        line.replace("\t", "<br><br>")
                        new_lines[-1] = new_lines[-1].rstrip() + "<br><br>" + line
                else:
                    for i in range(len(parts), 9):
                        parts.insert(3, "")
                    new_lines.append("\t".join(parts))
            else:
                new_lines.append("\t".join(parts))
                if parts[3]:
                    ids.append(parts[3])
        for i, line in enumerate(new_lines):
            parts = line.split("\t")
            if not parts[3]:
                letters = string.ascii_lowercase + string.digits
                id = ''
                print(parts[0:4])
                while id not in ids:
                    id = ''.join(random.choice(letters) for i in range(4))
                    print(id)
                ids.append(id)
                parts[3] = id
            new_lines[i] = "\t".join(parts)
        for line in new_lines:
            new_file.write(line)
    copymode(target_path, abs_path)
    remove(target_path)
    move(abs_path, target_path)


if __name__ == '__main__':
    source_dir = sys.argv[1]
    files_path = os.path.join(source_dir, '*.tsv')
    files = glob(files_path)
    files.sort()
    for file in files:
        fix_file(file)
