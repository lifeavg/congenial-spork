import asyncio
import io
import os
import shutil
import tempfile
from typing import Self


class SpoolStreamException(Exception):
    pass


def _rollover_copy(memory_buffer, new_file):
    memory_buffer.seek(0)
    shutil.copyfileobj(memory_buffer, new_file)
    new_file.flush()


class AsyncSpoolStream:
    """
    Single writer -> single reader spooled bytes stream
    """

    def __init__(self, memory_limit: int = 1024 * 1024, max_size: int | None = None) -> None:
        self._memory_limit = memory_limit
        self._disk_limit = max_size
        self._memory: io.BytesIO | None = io.BytesIO()
        self._file: io.BufferedRandom | None = None
        self._write_pos = 0
        self._read_pos = 0
        self._condition = asyncio.Condition()
        self._reader_claimed = False
        self._writer_claimed = False
        self._eof = False

    async def write(self, data: bytes) -> None:
        async with self._condition:
            if self._eof:
                raise SpoolStreamException("Stream already closed")
            new_size = self._write_pos + len(data)
            if self._disk_limit is not None and new_size > self._disk_limit:
                raise SpoolStreamException("Disk limit exceeded")
            rollover_needed = self._file is None and new_size > self._memory_limit
            memory_buffer = self._memory if rollover_needed else None
        # ---- Phase 2: slow I/O outside lock ----
        if rollover_needed:
            new_file = tempfile.TemporaryFile()
            memory_buffer.seek(0)  # type: ignore
            await asyncio.to_thread(_rollover_copy, memory_buffer, new_file)
            # ---- Phase 3: swap under lock ----
            async with self._condition:
                # Another writer may have rolled over already
                if self._file is None:
                    self._file = new_file
                    self._memory = None
                else:
                    # Someone else already rolled over
                    new_file.close()
        # ---- Perform write ----
        if self._memory is not None:
            self._write_memory(data)
        else:
            assert self._file is not None
            await asyncio.to_thread(os.pwrite, self._file.fileno(), data, self._write_pos)
        async with self._condition:
            self._write_pos += len(data)
            self._condition.notify_all()

    async def read(self, n: int = -1) -> bytes:
        async with self._condition:
            await self._condition.wait_for(self._could_receive)
            available = self._write_pos - self._read_pos
            if available <= 0:
                return b""
            size = available if n < 0 else min(n, available)
        if self._memory is not None:
            data = self._read_memory(size)
        else:
            assert self._file is not None
            data = await asyncio.to_thread(os.pread, self._file.fileno(), size, self._read_pos)
        async with self._condition:
            self._read_pos += len(data)
        return data

    async def flush(self) -> None:
        if self._memory is not None:
            self._memory.flush()
        if self._file is not None:
            await asyncio.to_thread(self._file.flush)

    async def eof(self) -> None:
        async with self._condition:
            self._eof = True
            self._condition.notify_all()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        chunk = await self.read()
        if not chunk:
            raise StopAsyncIteration()
        return chunk

    def _could_receive(self) -> bool:
        return self._write_pos > self._read_pos or self._eof

    def _write_memory(self, data: bytes) -> None:
        assert self._memory is not None
        if self._memory.tell() != self._write_pos:
            self._memory.seek(self._write_pos)
        self._memory.write(data)

    def _read_memory(self, size: int) -> bytes:
        assert self._memory is not None
        if self._memory.tell() != self._read_pos:
            self._memory.seek(self._read_pos)
        return self._memory.read(size)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        async with self._condition:
            self._eof = True
            self._condition.notify_all()
        await asyncio.to_thread(self._close)

    def _close(self) -> None:
        if self._file is not None:
            self._file.close()
        if self._memory is not None:
            self._memory.close()
