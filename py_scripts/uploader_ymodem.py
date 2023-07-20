#!/usr/bin/python3
import config.config as cf
import src.colorLog as log
import sys, os, time
from getopt import getopt
from getopt import GetoptError
import serial
import platform
import types
import src.commonFunction as commonFunction
fun = commonFunction.Common()

default_baudrate = 115200
boot_mode = 0

class RWBuilder(object):
    def __init__(self, rFunc=None, wFunc=None):
        self.read = rFunc
        self.write = wFunc

class Protocol(object):

    @property
    def reader(self):
        return self._reader

    @property
    def writer(self):
        return self._writer

    @reader.setter
    def reader(self, r):
        if hasattr(r, "read") and isinstance(r.read, types.FunctionType):
            self._reader = r
        elif isinstance(r, types.FunctionType):
            self._reader = RWBuilder(rFunc=r)
        else:
            raise TypeError("unknown type for reader")
    
    @writer.setter
    def writer(self, w):
        if hasattr(w, "write") and isinstance(w.write, types.FunctionType):
            self._writer = w
        elif isinstance(w, types.FunctionType):
            self._writer = RWBuilder(wFunc=w)
        else:
            raise TypeError("unknown type for writer")


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
NAK = b'\x15'
CAN = b'\x18'
CRC = b'\x43'

USE_LENGTH_FIELD    = 0b100000
USE_DATE_FIELD      = 0b010000
USE_MODE_FIELD      = 0b001000
USE_SN_FIELD        = 0b000100
ALLOW_1KBLK         = 0b000010
ALLOW_YMODEMG       = 0b000001

class Modem(Protocol):
    def __init__(self, reader, writer, mode='ymodem1k', program="rzsz"):
        self.reader = reader
        self.writer = writer
        self.mode   = mode

        '''
        YMODEM Header Information and Features
        _____________________________________________________________
        | Program   | Length | Date | Mode | S/N | 1k-Blk | YMODEM-g |
        |___________|________|______|______|_____|________|__________|
        |Unix rz/sz | yes    | yes  | yes  | no  | yes    | sb only  |
        |___________|________|______|______|_____|________|__________|
        |VMS rb/sb  | yes    | no   | no   | no  | yes    | no       |
        |___________|________|______|______|_____|________|__________|
        |Pro-YAM    | yes    | yes  | no   | yes | yes    | yes      |
        |___________|________|______|______|_____|________|__________|
        |CP/M YAM   | no     | no   | no   | no  | yes    | no       |
        |___________|________|______|______|_____|________|__________|
        |KMD/IMP    | ?      | no   | no   | no  | yes    | no       |
        |___________|________|______|______|_____|________|__________|
        '''
        try:
            self.ymodem_flags = dict(
                rzsz    = USE_LENGTH_FIELD | USE_DATE_FIELD | USE_MODE_FIELD | ALLOW_1KBLK,
                rbsb    = USE_LENGTH_FIELD | ALLOW_1KBLK,
                pyam    = USE_LENGTH_FIELD | USE_DATE_FIELD | USE_SN_FIELD | ALLOW_1KBLK | ALLOW_YMODEMG,
                cyam    = ALLOW_1KBLK,
                kimp    = ALLOW_1KBLK,
            )[program]
        except KeyError:
            raise ValueError("Invalid program specified: {}".format(program))
        
    def abort(self, count=2, timeout=60):
        for _ in range(count):
            self.writer.write(CAN, timeout)

    def send(self, stream, retry=30, timeout=10, quiet=False, callback=None, info=None):
        try:
            packet_size = dict(
                xmodem    = 128,
                xmodem1k  = 1024,
                ymodem    = 128,
                # Not all but most programs support 1k length
                ymodem1k  = (128, 1024)[(self.ymodem_flags & ALLOW_1KBLK) != 0],
            )[self.mode]
        except KeyError:
            raise ValueError("Invalid mode specified: {self.mode!r}".format(self=self))
        
        '''
        The first package for YMODEM Batch Transmission
        It will contain some important information about the source file
        '''
        if self.mode.startswith("ymodem"):

            log.Logger('[S] STATE: Waiting the mode request...', 'GREEN')

            error_count = 0
            crc_mode = 0
            cancel = 0
            while True:
                char = self.reader.read(1)
                if char:
                    if char == NAK:
                        log.Logger("[S] STATE: Received checksum request (NAK)", 'GREEN')
                        crc_mode = 0
                        log.Logger("[S] STATE: Checksum mode applied", 'GREEN')
                        break
                    elif char == CRC:
                        log.Logger("[S] STATE: Received CRC request (C/CRC)", 'GREEN')
                        crc_mode = 1
                        log.Logger("[S] STATE: 16-bit CRC mode applied", 'GREEN')
                        break
                    elif char == CAN:
                        if not quiet:
                            log.Logger('received CAN', file=sys.stderr)
                        if cancel:
                            log.Logger("[S] STATE: Transmission cancelled (Received 2 CANs at mode request)", 'RED')
                            return False
                        else:
                            log.Logger("[S] STATE: Ready for transmission cancellation")
                            cancel = 1
                    elif char == EOT:
                        log.Logger("[S] STATE: Transmission cancelled (Received EOT at mode request)", 'RED')
                        return False
                    else:
                        log.Logger("[S] ERROR: Expected NAK, CRC, EOT or CAN but got %r"%char, 'RED')
                error_count += 1
                if error_count > retry:
                    log.Logger("[S] ERROR: error_count reached {}, aborting...".format(retry), 'RED')
                    self.abort(timeout=timeout)
                    return False


            log.Logger("[S] STATE: Preparing info block", 'GREEN')

            header = self._make_send_header(packet_size, 0)

            # [required] Name
            data = info["name"].encode("utf-8")
            
            # [Optional] Length
            if self.ymodem_flags & USE_LENGTH_FIELD:
                data += bytes(1)
                data += str(info["length"]).encode("utf-8")

            '''
            [Optional] Modification Date
            oct() has different representations of octal numbers in different versions of Python:
            Python 2+: 0123456
            Python 3+: 0o123456
            '''
            '''
            if self.ymodem_flags & USE_DATE_FIELD:
                mtime = oct(int(info["mtime"]))
                if mtime.startswith("0o"):
                    data += (" " + mtime[2:]).encode("utf-8")
                else:
                    data += (" " + mtime[1:]).encode("utf-8")

            # [Optional] Mode
            if self.ymodem_flags & USE_MODE_FIELD:
                if info["source"] == "Unix":
                    data += (" " + oct(0x8000)).encode("utf-8")
                else:
                    data += (" 0").encode("utf-8")

            # [Optional] Serial Number
            if self.ymodem_flags & USE_MODE_FIELD:
                data += (" 0").encode("utf-8")
            '''
            data = data.ljust(packet_size, b"\x00")
            checksum = self._make_send_checksum(crc_mode, data)
                
            error_count = 0
            self.writer.write(header + data + checksum)
            while True:
                
                log.Logger("[S] TRANSMISSION: info block sent", 'GREEN')
                time.sleep(1)
                char = self.reader.read(1, timeout)
                if char == ACK:
                    error_count = 0
                    break

                log.Logger("[S] ERROR: Expected ACK but got %r for info block"%char, 'RED')
                error_count += 1
                if error_count > retry:
                    log.Logger("[S] ERROR: NAK received {} times, aborting...".format(error_count), 'RED')
                    self.abort(timeout=timeout)
                    return False

        # Data packets
        log.Logger("[S] STATE: Waiting the mode request...", 'GREEN')
        error_count = 0
        crc_mode = 0
        cancel = 0
        while True:
            char = self.reader.read(1)
            if char:
                if char == NAK:
                    log.Logger("[S] STATE: Received checksum request (NAK)", 'GREEN')
                    crc_mode = 0
                    log.Logger("[S] STATE: Checksum mode applied", 'GREEN')
                    break
                elif char == CRC:
                    log.Logger("[S] STATE: Received CRC request (C/CRC)", 'GREEN')
                    crc_mode = 1
                    log.Logger("[S] STATE: 16-bit CRC mode applied", 'GREEN')
                    break
                elif char == CAN:
                    if not quiet:
                        log.Logger('received CAN', file=sys.stderr)
                    if cancel:
                        log.Logger("[S] TRANSMISSION: Cancelled (Received 2 CANs at mode request)", 'RED')
                        return False
                    else:
                        log.Logger("[S] STATE: Ready for transmission cancellation", 'GREEN')
                        cancel = 1
                elif char == EOT:
                    log.Logger("[S] TRANSMISSION: Cancelled (Received EOT at mode request)", 'RED')
                    return False
                else:
                    log.Logger("[S] ERROR: Expected NAK, CRC, EOT or CAN but got %r"%char, 'RED')
            error_count += 1
            if error_count > retry:
                log.Logger("[S] ERROR: error_count reached {}, aborting...".format(retry), 'RED')
                self.abort(timeout=timeout)
                return False

        error_count = 0
        success_count = 0
        total_packets = 0
        sequence = 1
        cancel = 0
        while True:
            data = stream.read(packet_size)
            if not data:
                log.Logger("[S] TRANSMISSION: Reached EOF", 'GREEN')
                break
            total_packets += 1

            header = self._make_send_header(packet_size, sequence)
            # fill with 1AH(^z)
            data = data.ljust(packet_size, b"\x1a")
            checksum = self._make_send_checksum(crc_mode, data)

            while True:
                self.writer.write(header + data + checksum)
                log.Logger("[S] TRANSMISSION: block {} (seq={}) sent".format(success_count, sequence))
                char = self.reader.read(1, timeout)
                if char == ACK:
                    success_count += 1
                    if callable(callback):
                        callback(total_packets, success_count, error_count)
                    error_count = 0
                    break
                elif char == CAN:
                    if cancel:
                        log.Logger("[S] TRANSMISSION: Cancelled (Received 2 CANs at transmission)", 'RED')
                        self.abort(timeout=timeout)
                        return False
                    else:
                        log.Logger("[S] STATE: Ready for transmission cancellation", 'RED')
                        cancel = 1
      

                log.Logger('[S] ERROR: Expected ACK but got %r for block %d' %(char, sequence), 'RED')
                error_count += 1
                if callable(callback):
                    callback(total_packets, success_count, error_count)
                if error_count > retry:
                    log.Logger("[S] ERROR: NAK received {} times, aborting...".format(error_count), 'RED')
                    self.abort(timeout=timeout)
                    return False

            sequence = (sequence + 1) % 0x100

        while True:
            self.writer.write(EOT)
            log.Logger("[S] TRANSMISSION: EOT sent and awaiting ACK", 'GREEN')

            char = self.reader.read(1, timeout)
            if char == ACK:
                break
            else:
                log.Logger("[S] ERROR: Expected ACK but got %r"%char, 'RED')
                error_count += 1
                if error_count > retry:
                    log.Logger("[S] WARN: EOT was not ACKd, aborting transfer...", 'RED')
                    self.abort(timeout=timeout)
                    return False

        log.Logger("[S] TRANSMISSION: Finished (ACK received)", 'GREEN')
        
        while True:
            header = self._make_send_header(packet_size, 0)
            data = data.ljust(packet_size, b"\x00")
            checksum = self._make_send_checksum(crc_mode, data)
            self.writer.write(header + data + checksum)
            log.Logger("[S] TRANSMISSION: SEND NULL", 'GREEN')
            char = self.reader.read(1, timeout)
            if char == ACK:
                break
            else:
                log.Logger("[S] ERROR: Expected ACK but got %r"%char, 'RED')
                error_count += 1
                if error_count > retry:
                    log.Logger("[S] WARN: EOT was not ACKd, aborting transfer...", 'RED')
                    self.abort(timeout=timeout)
                    return False
        return True

    def _make_send_header(self, packet_size, sequence):
        assert packet_size in (128, 1024), packet_size
        _bytes = []
        if packet_size == 128:
            _bytes.append(ord(SOH))
        elif packet_size == 1024:
            _bytes.append(ord(STX))
        _bytes.extend([sequence, 0xff - sequence])
        return bytearray(_bytes)

    def _make_send_checksum(self, crc_mode, data):
        _bytes = []
        if crc_mode:
            crc = self.calc_crc(data)
            _bytes.extend([crc >> 8, crc & 0xff])
        else:
            crc = self.calc_checksum(data)
            _bytes.append(crc)
        return bytearray(_bytes)

    def recv(self, stream, crc_mode=1, retry=10, timeout=10, delay=1, quiet=0, callback=None, info=None):
        self._recv_file_name = ""
        self._remaining_data_length = 0
        self._recv_file_mtime = 0
        self._recv_mode = 0
        self._recv_sn = 0

        '''
        Parse the first package of YMODEM Batch Transmission to get the target file information
        '''
        if self.mode.startswith("ymodem"):
            error_count = 0
            char = 0
            cancel = 0
            while True:
                if error_count >= retry:
                    log.Logger("[R] ERROR: error_count reached {}, aborting...".format(retry), 'RED')
                    self.abort(timeout=timeout)
                    return None
                elif crc_mode and error_count < (retry // 2):
                    if not self.writer.write(CRC):
                        log.Logger("[R] ERROR: Write failed, sleeping for {}".format(delay), 'RED')
                        time.sleep(delay)
                        error_count += 1
                else:
                    crc_mode = 0
                    if not self.writer.write(NAK):
                        log.Logger("[R] ERROR: Write failed, sleeping for {}".format(delay), 'RED')
                        time.sleep(delay)
                        error_count += 1

                char = self.reader.read(1, timeout=3)
                if char is None:
                    log.Logger("[R] ERROR: Read timeout in info block", 'RED')
                    error_count += 1
                    continue
                elif char == SOH:
                    log.Logger("[R] STATE: Received valid header (SOH)", 'GREEN')
                    break
                elif char == STX:
                    log.Logger("[R] STATE: Received valid header (STX)", 'GREEN')
                    break
                elif char == CAN:
                    if cancel:
                        log.Logger("[R] TRANSMISSION: Cancelled (Received 2 CANs at info block)", 'RED')
                        return None
                    else:
                        log.Logger("[R] STATE: Ready for transmission cancellation", 'GREEN')
                        cancel = 1
                else:
                    error_count += 1

            error_count = 0
            packet_size = 128
            cancel = 0
            while True:
                while True:
                    if char == SOH:
                        if packet_size != 128:
                            log.Logger("[R] STATE: Set 128 bytes for packet_size", 'GREEN')
                            packet_size = 128
                        break
                    elif char == STX:
                        if packet_size != 1024:
                            log.Logger("[R] STATE: Set 1024 bytes for packet_size", 'GREEN')
                            packet_size = 1024
                        break
                    elif char == CAN:
                        if cancel:
                            log.Logger("[R] TRANSMISSION: Cancelled (Received 2 CANs at info block)", 'RED')
                            return None
                        else:
                            log.Logger("[R] STATE: Ready for transmission cancellation", 'GREEN')
                            cancel = 1
                    else:
                        err_msg = ("[R] ERROR: Expected SOH, EOT but got {0!r}".format(char))
                        if not quiet:
                            log.Logger(err_msg, file=sys.stderr)
                        log.Logger(err_msg, 'RED')
                        error_count += 1
                        if error_count > retry:
                            log.Logger("[R] ERROR: error_count reached %d, aborting...".format(retry), 'RED')
                            self.abort()
                            return None
                
                log.Logger('[R] STATE: Preparing for data packets....', 'GREEN')
                error_count = 0
                cancel = 0
                seq1 = self.reader.read(1, timeout)
                if seq1 is None:
                    log.Logger("[R] WARN: Read failed to get first sequence byte", 'RED')
                    seq2 = None
                else:
                    seq1 = ord(seq1)
                    seq2 = self.reader.read(1, timeout)
                    if seq2 is None:
                        log.Logger("[R] WARN: Read failed to get second sequence byte", 'RED')
                    else:
                        seq2 = 0xff - ord(seq2)

                if not (seq1 == seq2 == 0):
                    log.Logger("[R] ERROR: expected seq=0, got (seq1=%r, seq2=%r), receiving next block..."%(seq1, seq2), 'RED')
                    self.reader.read(packet_size + 1 + crc_mode)
                else:
                    log.Logger("crc mode" + str(crc_mode))
                    data = self.reader.read(packet_size + 1 + crc_mode, timeout)
                    valid, data = self._verify_recv_checksum(crc_mode, data)

                    if valid:
                        data = data.lstrip(b"\x00")
                        self._recv_file_name = bytes.decode(data.split(b"\x00")[0], "utf-8")
                        log.Logger("[R] TRANSMISSION: File - {}".format(self._recv_file_name), 'GREEN')

                        try:
                            stream = open(os.path.join(info["save_path"], self._recv_file_name), "wb+")
                        except IOError as e:
                            stream.close()
                            log.Logger("[R] ERROR: Cannot open save path", 'RED')
                            return
                        data = bytes.decode(data.split(b"\x00")[1], "utf-8")

                        if self.ymodem_flags & USE_LENGTH_FIELD:
                            space_index = data.find(" ")
                            self._remaining_data_length = int(data if space_index == -1 else data[:space_index])
                            log.Logger("[R] TRANSMISSION: Size - {} bytes".format(self._remaining_data_length), 'GREEN')
                            data = data[space_index + 1:]

                        if self.ymodem_flags & USE_DATE_FIELD:
                            space_index = data.find(" ")
                            self._recv_file_mtime = int(data if space_index == -1 else data[:space_index], 8)
                            log.Logger("[R] TRANSMISSION:  Mtime - {} seconds".format(self._recv_file_mtime), 'GREEN')
                            data = data[space_index + 1:]

                        if self.ymodem_flags & USE_MODE_FIELD:
                            space_index = data.find(" ")
                            self._recv_mode = int(data if space_index == -1 else data[:space_index])
                            log.Logger("[R] TRANSMISSION: Mode - {}".format(self._recv_mode), 'GREEN')
                            data = data[space_index + 1:]

                        if self.ymodem_flags & USE_SN_FIELD:
                            space_index = data.find(" ")
                            self._recv_sn = int(data if space_index == -1 else data[:space_index])
                            log.Logger("[R] TRANSMISSION: SN - {}".format(self._recv_sn), 'GREEN')

                        self.writer.write(ACK)
                        break

                log.Logger('[R] WARN: Purge, requesting retransmission (NAK)', 'RED')
                while True:
                    data = self.reader.read(1, timeout=1)
                    if data is None:
                        break
                self.writer.write(NAK)
                char = self.reader.read(1, timeout)
                continue

        error_count = 0
        char = 0
        cancel = 0
        while True:
            if error_count >= retry:
                log.Logger("[R] ERROR: error_count reached %d, aborting...".format(retry), 'RED')
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry // 2):
                if not self.writer.write(CRC):
                    log.Logger("[R] ERROR: Write failed, sleeping for {}".format(delay), 'RED')
                    time.sleep(delay)
                    error_count += 1
            else:
                crc_mode = 0
                if not self.writer.write(NAK):
                    log.Logger("[R] ERROR: Write failed, sleeping for {}".format(delay), 'RED')
                    time.sleep(delay)
                    error_count += 1

            char = self.reader.read(1, timeout=3)
            if char is None:
                log.Logger("[R] WARN: Read timeout in start sequence", 'RED')
                error_count += 1
                continue
            elif char == SOH:
                log.Logger("[R] STATE: Received valid header (SOH)", 'GREEN')
                break
            elif char == STX:
                log.Logger("[R] STATE: Received valid header (STX)", 'GREEN')
                break
            elif char == CAN:
                if cancel:
                    log.Logger("[R] TRANSMISSION: Cancelled (Received 2 CANs at data block)", 'RED')
                    return None
                else:
                    log.Logger("[R] STATE: Ready for transmission cancellation", 'GREEN')
                    cancel = 1
            else:
                error_count += 1
                
        error_count = 0
        success_count = 0
        income_size = 0
        packet_size = 128
        sequence = 1
        cancel = 0
        while True:
            while True:
                if char == SOH:
                    if packet_size != 128:
                        log.Logger("[R] STATE: Set 128 bytes for packet_size", 'GREEN')
                        packet_size = 128
                    break
                elif char == STX:
                    if packet_size != 1024:
                        log.Logger("[R] STATE: Set 1024 bytes for packet_size", 'GREEN')
                        packet_size = 1024
                    break
                elif char == EOT:
                    self.writer.write(ACK)
                    log.Logger("[R] TRANSMISSION: Finished (%d bytes received)" %income_size, 'GREEN')
                    return income_size
                elif char == CAN:
                    if cancel:
                        log.Logger("[R] TRANSMISSION: Cancelled: Received 2xCAN at data block {} (seq={})".format(success_count, sequence), 'RED')
                        return None
                    else:
                        log.Logger("[R] STATE: Ready for transmission cancellation at data block {} (seq={})".format(success_count, sequence), 'GREEN')
                        cancel = 1
                else:
                    err_msg = ("[R] ERROR: Expected SOH, EOT but got {0!r}".format(char))
                    if not quiet:
                        log.Logger(err_msg, file=sys.stderr)
                    log.Logger(err_msg, 'RED')
                    error_count += 1
                    if error_count > retry:
                        log.Logger("[R] ERROR: error_count reached {}, aborting...".format(retry), 'RED')
                        self.abort()
                        return None

            seq1 = self.reader.read(1, timeout)
            if seq1 is None:
                log.Logger("[R] WARN: Read failed to get first sequence byte", 'RED')
                seq2 = None
            else:
                seq1 = ord(seq1)
                seq2 = self.reader.read(1, timeout)
                if seq2 is None:
                    log.Logger("[R] WARN: Read failed to get second sequence byte", 'RED')
                else:
                    seq2 = 0xff - ord(seq2)

            # Packet received in wrong number
            if not (seq1 == seq2 == sequence):
                log.Logger("[R] ERROR: Expected seq=%d but got (seq1=%r, seq2=%r), receiving next block..."%(sequence, seq1, seq2), 'RED')
                self.reader.read(packet_size + 1 + crc_mode)
            
            # Packet received
            else:
                data = self.reader.read(packet_size + 1 + crc_mode, timeout)
                valid, data = self._verify_recv_checksum(crc_mode, data)

                # Write the original data to the target file
                if valid:
                    success_count += 1
                    log.Logger('[R] TRANSMISSION: Data block %d (seq=%d) is valid' %(success_count, sequence), 'GREEN')

                    valid_length = packet_size

                    # The last package adjusts the valid data length according to the file length
                    if (self._remaining_data_length > 0):
                        valid_length = min(valid_length, self._remaining_data_length)
                        self._remaining_data_length -= valid_length
                    data = data[:valid_length]

                    income_size += len(data)
                    stream.write(data)

                    if callable(callback):
                        callback(income_size, self._remaining_data_length)

                    self.writer.write(ACK)

                    sequence = (sequence + 1) % 0x100

                    char = self.reader.read(1, timeout)
                    continue

            # Broken packet received
            log.Logger("[R] ERROR: Purge, requesting retransmission (NAK)", 'RED')
            while True:
                data = self.reader.read(1, timeout=1)
                if data is None:
                    break
            self.writer.write(NAK)
            char = self.reader.read(1, timeout)
            continue

    def _verify_recv_checksum(self, crc_mode, data):
        if crc_mode:
            _checksum = bytearray(data[-2:])
            their_sum = (_checksum[0] << 8) + _checksum[1]
            data = data[:-2]

            our_sum = self.calc_crc(data)
            valid = bool(their_sum == our_sum)
            if not valid:
                log.Logger("[R] ERROR: Checksum failed (theirs=%04x, ours=%04x)" %(their_sum, our_sum), 'RED')
        else:
            _checksum = bytearray([data[-1]])
            their_sum = _checksum[0]
            data = data[:-1]

            our_sum = self.calc_checksum(data)
            valid = their_sum == our_sum
            if not valid:
                log.Logger("[R] ERROR: Checksum failed (theirs=%02x, ours=%02x)"%(their_sum, our_sum), 'RED')
        return valid, data

    def calc_checksum(self, data, checksum=0):
        if platform.python_version_tuple() >= ('3', '0', '0'):
            return (sum(data) + checksum) % 256
        else:
            return (sum(map(ord, data)) + checksum) % 256

    # For CRC algorithm
    crctable = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
    ]

    # CRC-16-CCITT
    def calc_crc(self, data, crc=0):
        for char in bytearray(data):
            crctbl_idx = ((crc >> 8) ^ char) & 0xff
            crc = ((crc << 8) ^ self.crctable[crctbl_idx]) & 0xffff
        return crc & 0xffff


def enter_dfu_mode(com, file):
    global boot_mode, com_port, zip_file
    log.Logger('*** Upgrading Firmware to "%s" (%s)'%(file.split('/')[-1], com), 'BLACK', 'WHITE', timestamp=0)
    com_port = com
    zip_file = file
    ser = serial.Serial(port=com, baudrate=default_baudrate, timeout=1)
    log.Logger('%s: %s'%(com, 'AT+HWID=?'))
    ser.write(str.encode('AT+HWID=?\r'))
    time.sleep(1)
    data = ""
    for i in range(3):
        tmp = ser.readline().decode('ascii', 'ignore').replace('\n', '').replace('\r', '')
        log.Logger('%s: %s' %(com, tmp))
        data += tmp
    if "apollo3" in str(data):
        if fun.shell('python3 %s/py_scripts/apollo3_uart_update_script.py -p %s -f %s -v' %(cf.get_value('root_dir'), com, file), 'Bootload completed successfully'):
            return True
        else:
            return False

    close_serial(ser)
    '''while check_boot_mode() ==False:
        log.Logger("enter dfu mode fail, again")
        time.sleep(5)'''
    if not check_boot_mode():
        detect_baudrate()
    if not boot_mode:
        if not check_boot_mode():
            log.Logger("Device do not enter boot mode")
            return False
    data = b""  
    ser = serial.Serial(port=com_port, baudrate=default_baudrate, timeout=5)
    if boot_mode:
        ser.write(b"at+update\r\n")
    else:
        log.Logger("enter dfu mode fail")
        return False
    while (ser.in_waiting):
        ser.read(1)
    time.sleep(1)
    def getc(size, timeout=1):
        data = ser.read(size)
        log.Logger('%s: %s' %(com, str(data)))
        return data or None
    def putc(data, timeout=1):
        return ser.write(data)
    sender = Modem(getc, putc,mode="ymodem1k")
    file_stream = open(zip_file, 'rb')
    file_info = {
            "name"      :   os.path.basename(zip_file),
            "length"    :   os.path.getsize(zip_file),
            "mtime"     :   os.path.getmtime(zip_file),
            "source"    :   "win"
        }
    if not sender.send(file_stream,info = file_info):
        log.Logger("Upload Failed")
        return False
    time.sleep(1)
    file_stream.close()
    ser.close()
    return True

def close_serial(ser):
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.close()

def ask_ok(ser,times=10):
    i=0
    data = b""
    while(b"OK\r\n" not in data):
        ser.write(b'a')
        time.sleep(0.5)
        ser.write(b't')
        time.sleep(0.5)
        ser.write(b'\r')
        time.sleep(0.5)
        ser.write(b'\n')
        time.sleep(0.5)
        data = b""
        while (ser.in_waiting):
            data  += ser.read(1)
        if i == times:
            return False
        i+=1
    return True



def detect_baudrate():
    test_baudrate = [
        115200,
        9600,
        921600,
        57600,
        38400,
        19200,
        230400,
        460800,
        76800,
        56000,
        31250,
        28800,
        14400,
        4800,
        250000,
        1000000,
        2400,
        1200]
    log.Logger("Detecting baudrate...")
    for i in test_baudrate:
        ser = serial.Serial(port=com_port, baudrate=i, timeout=5)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(b'\r\n')
        ser.write(b'\r\n')
        time.sleep(0.5)
        ser.write(b'at\r\n')
        time.sleep(2)
        data = b""
        while (ser.in_waiting):
            data += ser.read(1)
        if b"OK\r\n" in data or b"AT_ERROR" in data:
            if ask_ok(ser):
                log.Logger("Entering boot mode")
                log.Logger('%s: %s'%(com_port, b'at+boot\r\n'))
                ser.write(b'at+boot\r\n')
                time.sleep(1)
                close_serial(ser)
                return
        close_serial(ser)
    log.Logger("Detect baudrate fail, can not get the baudrate")
    return False

def check_boot_mode():
    while True:
        ser = serial.Serial(port=com_port, baudrate=default_baudrate, timeout=1)
        if ser:
            break
        time.sleep(10)
    
    ser.write(str.encode('AT+BOOT\r'))
    time.sleep(1)
    '''ser.write(b'a')
    time.sleep(0.5)
    ser.write(b't')
    time.sleep(0.5)
    ser.write(b'+')
    time.sleep(0.5)
    ser.write(b'\r')
    time.sleep(0.5)
    ser.write(b'\n')
    time.sleep(0.5)

    ser.write(b'at+\r\n')'''
    time.sleep(2)
    data = ""
    log.Logger('%s: %s'%(com_port, str.encode('AT+VER=?')))
    ser.write(str.encode('AT+VER=?\r'))
    for i in range(5):
        tmp = ser.readline().decode('ascii', 'ignore').replace('\n', '').replace('\r', '')
        log.Logger('%s: %s' %(com_port, tmp))
        data += tmp

    #while (ser.in_waiting):
    #    data += ser.read(1)
    if "BOOT" in str(data) or "AT not support" in str(data):
        global boot_mode
        boot_mode = 1
        close_serial(ser)
        log.Logger("Device is in boot mode")
        return True
    close_serial(ser)
    log.Logger("Device is not in boot mode")
    return False


#enter_dfu_mode('/dev/cu.usbserial-2140', '/Users/reesehung/Downloads/Firmware5/RAK3172-E/3172_164.bin')
#python uploader_ymodem.py -p com53 -f RUI_3.5.0a_RAK3172-E.bin
