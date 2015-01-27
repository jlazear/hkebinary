import sys
import os

import numpy as np

from HKEBinaryFile import HKEBinaryFile as File

def hkebinary_to_csv(fname):
    f = File(fname)

    reglist = f.list_registers()

    header = []
    alldata = None
    for reg in reglist:
        data = f.get_data(reg)
        ncols = data.shape[1]
        colnames = ['{0}_{1}'.format(reg, i) for i in range(ncols)]
        header.extend(colnames)
        try:
            alldata = np.hstack([alldata, data])
        except ValueError:
            alldata = data

    header = ','.join(header)

    base, ext = os.path.splitext(fname)
    newfname = base + '.csv.gz'
    np.savetxt(newfname, alldata, delimiter=',', header=header)


if __name__ == "__main__":
    fname = sys.argv[1]
    hkebinary_to_csv(fname)


