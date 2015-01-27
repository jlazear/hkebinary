#!/bin/env python
"""
HKEBinaryLibrary.py - A library for reading the HKE Binary Files.

Example usage:
    None; used by HKEBinaryFile.py instead.

jlazear
jlazear@pha.jhu.edu
June 25, 2012
"""

from bitstring import BitStream
from numpy import *


class RegisterFrameDescription(object):
    def __init__(self, hkebreader):
        # This check slows down the read considerably, so just enforce
        # that hkebreader is actually a HKEBinaryReader object.
        # if isinstance(hkebreader, HKEBinaryReader):
        #     h = hkebreader
        # else:
        #     h = HKEBinaryReader(bitstream=hkebreader)
        h = hkebreader
        self.reader = hkebreader
        self.filename = self.reader.filename

        h.bitstream.pos = 0
        self.startpos = h.bitstream.pos + 0
        self.magic = h.char()
        if self.magic is not 'F':
            raise HKEMagicError
        self.version = h.ushort()
        self.timestamp = h.string()
        self.boardcount = h.ushort()
        self.boarddescriptions = []
        self.boards = {}
        for i in range(self.boardcount):
            bd = BoardDescription(self)
            self.boarddescriptions.append(bd)
            self.boards[bd.description] = bd

        self._rkeylist = []
        self._rdlist = []
        for bd in self.boarddescriptions:
            btype = bd.boardtype
            baddress = bd.address
            bdesc = bd.description
            prefixstr = '{desc} ({address}-{type}): '
            prefix = prefixstr.format(desc=bdesc,
                                      type=btype,
                                      address=baddress)
            for rd in bd.registerdescriptions:
                rname = rd.name
                key = prefix + rname
                self._rkeylist.append(key)
                self._rdlist.append(rd)
        self.endpos = h.bitstream.pos + 0
        self.length = self.endpos - self.startpos + 1


class BoardDescription(object):
    def __init__(self, rfd):
        # This check slows down the read considerably, so just enforce
        # that hkebreader is actually a HKEBinaryReader object.
        # if isinstance(hkebreader, HKEBinaryReader):
        #     h = hkebreader
        # else:
        #     h = HKEBinaryReader(bitstream=hkebreader)
        self.rfd = rfd
        self.registerframedescription = self.rfd
        self.reader = self.rfd.reader

        self.startpos = self.reader.bitstream.pos + 0.
        self.magic = self.reader.char()
        if self.magic is not 'B':
            raise HKEMagicError
        self.boardtype = self.reader.string()
        self.address = self.reader.byte()
        self.description = self.reader.string()
        self.registercount = self.reader.ushort()
        self.registerdescriptions = []
        self.registers = {}
        for i in range(self.registercount):
            rd = RegisterDescription(self)
            self.registerdescriptions.append(rd)
            self.registers[rd.name] = rd
        self.endpos = self.reader.bitstream.pos + 0
        self.length = self.endpos - self.startpos + 1


class RegisterDescription(object):
    _rtypenamedict = {0: 'uint8', 1: 'uint16', 2: 'uint32',
                      3: 'float', 4: 'int16', 5: 'int32'}
    _rtypelengthdict = {0: 1, 1: 2, 2: 4, 3: 4, 4: 2, 5: 4,
                        'uint8': 1, 'uint16': 2, 'uint32': 4,
                        'float': 4, 'int16': 2, 'int32': 4}

    def __init__(self, bd):
        # This check slows down the read considerably, so just enforce
        # that hkebreader is actually a HKEBinaryReader object.
        # if isinstance(hkebreader, HKEBinaryReader):
        #     h = hkebreader
        # else:
        #     h = HKEBinaryReader(bitstream=hkebreader)
        self.bd = bd
        self.boarddescription = self.bd
        self.reader = self.bd.reader

        self.startpos = self.reader.bitstream.pos + 0
        self.magic = self.reader.char()
        if self.magic is not 'R':
            raise HKEMagicError
        self.name = self.reader.string()
        self.fullname = '{desc} ({address}-{type}): {name}\
'.format(desc=self.bd.description, address=self.bd.address,
         type=self.bd.boardtype, name=self.name)
        self.columnname = '{address}-{name}'.format(address=self.bd.address,
                                                    name=self.name)
        self.registertype = self.reader.byte()
        self.registertypename = self._rtypenamedict[self.registertype]
        self.registertypelength = self._rtypelengthdict[self.registertype]
        self.nch = self.reader.ushort()
        self.nsamples = self.reader.ushort()
        self.chtags = self.reader.stringarray(length=self.nch)
        self.flags = self.reader.byte()
        if self.flags is 0:
            self.units = None
            self.linslope = None
            self.linoffset = None
            return
        self.units = self.reader.string()
        if self.flags is 2:
            self.linslope = self.reader.float()
            self.linoffset = self.reader.float()
        else:
            self.linslope = None
            self.linoffset = None
        self.endpos = self.reader.bitstream.pos + 0
        self.length = self.endpos - self.startpos + 1


class HKEBinaryReader(object):

    bitstream = None

    def __init__(self, filename):
        self.arraydict = {'uint8': self.uint8array,
                          'uint16': self.uint16array,
                          'uint32': self.uint32array,
                          'float': self.floatarray,
                          'int16': self.int16array,
                          'int32': self.int32array,
                          0: self.uint8array,
                          1: self.uint16array,
                          2: self.uint32array,
                          3: self.floatarray,
                          4: self.int16array,
                          5: self.int32array}

        self.filename = filename
        self.bitstream = BitStream(filename=filename)
        self.bitstream.pos = 0

    def char(self, bitstream=None):
        """
        Read a character from the specified bitstream or stored
        bistream if none is given. Returns a string object containing
        the single read character.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        b = self.byte(bitstream)
        c = chr(b)
        return c

    def string(self, bitstream=None):
        """
        Read a string from the specified bitstream or stored bitstream
        if none is given. Returns a string object containing the read
        string.

        Note that this type of string is the HKE string, which has the
        format:

            ucccc...

        where u is a unsigned byte (standard 'char' not converted to
        ASCII) that specified how many characters are in the
        string; c is a character (as above). The number of c's is
        determined by the value of u, i.e. u = (# of c's).
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        num = self.byte(bitstream)
        slist = bitstream.readlist('{num}*uint:8'.format(num=num))
        string = ''.join([chr(s) for s in slist])
        return string

    def byte(self, bitstream=None):
        """
        Read a HKE byte from the specified bitstream or stored
        bitstream if none is given. Returns the value of the read
        byte.

        The HKE byte is an unsigned byte (standard 'char' not
        converted to ASCII; equivalently a standard uint8), and has a
        value that ranged from 0 to 255.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        byte = bitstream.read('uintle:8')
        return byte

    def uint8(self, bitstream=None):
        """
        Read a uint8 from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read uint8.

        A uint8 is an unsigned 8-bit integer and can take values
        0 to 255.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint8 = bitstream.read('uintle:8')
        return uint8

    def ushort(self, bitstream=None):
        """
        Read an unsigned short from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read ushort.

        ushort is a 2-byte (16-bit) unsigned integer with values
        ranging from 0 to 65535.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        ushort = bitstream.read('uintle:16')
        return ushort

    def uint16(self, bitstream=None):
        """
        Read a uint16 from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read uint16.

        A uint16 is an unsigned 16-bit integer and can take values
        0 to 65535.

        Note that uint16 and ushort are the same thing.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint16 = bitstream.read('uintle:16')
        return uint16

    def uint32(self, bitstream=None):
        """
        Read a uint32 from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read uint32.

        A uint32 is an unsigned 16-bit integer and can take values
        0 to 4294967295.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint32 = bitstream.read('uintle:32')
        return uint32

    def int16(self, bitstream=None):
        """
        Read a int16 from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read int16.

        An int16 is an signed 16-bit integer and can take values
        -32767 to 32767.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        int16 = bitstream.read('intle:16')
        return int16

    def int32(self, bitstream=None):
        """
        Read a int32 from the specified bitstream or stored
        bitstream if none is given. Returns a Python int object with
        the value of the read int32.

        An int32 is an signed 32-bit integer and can take values
        -2147483647 to 2147483647.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        int32 = bitstream.read('intle:32')
        return int32

    def stringarray(self, length, bitstream=None):
        """
        Read an array of strings from the specified bitstream or
        stored bitstream if none is given. Returns the read strings in
        a list of specified length.

        A string is the HKE string. See HKEBinaryReader.string for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        stringarray = []
        for i in range(length):
            string = self.string(bitstream)
            stringarray.append(string)

        return stringarray

    def float(self, bitstream=None):
        """
        Read an 32-bit float from the specified bitstream or stored
        bitstream if none is given. Returns a native Python float
        object (32bit if 32-bit Python, 64bit if 64-bit Python) of the
        same value as the read float.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        f = bitstream.read('floatle:32')
        return f

    def bytearray(self, length, bitstream=None):
        """
        Read an array of bytes from the specified bitstream or stored
        bitstream if none is given. Returns the read bytes in a list
        of specified length.

        A byte is the HKE byte. See HKEBinaryReader.byte for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        bytearray = []
        for i in range(length):
            byte = self.byte(bitstream)
            bytearray.append(byte)

        return bytearray

    def floatarray(self, length, bitstream=None):
        """
        Read an array of floats from the specified bitstream or stored
        bitstream if none is given. Returns the read floats in a list
        of specified length.

        A float is the HKE float. See HKEBinaryReader.float for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        floatarray = []
        for i in range(length):
            float = self.float(bitstream)
            floatarray.append(float)

        return floatarray

    def uint8array(self, length, bitstream=None):
        """
        Read an array of uint8s from the specified bitstream or stored
        bitstream if none is given. Returns the read uint8s in a list
        of specified length.

        A uint8 is the HKE uint8. See HKEBinaryReader.uint8 for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint8array = []
        for i in range(length):
            uint8 = self.uint8(bitstream)
            uint8array.append(uint8)

        return uint8array

    def uint16array(self, length, bitstream=None):
        """
        Read an array of uint16s from the specified bitstream or stored
        bitstream if none is given. Returns the read uint16s in a list
        of specified length.

        A uint16 is the HKE uint16. See HKEBinaryReader.uint16 for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint16array = []
        for i in range(length):
            uint16 = self.uint16(bitstream)
            uint16array.append(uint16)

        return uint16array

    def uint32array(self, length, bitstream=None):
        """
        Read an array of uint32s from the specified bitstream or stored
        bitstream if none is given. Returns the read uint32s in a list
        of specified length.

        A uint32 is the HKE uint32. See HKEBinaryReader.uint32 for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        uint32array = []
        for i in range(length):
            uint32 = self.uint32(bitstream)
            uint32array.append(uint32)

        return uint32array

    def int16array(self, length, bitstream=None):
        """
        Read an array of int16s from the specified bitstream or stored
        bitstream if none is given. Returns the read int16s in a list
        of specified length.

        A int16 is the HKE int16. See HKEBinaryReader.int16 for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        int16array = []
        for i in range(length):
            int16 = self.int16(bitstream)
            int16array.append(int16)

        return int16array

    def int32array(self, length, bitstream=None):
        """
        Read an array of int32s from the specified bitstream or stored
        bitstream if none is given. Returns the read int32s in a list
        of specified length.

        A int32 is the HKE int32. See HKEBinaryReader.int32 for info.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        int32array = []
        for i in range(length):
            int32 = self.int32(bitstream)
            int32array.append(int32)

        return int32array

    def array(self, length, type, bitstream=None):
        """
        Reads an array of the specified type from the specified
        bitstream or stored bitstream if none is given. Returns the
        read values in a list of the specified length.
        """
        if bitstream is None:
            bitstream = self.bitstream

        if bitstream is None:
            raise HKEBitstreamError

        try:
            method = self.arraydict[type]
        except KeyError:
            print "Invalid array type."
            return

        a = method(length, bitstream)
        return a


class Header(RegisterFrameDescription):
    """
    The HKE binary data file header.

    Currently this contains only the RegisterFrameDescription. As
    such, it's being made transparent. If other objects are added to
    the header, this class should be rewritten.
    """
    def __init__(self, hkebreader):
        RegisterFrameDescription.__init__(self, hkebreader)


class Data(object):
    """
    The HKE binary data file data.

    Contains a series of RegisterFrames.
    """
    def __init__(self, header):
        self.filename = header.filename
        self.header = header
        f = open(self.filename, 'rb')
        # This is a HUGE hack. Should really do this in RegFrameDesc...
        self.header.rawheader = f.read(self.header.endpos/8)
        # f.seek(self.header.endpos/8)

        self.dt = self.dtype_from_rfd(self.header)
        self.data = fromfile(f, self.dt)

    def dtype_from_rfd(self, rfd):
        dta = [('magic', 'S1'), ('framecount', 'u4'),
               ('framereceivedms', 'u4')]
        for bd in rfd.boarddescriptions:
            toadd = self.dtype_from_bd(bd)
            dta.extend(toadd)
        return dtype(dta)

    def dtype_from_bd(self, bd):
        dta = []
        for rd in bd.registerdescriptions:
            toadd = self.dtype_from_rd(rd)
            dta.extend(toadd)
        return dta

    def dtype_from_rd(self, rd):
        rtypedict = {0: 'u1', 1: 'u2', 2: 'u4', 3: 'f4', 4: 'i2',
                     5: 'i4'}

        dta = []
        rtype = rd.registertype
        rt = rtypedict[rtype]
        nchstr = '({0},{1})'.format(rd.nch, rd.nsamples)
        label = rd.fullname
        toadd = (label, nchstr + rt)
        dta.append(toadd)
        if rd.flags == 4:
            toadd = (label + ' (reduced)', nchstr + 'f4')
            dta.append(toadd)

        return dta



class HKEBinaryError(Exception):
    """
    Exception class for handling errors unique to working with the HKE
    binary files.
    """
    pass


class HKEMagicError(HKEBinaryError):
    """
    An incorrect magic character was encountered.
    """
    pass


class HKEBitstreamError(HKEBinaryError):
    """
    There was an error in the bitstream to be read.
    """
    pass


class HKEInvalidRegisterError(HKEBinaryError):
    """
    User tried to access an invalid register.
    """
    def __init__(self, rname):
        self.rname = rname
        self.msg = ("Invalid register specifier:"
                    " {0}".format(self.rname))

    def __str__(self):
        return self.msg


# def entrypoint():
#     s = BitStream(filename='hke_20120323_000.dat')

#     header = Header(s)
#     data = Data(s, header)

# def entrypoint2():
#     s = BitStream(filename='hke_20120323_000.dat')
#     h = HKEBinaryReader(bitstream=s)
#     header = Header(h)
#     data = Data(h, header)
#     return s, h, header, data

# def runprofiling(entrypoint):
#     import cProfile
#     import pstats
#     name = entrypoint.__name__
#     tocall = name + '()'
#     cProfile.run(tocall, 'tempprof')
#     p = pstats.Stats('tempprof')
#     p.strip_dirs()
#     p.sort_stats('time')
#     p.print_stats(15)
#     return p

# # if __name__ == '__main__':
# #     p = runprofiling(entrypoint2)
