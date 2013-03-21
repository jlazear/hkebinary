#!/bin/env python
"""
HKEBinaryFile.py - A class that creates a Python representation of a
HKE binary file.

Example usage:
    f = HKEBinaryFile('hke_20120624_001.dat')
    f.list_registers()
    RTs = f.get_data(0).flatten()
    Rs = f.get_data(-6)[...,1]

jlazear
jlazear@pha.jhu.edu
June 25, 2012
"""

from HKEBinaryLibrary2 import HKEBinaryReader, Header, Data, HKEBinaryError
from numpy import *


class HKEBinaryFile:
    """
    A class representing the full HKE binary file and containing some
    useful methods for accessing the encapsulated data.

    Arguments:
        filename - (str) filename of HKE binary file

    Example usage:
    f = HKEBinaryFile('hke_20120624_001.dat')
    f.list_registers()
    RTs = f.get_data(0).flatten()
    Rs = f.get_data(-6)[...,1]
    """
    def __init__(self, filename, verbose=True):
        if verbose is True:
            print "Reading data file..."
        self.filename = filename
        self.reader = HKEBinaryReader(filename=self.filename)
        self.header = Header(self.reader)
        self.data = Data(self.header)
        self._make_board_list()
        self._make_register_list()

    def _make_board_list(self):
        """
        A helper function to make a list of boards available in the
        file and create the necessary attributes.
        """
        self.boardlist = []
        self._boarddict = {}
        self._boarddictbyaddress = {}

        for bd in self.header.boarddescriptions:
            address = bd.address
            btype = bd.boardtype
            desc = bd.description
            toadd = '{desc} ({a}-{btype})'.format(a=address,
                                                  btype=btype,
                                                  desc=desc)
            self.boardlist.append(toadd)
            self._boarddict[toadd] = bd
            self._boarddictbyaddress[address] = bd

    def list_boards(self):
        """
        Returns a list of the boards in the file in the format:

            <description> (<address>-<board type>)
        """
        return self.boardlist

    def get_board(self, identifier=None, address=None):
        """
        Get a reference to a particular board object.

        Identifier may be an integer or a string. If it is an integer,
        then it is interpreted as an index of self.boardlist and
        returns a reference to the board of that index. If it is a
        string, then it is interpreted as the name of the board to
        return a reference of.

        Boards may also be referenced by address. Use the address
        keyword argument to pass an address integer.
        """
        if isinstance(identifier, int):
        # if type(identifier) is type(1):
            return self._boarddict[self.boardlist[identifier]]
        # elif type(identifier) is type('a'):
        elif isinstance(identifier, str):
            return self._boarddict[identifier]

        if address is not None:
            return self._boarddictbyaddress[address]

    def _make_register_list(self):
        """
        A helper function to make a list of registers available in the
        file and create the necessary attributes.
        """
        self.registerlist = self.header._rkeylist
        self.registerdescriptionlist = self.header._rdlist

        self._registerdict = {}
        self._registerdescriptiondict = {}
        for i, rname in enumerate(self.registerlist):
            toadd = [rf.registers[rname] for rf in
                     self.data.registerframelist]
            self._registerdict[rname] = toadd

            toaddrd = self.registerdescriptionlist[i]
            self._registerdescriptiondict[rname] = toaddrd

    def list_registers(self):
        """
        Returns a list of the registers in the format:

            <board description> (<address>-<board type>): <register description>
        """
        return self.registerlist

    def get_registers(self, identifier=None):
        """
        Get a reference to a list of registers identified by
        identifier.

        Identifier may be an integer or a string. If it is an integer,
        then it is interpreted as an index of self.registerlist and
        returns a reference to the registers of that index. If it is a
        string, then it is interpreted as the name of the registers to
        return a reference of.
        """
        if isinstance(identifier, int):
            return self._registerdict[self.registerlist[identifier]]
        elif isinstance(identifier, str):
            return self._registerdict[identifier]

    def get_register_description(self, identifier=None):
        """
        Get a reference to the register description identified by
        identifier.

        Identifier may be an integer or a string. If it is an integer,
        then it is interpreted as an index of self.registerlist and
        returns a reference to the register description of that
        index. If it is a string, then it is interpreted as the name
        of the register whose description is to be returned.
        """
        if isinstance(identifier, int):
            return self._registerdescriptiondict[self.registerlist[identifier]]
        elif isinstance(identifier, str):
            return self._registerdescriptiondict[identifier]

    def _get_single_data(self, identifier, reduced=None,
                         reductionfunction=None):
        """
        Extracts data from a single register specified by identifier.

        The reduced flag specifies whether to extract the reduced data
        or the raw data. In most cases, only the reduced data is
        interesting, so reduced=True is the default setting.

        If nch > 1 in the register, then each RegisterFrame will
        have multiple independent channels. Each of these channels is
        read out independently, resulting in the returned array having
        more than one column (second index).

        If nsamples > 1 in the register, then each channel of each
        RegisterFrame will have multiple data points. This method also
        admits a function to reduce those multiple data points to a
        single data point, reductionfunction.

        reductionfunction defaults to average, which simply averages
        the points. An arbitrary reductionfunction is allowed, subject
        to the following constraints:

            - it must accept a 3D ndarray
            - it must accept an axis keyword argument, such that
                axis=2 specifies that the function is to apply over
                the third index.
            - it must return a 2D ndarray of an object type that can
                be converted to a numpy float32.

        Note that any function that takes a list of values and returns
        a float can be converted to this form, though it may take some
        work.
        """
        if reduced is None:
            reduced = True

        if reductionfunction is None:
            reductionfunction = average

        rd = self.get_register_description(identifier)
        if (rd.flags is 0) and (reduced == True):
            print "Register {rname} does not have reduced \
data. Extracting raw data.".format(rname=rd.fullname)
            reduced = False

        if reduced == True:
            data = array([r.reduceddata for r in
                          self.get_registers(identifier)])
        elif reduced == False:
            data = array([r.rawdata for r in
                          self.get_registers(identifier)])
        else:
            raise HKEBinaryError

        nch = rd.nch
        nreg = len(data)

        data = data.reshape(nreg, nch, -1)
        if data.shape[-1] == 1:
            data = data.reshape(nreg, nch)
        else:
            data = reductionfunction(data, axis=2)

        return data

    def get_data(self, identifier=None, reduced=None,
                 reductionfunction=None, channels=None):
        """
        Extracts data from the registers and returns them as a NumPy
        structured array.

        identifier may be an integer or a string, as in
        self.get_registers, or it may also be a list of integers or a
        list of strings. If identifier is not a list, then it returns
        a 1D array of the data specified by the identifier. If
        identifier is a list, then it returns a 2D array, the first
        index specifying the register and the second specifying the
        register frame, i.e. the first index indexes the identifier
        list, and the second the corresponding data set.

        The defining property of structured arrays is that their
        columns may be indexed like a dictionary, so something like

            >>> mydata = get_data(['col1', 'col2'])
            >>> mydata['col1']

        will return the data corresponding to 'col1'.

        Users that are more comfortable with standard Numpy arrays may
        convert the structured arrays to standard arrays using the
        self.sarray_to_array() method.

        Note that in order to avoid name collisions between boards of
        the same type, columns are named according to the convention:

            <board address>-<register name>

        The reduced flag indicates whether to extract the reduced data
        or the raw data. Since normally only the reduced data is of
        any interest, by default the reduced data is
        extracted. Setting reduced=False will extract the raw
        data. reduced may also be a list of boolean values, which
        matches up with a list of identifiers and allows reduced to be
        set on a per-identifier basis.

        The reductionfunction is used to handle registers with
        nsamples > 1 and reduces these multiple data points in the
        register to a single data point. It defaults to average.
        """
        # listtypes = [list, tuple, numpy.ndarray]
        listtypes = [type([1]), type((1, 2)), type(array([1, 2]))]
        # singletypes = [int]
        singletypes = [type(1), type(1.0), type('a')]
        if type(identifier) in listtypes:
#             numcols = len(identifier)
            numrows = len(self.data.registerframelist)
            names = []
            for i, idf in enumerate(identifier):
                rd = self.get_register_description(idf)
                try:
                    chs = channels[i]
                    if type(chs) in listtypes:
                        pass
                    elif type(chs) in (type(1), type(1.)):
                        chs = [chs]
                    else:
                        raise TypeError
                except TypeError:
                    chs = range(rd.nch)

                if rd.nch == 1:
                    names.append(rd.columnname)
                elif rd.nch > 1:
                    for j in range(rd.nch):
                        if j in chs:
                            names.append(rd.columnname + '-' + str(j))
                else:
                    raise HKEBinaryError  # Should never get here...
            formats = ['f8' for n in names]
            dtdict = {'names': names, 'formats': formats}
            d = dtype(dtdict)
            rarray = recarray((numrows,), dtype=d)
            namesiter = iter(names)

            for i, idf in enumerate(identifier):
                rd = self.get_register_description(idf)
                try:
                    rflag = reduced[i]
                except TypeError:
                    rflag = reduced
                try:
                    chs = channels[i]
                    if type(chs) in (type(1), type(1.)):
                        chs = [chs]
                    elif type(chs) in listtypes:
                        pass
                    else:
                        raise TypeError
                except TypeError:
                    chs = range(rd.nch)

                a = self._get_single_data(idf, reduced=reduced,
                                          reductionfunction=reductionfunction)

                for j in chs:
                    colname = namesiter.next()
                    c = a[..., j]
                    rarray[colname] = c

            return rarray
        elif type(identifier) in singletypes:
            rd = self.get_register_description(identifier)
            if channels is None:
                ch = range(rd.nch)
            elif channels in (type(1), type(1.0)):
                ch = [channels]
            elif channels in listtypes:
                ch = array(channels).flatten()
            else:
                raise HKEBinaryError
            a = self._get_single_data(identifier, reduced=reduced,
                                      reductionfunction=reductionfunction)

            return a[..., ch]
        else:
            raise HKEBinaryError

    def sarray_to_array(self, sarray):
        """
        Convert a structured array (e.g. the output of
        self.get_data([0,1])) to a regular 2D Numpy array. Note that
        this creates a view of the structured array, so the values in
        the structured array and resulting 2D ndarray are linked.
        """
        columns = len(sarray.dtype.names)
        a = sarray.view().reshape(-1, columns)
        return a
